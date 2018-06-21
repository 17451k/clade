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

        self.clade_raw = self.__setup_raw_file()
        self.env = self.__setup_env()

    def __parse_args(self, args):
        parser = argparse.ArgumentParser()

        parser.add_argument("-d", "--debug", help="enable debug logging messages", action="store_true")
        parser.add_argument("-f", "--fallback", help="enable fallback intercepting mode", action="store_true")
        parser.add_argument(dest="command", nargs=argparse.REMAINDER, help="build command to run and intercept")

        args = parser.parse_args(args)

        if not args.command:
            raise sys.exit("Build command is mising")

        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG if args.debug else logging.INFO)

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

        return libinterceptor

    def __find_wrapper(self):
        wrapper = os.path.join(os.path.dirname(__file__), "libinterceptor", "wrapper")

        if not os.path.exists(wrapper):
            raise RuntimeError("wrapper is not found")

        return wrapper

    def __setup_raw_file(self):
        clade_intercept = os.path.join(tempfile.gettempdir(), "clade-intercept")

        if os.path.exists(clade_intercept):
            shutil.rmtree(clade_intercept)

        os.makedirs(clade_intercept)

        return os.path.join(clade_intercept, "raw.txt")

    def __crete_wrappers(self):
        clade_bin = os.path.join(tempfile.gettempdir(), "clade-bin")

        if os.path.exists(clade_bin):
            shutil.rmtree(clade_bin)

        os.makedirs(clade_bin)

        paths = os.environ.get("PATH", "").split(os.pathsep)

        for path in paths:
            for file in os.listdir(path):
                if os.access(os.path.join(path, file), os.X_OK):
                    try:
                        os.symlink(self.wrapper, os.path.join(clade_bin, file))
                    except FileExistsError:
                        continue

        print(clade_bin)

        return clade_bin

    def __setup_env(self):
        env = dict(os.environ)

        if not self.args.fallback:
            if sys.platform == "darwin":
                env["DYLD_INSERT_LIBRARIES"] = self.libinterceptor
                env["DYLD_FORCE_FLAT_NAMESPACE"] = "1"
            elif sys.platform == "linux":
                env["LD_PRELOAD"] = self.libinterceptor
        else:
            env["PATH"] = self.__crete_wrappers() + ":" + os.environ.get("PATH", "")

        env["CLADE_INTERCEPT"] = self.clade_raw

        return env

    def __intercept_first_command(self):
        # "Intercept" the main command manually
        which = shutil.which(self.args.command[0])

        if not which:
            return

        with open(self.clade_raw, "a") as f:
            f.write("||".join([os.getcwd(), which] + self.args.command) + "\n")

    def __process_raw_file(self):
        if not os.path.exists(self.clade_raw):
            raise RuntimeError("clade row file '{}' is not found".format(self.clade_raw))

        cmds = []

        with open(self.clade_raw, "r") as f:
            for cmd_id, line in enumerate(f):
                cmd = dict()
                cmd["cwd"], cmd["which"], *cmd["command"] = line.strip().split("||")
                cmd["id"] = cmd_id
                cmds.append(cmd)

        cmds_json = os.path.abspath("cmds.json")

        with open(cmds_json, "w") as f:
            json.dump(cmds, f, sort_keys=True, indent=4)

        logging.info("Intercepted commads can be found here: {}".format(cmds_json))
        return cmds_json

    def execute(self):
        self.__intercept_first_command()

        logging.info('Execute "{}" command'.format(self.args.command))
        resut = subprocess.run(self.args.command, env=self.env)

        if not resut.returncode:
            self.__process_raw_file()
        else:
            sys.exit("Something went wrong")


def main(args=sys.argv[1:]):
    i = Interceptor(args)
    i.execute()


if __name__ == "__main__":
    main(sys.argv[1:])
