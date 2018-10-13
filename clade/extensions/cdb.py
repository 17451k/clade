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
import os
import sys
import tempfile

from clade.extensions.abstract import Extension
from clade.intercept import Interceptor


class CDB(Extension):
    requires = ["CC"]

    def __init__(self, work_dir, conf=None, preset="base"):
        if not conf:
            conf = dict()

        conf["log_level"] = "ERROR"
        super().__init__(work_dir, conf, preset)

        self.cdb = []
        self.cdb_file = os.path.abspath(self.conf.get("CDB.output", "compile_commands.json"))

    @Extension.prepare
    def parse(self, cmds_file):
        cmds = self.extensions["CC"].load_all_cmds(compile_only=True)

        for cmd in cmds:
            for i, cmd_in in enumerate(cmd["in"]):
                # Ignore commands with object files as input
                # So, gcc lib1.o lib2.o -o lib will be ignored
                file_ext = os.path.splitext(os.path.basename(cmd_in))[1]
                if file_ext not in self.extensions["CC"].file_extensions:
                    continue

                arguments = [cmd["command"]] + cmd["opts"] + [cmd_in]
                if cmd["out"]:
                    if "-c" in cmd["opts"]:
                        arguments.extend(["-o", cmd["out"][i]])
                    else:
                        arguments.extend(["-o", cmd["out"][0]])

                self.cdb.append({
                    "directory": cmd["cwd"],
                    "arguments": arguments,
                    "file": cmd_in
                })

        self.dump_data(self.cdb, self.cdb_file)

    def load_cdb(self):
        """Load compilation database."""
        return self.load_data(self.cdb_file)


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", help="a path to the FILE where compilation database will be saved", metavar='FILE', default="compile_commands.json")
    parser.add_argument("-f", "--fallback", help="enable fallback intercepting mode", action="store_true")
    parser.add_argument("-c", "--cmds_file", help="a path to the file with intercepted commands")
    parser.add_argument(dest="command", nargs=argparse.REMAINDER, help="build command to run")

    args = parser.parse_args(args)

    if not args.command and not args.cmds_file:
        sys.exit("Build command is missing")

    if not args.cmds_file:
        args.cmds_file = os.path.join(tempfile.mkdtemp(), "cmds.txt")

    return args


def main(args=sys.argv[1:]):
    args = parse_args(args)

    if args.command:
        i = Interceptor(command=args.command, output=args.cmds_file, debug="ERROR", fallback=args.fallback)
        i.execute()

    c = CDB(tempfile.mkdtemp(), conf={"CDB.output": args.output})
    c.parse(args.cmds_file)
