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

import os
import re
import subprocess
import sys

from clade.extensions.common import Common
from clade.extensions.utils import common_main


class CC(Common):
    """Class for parsing CC build commands."""

    requires = Common.requires + ["Storage"]

    file_extensions = [
        ".c", ".i", ".h",  # C
        "C", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hh", ".hpp", ".hxx", ".h++",  # C++
        ".s", ".S", ".asm"  # Assembly
    ]

    def __init__(self, work_dir, conf=None, preset="base"):
        super().__init__(work_dir, conf, preset)

        if "CC.which_list" not in self.conf:
            self.which_list = [
                r"^.*cc$",
                r"^.*[mg]cc(-?\d+(\.\d+){0,2})?$",
                r"^.*clang(-?\d+(\.\d+){0,2})?$"
            ]
        else:
            self.which_list = self.conf["CC.which_list"]

        if "CC.with_system_header_files" not in self.conf:
            self.conf["CC.with_system_header_files"] = True

        if "CC.store_deps" not in self.conf:
            self.conf["CC.store_deps"] = False

    def parse(self, cmds_file):
        super().parse(cmds_file, self.which_list)

    def parse_cmd(self, cmd):
        cmd_id = cmd["id"]

        parsed_cmd = super().parse_cmd(cmd, self.name)

        if self.is_bad(parsed_cmd):
            return

        self.debug("Parsed command: {}".format(parsed_cmd))

        # BUG: gcc do not print proper dependencies for commands with several input file
        # For example, there is no "file.c" in dependencies for command "gcc func.c main.c -o main"
        deps = set(self.__get_deps(cmd_id, parsed_cmd) + parsed_cmd["in"])
        self.debug("Dependencies: {}".format(deps))
        self.dump_deps_by_id(cmd_id, deps)
        self.dump_cmd_by_id(cmd_id, parsed_cmd)

        if self.conf["CC.store_deps"]:
            self.__store_src_files(deps, parsed_cmd["cwd"])

    def __get_deps(self, cmd_id, cmd):
        """Get a list of CC command dependencies."""
        deps_file = self.__collect_deps(cmd_id, cmd)
        return self.__parse_deps(deps_file)

    def __collect_deps(self, cmd_id, cmd):
        deps_file = os.path.join(self.temp_dir, "{}-deps.txt".format(cmd_id))

        if self.conf["CC.with_system_header_files"]:
            additional_opts = ["-Wp,-MD,{}".format(deps_file), "-M"]
        else:
            additional_opts = ["-Wp,-MMD,{}".format(deps_file), "-MM"]

        opts = cmd["opts"] + additional_opts
        command = [cmd["command"]] + opts + cmd["in"]

        # Do not execute a command that does not contain any input files
        if "-" not in command and cmd["in"]:
            subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=cmd["cwd"])

        return deps_file

    def __parse_deps(self, deps_file):
        deps = []

        if os.path.isfile(deps_file):
            with open(deps_file, encoding='utf8') as fp:
                match = re.match(r'[^:]+:(.+)', fp.readline())
                if match:
                    first_dep_line = match.group(1)
                else:
                    raise RuntimeError('Dependencies file has unsupported format')

                for dep_line in [first_dep_line] + fp.readlines():
                    if ':' in dep_line:
                        break
                    dep_line = dep_line.lstrip(' ')
                    dep_line = dep_line.rstrip(' \\\n')
                    if not dep_line:
                        continue
                    deps.extend(dep_line.split(' '))

            os.remove(deps_file)

        return deps

    def __store_src_files(self, deps, cwd):
        for file in deps:
            if not os.path.isabs(file):
                file = os.path.join(cwd, file)
            self.extensions["Storage"].add_file(file)

    def load_deps_by_id(self, id):
        return self.load_data(os.path.join("deps", "{}.json".format(id)))

    def dump_deps_by_id(self, id, deps):
        self.dump_data(deps, os.path.join("deps", "{}.json".format(id)))

    def is_a_compilation_command(self, cmd):
        if [cmd_in for cmd_in in cmd["in"] if os.path.splitext(os.path.basename(cmd_in))[1] not in self.file_extensions]:
            return False

        return True

    def load_all_cmds(self, filter_by_pid=True, with_opts=True, with_deps=False, compile_only=False):
        cmds = super().load_all_cmds(filter_by_pid=filter_by_pid)

        # compile only - ignore linker commands, like gcc func.o main.o -o main
        for cmd in cmds:
            if compile_only and not self.is_a_compilation_command(cmd):
                continue

            if with_opts:
                cmd["opts"] = self.load_opts_by_id(cmd["id"])
            if with_deps:
                cmd["deps"] = self.load_deps_by_id(cmd["id"])

            yield cmd


def main(args=sys.argv[1:]):
    common_main(CC, args)
