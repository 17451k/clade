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

DELIMITER = "||"
LIB = os.path.join(os.path.dirname(__file__), "libinterceptor", "lib")
LIB64 = os.path.join(os.path.dirname(__file__), "libinterceptor", "lib64")


class Interceptor():
    """Object for intercepting and parsing build commands.

    Attributes:
        command: A list of strings representing build command to run and intercept
        output: A path to the file where intercepted commands will be saved
        debug: A boolean enabling debug logging messages
        fallback: A boolean enableing fallback intercepting mode

    Raises:
        NotImplementedError: Clade is launched on Windows
        RuntimeError: Clade installation is corrupted, or intercepting process failed
    """

    def __init__(self, command=[], output="cmds.txt", debug=False, fallback=False):
        self.command = command
        self.output = os.path.abspath(output)
        self.debug = debug
        self.fallback = fallback

        if self.fallback:
            self.wrapper = self.__find_wrapper()
        else:
            self.libinterceptor = self.__find_libinterceptor()

        self.env = self.__setup_env()

    def __find_libinterceptor(self):
        if sys.platform == "linux":
            libinterceptor = self.__find_libinterceptor_linux()
        elif sys.platform == "darwin":
            libinterceptor = self.__find_libinterceptor_darwin()
        else:
            raise NotImplementedError("To use Clade on {!r} please run it with fallback mode enabled".format(sys.platform))

        return libinterceptor

    def __find_libinterceptor_linux(self):
        libinterceptor_name = "libinterceptor.so"
        libinterceptor = os.path.join(os.path.dirname(__file__), "libinterceptor", libinterceptor_name)

        if not os.path.exists(libinterceptor):
            raise RuntimeError("libinterceptor is not found in {!r}".format(libinterceptor))

        # Multilib support
        path = os.path.join(LIB, libinterceptor_name)
        path64 = os.path.join(LIB64, libinterceptor_name)

        if os.path.exists(path) and os.path.exists(path64):
            libinterceptor = libinterceptor_name
            logging.debug("Path to libinterceptor library locations: {!r}, {!r}".format(path, path64))
        else:
            logging.debug("Path to libinterceptor library location: {!r}".format(libinterceptor))

        return libinterceptor

    def __find_libinterceptor_darwin(self):
        libinterceptor = os.path.join(os.path.dirname(__file__), "libinterceptor", "libinterceptor.dylib")

        if not os.path.exists(libinterceptor):
            raise RuntimeError("libinterceptor is not found in {!r}".format(libinterceptor))

        logging.debug("Path to libinterceptor library location: {!r}".format(libinterceptor))

        return libinterceptor

    def __find_wrapper(self):
        wrapper = os.path.join(os.path.dirname(__file__), "libinterceptor", "wrapper")

        if not os.path.exists(wrapper):
            raise RuntimeError("wrapper is not found in {!r}".format(wrapper))

        logging.debug("Path to the wrapper: {!r}".format(wrapper))

        return wrapper

    def __crete_wrappers(self):
        clade_bin = tempfile.mkdtemp()
        logging.debug("Create temporary directory for wrappers: {!r}".format(clade_bin))

        if os.path.exists(clade_bin):
            shutil.rmtree(clade_bin)

        os.makedirs(clade_bin)

        paths = os.environ.get("PATH", "").split(os.pathsep)

        counter = 0
        logging.debug("Walk through every directory in PATH to create wrappers: {!r}".format(paths))
        for path in paths:
            try:
                for file in os.listdir(path):
                    if os.access(os.path.join(path, file), os.X_OK):
                        try:
                            os.symlink(self.wrapper, os.path.join(clade_bin, file))
                            counter += 1
                        except FileExistsError:
                            continue
            except FileNotFoundError:
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
            env["CLADE_INTERCEPT"] = self.output
        else:
            logging.debug("Set 'CLADE_INTERCEPT_FALLBACK' environment variable value")
            env["CLADE_INTERCEPT_FALLBACK"] = self.output

        if sys.platform == "linux":
            env["LD_LIBRARY_PATH"] = env.get("LD_LIBRARY_PATH", "") + ":" + LIB64 + ":" + LIB
            logging.debug("Set LD_LIBRARY_PATH environment variable value as {!r}".format(env["LD_LIBRARY_PATH"]))

        return env

    def __intercept_first_command(self):
        logging.debug("'Intercept' the main command manually in order for it to appear in the output file")
        which = shutil.which(self.command[0])

        if not which:
            return

        with open(self.output, "a") as f:
            f.write(DELIMITER.join([os.getcwd(), which] + self.command) + "\n")

    def execute(self):
        """Execute intercepting and parsing of build commands.

        Returns:
            0 if everything went successful and error code otherwise
        """
        if not self.fallback:
            # Fallback mode can intercept first command without our help
            self.__intercept_first_command()

        logging.debug("Execute {} command with the following environment: {}".format(self.command, self.env))
        result = subprocess.run(self.command, env=self.env)

        return result.returncode


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", help="a path to the FILE where intercepted commands will be saved", metavar='FILE', default="cmds.txt")
    parser.add_argument("-d", "--debug", help="enable debug logging messages", action="store_true")
    parser.add_argument("-f", "--fallback", help="enable fallback intercepting mode", action="store_true")
    parser.add_argument(dest="command", nargs=argparse.REMAINDER, help="build command to run and intercept")

    args = parser.parse_args(args)

    if not args.command:
        sys.exit("Build command is missing")

    return args


def main(args=sys.argv[1:]):
    args = parse_args(args)

    logging.basicConfig(format="%(asctime)s {}: %(message)s".format(os.path.basename(sys.argv[0])),
                        level=logging.DEBUG if args.debug else logging.INFO,
                        datefmt="%H:%M:%S")

    logging.debug("Parsed command line arguments: {}".format(args))

    i = Interceptor(command=args.command, output=args.output, debug=args.debug, fallback=args.fallback)
    sys.exit(i.execute())


if __name__ == "__main__":
    main(sys.argv[1:])
