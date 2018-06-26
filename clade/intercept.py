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
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile


class Interceptor():
    def __init__(self, args):
        self.args = self.__parse_args(args)

        if not self.args.fallback:
            self.libinterceptor = self.__find_libinterceptor()
        else:
            self.wrapper = self.__find_wrapper()

        self.clade_data = self.__create_data_file()
        self.env = self.__setup_env()
        self.delimeter = "||"

    def __parse_args(self, args):
        parser = argparse.ArgumentParser()

        parser.add_argument("-d", "--debug", help="enable debug logging messages", action="store_true")
        parser.add_argument("-f", "--fallback", help="enable fallback intercepting mode", action="store_true")
        parser.add_argument("-o", "--output", help="store intercepted commands in FILE", metavar='FILE', default="cmds.json")
        parser.add_argument(dest="command", nargs=argparse.REMAINDER, help="build command to run and intercept")

        args = parser.parse_args(args)

        if not args.command:
            raise sys.exit("Build command is mising")

        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG if args.debug else logging.INFO)

        logging.debug("Parsed command line arguments: {}".format(args))

        return args

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

        if not self.args.fallback:
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

        logging.debug("Set 'CLADE_INTERCEPT' environment variable value")
        env["CLADE_INTERCEPT"] = self.clade_data

        return env

    def __intercept_first_command(self):
        logging.debug("'Intercept' the main command manually in order for it to appear in the output file")
        which = shutil.which(self.args.command[0])

        if not which:
            return

        with open(self.clade_data, "a") as f:
            f.write(self.delimeter.join([os.getcwd(), which] + self.args.command) + "\n")

    def __process_data_file(self):
        if not os.path.exists(self.clade_data):
            raise RuntimeError("clade row file '{}' is not found".format(self.clade_data))

        cmds = []

        logging.debug("Process intercepted commands")
        with open(self.clade_data, "r") as f:
            for cmd_id, line in enumerate(f):
                cmd = dict()
                cmd["cwd"], cmd["which"], *cmd["command"] = line.strip().split(self.delimeter)
                cmd["id"] = cmd_id
                cmds.append(cmd)
                logging.debug("Process: {}".format(cmd))

        cmds_json = os.path.abspath(self.args.output)

        logging.debug("Store intercepted commads: {}".format(cmds_json))
        with open(cmds_json, "w") as f:
            json.dump(cmds, f, sort_keys=True, indent=4)

        return cmds_json

    def execute(self):
        if not self.args.fallback:
            # Fallback mode can intercept first command without our help
            self.__intercept_first_command()

        logging.debug("Execute '{}' command with the following environment: {}".format(self.args.command, self.env))
        result = subprocess.run(self.args.command, env=self.env)

        self.__process_data_file()

        return result.returncode


def main(args=sys.argv[1:]):
    i = Interceptor(args)
    i.execute()


if __name__ == "__main__":
    main(sys.argv[1:])
