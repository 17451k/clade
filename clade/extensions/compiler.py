# Copyright (c) 2019 ISP RAS (http://www.ispras.ru)
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

from clade.extensions.common import Common


class Compiler(Common):
    """Parent class for all C compiler classes."""

    requires = Common.requires + ["Storage"]

    file_extensions = [
        ".c", ".i", ".h",  # C
        "C", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hh", ".hpp", ".hxx", ".h++",  # C++
        ".s", ".S", ".asm"  # Assembly
    ]

    def store_src_files(self, deps, cwd):
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

    def load_all_cmds(self, filter_by_pid=True, with_deps=False, compile_only=False):
        cmds = super().load_all_cmds(filter_by_pid=filter_by_pid)

        # compile only - ignore linker commands, like gcc func.o main.o -o main
        for cmd in cmds:
            if compile_only and not self.is_a_compilation_command(cmd):
                continue

            if with_deps:
                cmd["deps"] = self.load_deps_by_id(cmd["id"])

            yield cmd
