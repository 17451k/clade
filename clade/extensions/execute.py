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
import concurrent.futures
import os
import re
import subprocess
import sys
import tempfile
import ujson

from clade.extensions.abstract import Extension
from clade.extensions.opts import filter_opts, preprocessor_deps_opts


def unwrap(*args, **kwargs):
    return Execute._execute_command(*args, **kwargs)


class Execute(Extension):
    requires = ["CC"]

    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        conf["log_level"] = conf.get("log_level", "ERROR")
        super().__init__(work_dir, conf)

    def parse(self, cmds_file):
        if self.is_parsed():
            self.log("Skip parsing")
            return

        os.makedirs(self.work_dir, exist_ok=True)

        self.parse_prerequisites(cmds_file)
        cmds = self.extensions["CC"].load_all_cmds()

        if self.conf.get("Execute.parallel"):
            max_workers = os.cpu_count()
        else:
            max_workers = 1

        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as p:
            for cmd in cmds:
                p.submit(unwrap, self, cmd)

    def _execute_command(self, cmd):
        for cmd_in in [cmd_in for cmd_in in cmd["in"] if self.__is_cmd_good(cmd)]:
            file = cmd_in

            if self.conf.get("Execute.preprocess", True):
                file = self.__preprocess_file(cmd_in, cmd)

            if file:
                self.__execute(file, cmd)

    def __preprocess_file(self, cmd_in, cmd):
        opts = self.extensions["CC"].load_opts_by_id(cmd["id"])
        opts = filter_opts(opts, preprocessor_deps_opts)
        out = os.path.join(self.work_dir, os.path.basename(cmd_in) + ".i")
        args = [cmd["command"]] + ["-E"] + opts + [cmd_in] + ["-o", out]

        subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cmd["cwd"], universal_newlines=True)

        if not os.path.exists(out):
            return None

        return out

    def __execute(self, preprocessed_file, cmd):
        args = []

        basename = os.path.basename(preprocessed_file)

        for arg in self.conf["Execute.command"]:
            if re.match(r"^OPTS$", arg):
                args.extend(cmd["opts"])
                continue

            arg = re.sub(r"INPUT", preprocessed_file, arg)
            arg = re.sub(r"BASENAME", basename, arg)
            args.append(arg)

        subprocess.run(args, cwd=cmd["cwd"])

    def __is_cmd_good(self, cmd):
        if cmd["in"] == []:
            return False

        for cmd_in in cmd["in"]:
            if cmd_in == "-" or cmd_in == "/dev/null" or not re.search(r'\.c$', cmd_in):
                return False

        return True


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument("-w", "--work_dir", help="a path to the DIR where processed commands will be saved", metavar='DIR', default=tempfile.mkdtemp())
    parser.add_argument("--config", help="a path to the JSON file with configuration", metavar="", default=None)
    parser.add_argument("-c", "--cmds", help="a path to the file with intercepted commands")
    parser.add_argument(dest="command", nargs=argparse.REMAINDER, help="command to execute around all preprocessed .c files")

    args = parser.parse_args(args)

    conf = dict()
    if args.config:
        try:
            with open(args.config, "r") as f:
                conf = ujson.load(f)
        except FileNotFoundError:
            print("Configuration file is not found")
            sys.exit(-1)

    conf["work_dir"] = conf.get("work_dir", args.work_dir)
    conf["cmds_file"] = conf.get("cmds_file", args.cmds)
    conf["Execute.command"] = conf.get("Execute.command", args.command)

    if not conf["Execute.command"]:
        print("Please specify command to execute")
        sys.exit(-1)

    return conf


def parse(args=sys.argv[1:]):
    conf = parse_args(args)

    c = Execute(conf["work_dir"], conf=conf)
    c.parse(conf["cmds_file"])
