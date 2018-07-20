# Copyright (c) 2018 ISP RAS (http://www.ispras.ru)
# Ivannikov Institute for System Programming of the Russian Academy of Sciences
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import ujson


class Interceptor():
    """Object for intercepting and parsing build commands.

    Attributes:
        command: A list of strings representing build command to run and intercept
        output: A path to the file where intercepted commands will be saved
        unprocessed: A path to the file where unprocessed intercepted commands will be saved
        reuse: A path to the file with unprocessed intercepted commands you want to reuse
        debug: A boolean enabling debug logging messages
        fallback: A boolean enableing fallback intercepting mode

    Raises:
        NotImplementedError: Clade is launched on Windows
        RuntimeError: Clade installation is corrupted, or intercepting process failed
    """

    def __init__(self, command=[], output="cmds.json", unprocessed="", reuse="", debug=False, fallback=False):
        self.command = command
        self.output = os.path.abspath(output)
        self.unprocessed = unprocessed
        self.reuse = reuse
        self.debug = debug
        self.fallback = fallback

        if not self.fallback and not self.reuse:
            self.libinterceptor = self.__find_libinterceptor()
        elif not self.reuse:
            self.wrapper = self.__find_wrapper()

        if self.unprocessed:
            self.unprocessed = os.path.abspath(self.unprocessed)
            self.clade_data = self.unprocessed
        elif self.reuse:
            self.reuse = os.path.abspath(self.reuse)
            self.clade_data = self.reuse
        else:
            self.clade_data = self.__create_data_file()

        if not self.reuse:
            self.env = self.__setup_env()

        self.delimeter = "||"

    def __find_libinterceptor(self):
        if sys.platform == "linux":
            libinterceptor = os.path.join(os.path.dirname(__file__), "libinterceptor", "libinterceptor.so")
        elif sys.platform == "darwin":
            libinterceptor = os.path.join(os.path.dirname(__file__), "libinterceptor", "libinterceptor.dylib")
        else:
            raise NotImplementedError("To use Clade on Windows please run it with fallback mode enabled ({})".format(sys.platform))

        if not os.path.exists(libinterceptor):
            raise RuntimeError("libinterceptor is not found")

        logging.debug("Path to libinterceptor library: {}".format(libinterceptor))

        return libinterceptor

    def __find_wrapper(self):
        wrapper = os.path.join(os.path.dirname(__file__), "libinterceptor", "wrapper")

        if not os.path.exists(wrapper):
            raise RuntimeError("wrapper is not found")

        logging.debug("Path to the wrapper: {}".format(wrapper))

        return wrapper

    def __create_data_file(self):
        (_, clade_data) = tempfile.mkstemp()
        logging.debug("Create temporary file where unprocessed intercepted commands will be stored: {}"
                      .format(clade_data))

        if os.path.exists(clade_data):
            os.remove(clade_data)

        return clade_data

    def __crete_wrappers(self):
        clade_bin = os.path.join(tempfile.gettempdir(), "clade-bin")
        logging.debug("Create temporary directory for wrappers: {}".format(clade_bin))

        if os.path.exists(clade_bin):
            shutil.rmtree(clade_bin)

        os.makedirs(clade_bin)

        paths = os.environ.get("PATH", "").split(os.pathsep)

        counter = 0
        logging.debug("Walk through every directory in PATH to create wrappers: {}".format(paths))
        for path in paths:
            for file in os.listdir(path):
                if os.access(os.path.join(path, file), os.X_OK):
                    try:
                        os.symlink(self.wrapper, os.path.join(clade_bin, file))
                        counter += 1
                    except FileExistsError:
                        continue

        logging.debug("{} wrappers were created".format(counter))

        return clade_bin

    def __setup_env(self):
        env = dict(os.environ)

        if not self.fallback:
            if sys.platform == "darwin":
                logging.debug("Set 'DYLD_INSERT_LIBRARIES' environment variable value")
                env["DYLD_INSERT_LIBRARIES"] = self.libinterceptor
                env["DYLD_FORCE_FLAT_NAMESPACE"] = "1"
            elif sys.platform == "linux":
                logging.debug("Set 'LD_PRELOAD' environment variable value")
                env["LD_PRELOAD"] = self.libinterceptor
        else:
            env["PATH"] = self.__crete_wrappers() + ":" + os.environ.get("PATH", "")
            logging.debug("Add directory with wrappers to PATH")

        # 2 CLADE_INTERCEPT variables are needed purely for debugging purposes
        if not self.fallback:
            logging.debug("Set 'CLADE_INTERCEPT' environment variable value")
            env["CLADE_INTERCEPT"] = self.clade_data
        else:
            logging.debug("Set 'CLADE_INTERCEPT_FALLBACK' environment variable value")
            env["CLADE_INTERCEPT_FALLBACK"] = self.clade_data

        return env

    def __intercept_first_command(self):
        logging.debug("'Intercept' the main command manually in order for it to appear in the output file")
        which = shutil.which(self.command[0])

        if not which:
            return

        with open(self.clade_data, "a") as f:
            f.write(self.delimeter.join([os.getcwd(), which] + self.command) + "\n")

    def __process_data_file(self):
        if not os.path.exists(self.clade_data):
            raise RuntimeError("Clade data file '{}' is not found".format(self.clade_data))

        cmds = []

        logging.debug("Process intercepted commands")
        with open(self.clade_data, "r") as f:
            for cmd_id, line in enumerate(f):
                cmd = dict()
                cmd["cwd"], cmd["which"], *cmd["command"] = line.strip().split(self.delimeter)
                cmd["which"] = os.path.normpath(cmd["which"])
                cmd["id"] = cmd_id
                cmds.append(cmd)

        cmds_json = os.path.abspath(self.output)

        logging.debug("Store intercepted commads: {}".format(cmds_json))
        with open(cmds_json, "w") as f:
            ujson.dump(cmds, f, sort_keys=True, indent=4)

        if not self.unprocessed and not self.reuse:
            logging.debug("Remove Clade data file")
            os.remove(self.clade_data)

        logging.debug("Processing complete")

    def execute(self):
        """Execute intercepting and parsing of build commands.

        Returns:
            0 if everything went successful and error code otherwise
        """
        if self.reuse:
            logging.debug("Reuse unprocessed intercepted commands")
            self.__process_data_file()
            return 0

        if not self.fallback:
            # Fallback mode can intercept first command without our help
            self.__intercept_first_command()

        logging.debug("Execute '{}' command with the following environment: {}".format(self.command, self.env))
        result = subprocess.run(self.command, env=self.env)

        self.__process_data_file()

        return result.returncode


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", help="a path to the FILE where intercepted commands will be saved", metavar='FILE', default="cmds.json")
    parser.add_argument("-u", "--unprocessed", help="a path to the FILE where unprocessed intercepted commands will be saved", metavar='FILE')
    parser.add_argument("-r", "--reuse", help="a path to the FILE with unprocessed intercepted commands you want to reuse", metavar='FILE')
    parser.add_argument("-d", "--debug", help="enable debug logging messages", action="store_true")
    parser.add_argument("-f", "--fallback", help="enable fallback intercepting mode", action="store_true")
    parser.add_argument(dest="command", nargs=argparse.REMAINDER, help="build command to run and intercept")

    args = parser.parse_args(args)

    if not args.command and not args.reuse:
        sys.exit("Build command is mising")

    if args.unprocessed and os.path.exists(args.unprocessed):
        sys.exit("File specified in --unprocessed argument already exists")

    if args.reuse and not os.path.exists(args.reuse):
        sys.exit("File specified in --reuse argument does not exist")

    return args


def main(args=sys.argv[1:]):
    args = parse_args(args)

    logging.basicConfig(format="%(asctime)s {}: %(message)s".format(os.path.basename(sys.argv[0])),
                        level=logging.DEBUG if args.debug else logging.INFO,
                        datefmt="%H:%M:%S")

    logging.debug("Parsed command line arguments: {}".format(args))

    i = Interceptor(command=args.command, output=args.output, unprocessed=args.unprocessed,
                    reuse=args.reuse, debug=args.debug, fallback=args.fallback)
    sys.exit(i.execute())


if __name__ == "__main__":
    main(sys.argv[1:])
