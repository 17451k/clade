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

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile


class Interceptor():
    def __init__(self, args):
        if not args:
            raise sys.exit("Build command is mising")
        self.args = args

        self.libinterceptor = self.__find_libinterceptor()
        self.clade_raw = self.__setup_raw_file()
        self.env = self.__setup_env()

    def __find_libinterceptor(self):
        if sys.platform == "linux":
            libinterceptor = os.path.join(os.path.dirname(__file__), "libinterceptor", "libinterceptor.so")
        elif sys.platform == "darwin":
            libinterceptor = os.path.join(os.path.dirname(__file__), "libinterceptor", "libinterceptor.dylib")
        else:
            raise NotImplementedError("clade is not yet supported on your platform ({})".format(sys.platform))

        if not os.path.exists(libinterceptor):
            raise RuntimeError("libinterceptor is not found")

        return libinterceptor

    def __setup_raw_file(self):
        clade_intercept = os.path.join(tempfile.gettempdir(), "clade-intercept")

        if os.path.exists(clade_intercept):
            shutil.rmtree(clade_intercept)

        os.makedirs(clade_intercept)

        return os.path.join(clade_intercept, "raw.txt")

    def __setup_env(self):
        env = dict(os.environ)

        if sys.platform == "darwin":
            env["DYLD_INSERT_LIBRARIES"] = self.libinterceptor
            env["DYLD_FORCE_FLAT_NAMESPACE"] = "1"
        elif sys.platform == "linux":
            env["LD_PRELOAD"] = self.libinterceptor

        env.update({"CLADE_INTERCEPT": self.clade_raw})

        return env

    def __intercept_first_command(self):
        # "Intercept" the main command manually
        which = shutil.which(self.args[0])

        if not which:
            return

        with open(self.clade_raw, "a") as f:
            f.write("||".join([os.getcwd(), which] + self.args) + "\n")

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

        logging.info('Execute "{}" command'.format(self.args))
        resut = subprocess.run(self.args, env=self.env)

        if not resut.returncode:
            self.__process_raw_file()
        else:
            sys.exit("Something went wrong")


def main(args=sys.argv[1:]):
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

    i = Interceptor(args)
    i.execute()


if __name__ == "__main__":
    main(sys.argv[1:])
