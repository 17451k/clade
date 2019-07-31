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

    file_extensions = [".c", ".i"]

    __version__ = "1"

    def store_deps_files(self, deps, cwd):
        self.__store_src_files(deps, cwd, self.conf.get("Compiler.deps_encoding"))

    def store_pre_files(self, deps, cwd, encoding=None):
        self.__store_src_files(deps, cwd, encoding)

    def __store_src_files(self, deps, cwd, encodng=None):
        for file in deps:
            if not os.path.isabs(file):
                file = os.path.join(cwd, file)

            self.extensions["Storage"].add_file(file, encoding=None)

    def load_deps_by_id(self, id):
        return self.load_data(os.path.join("deps", "{}.json".format(id)))

    def dump_deps_by_id(self, id, deps):
        self.dump_data(deps, os.path.join("deps", "{}.json".format(id)))

    def is_a_compilation_command(self, cmd):
        if any(
            (
                True
                for cmd_in in cmd["in"]
                if os.path.splitext(os.path.basename(cmd_in))[1] in self.file_extensions
            )
        ):
            return True

        return False

    def load_all_cmds(self, filter_by_pid=True, with_opts=False, with_raw=False, with_deps=False, compile_only=False):
        cmds = super().load_all_cmds(with_opts=with_opts, with_raw=with_raw, filter_by_pid=filter_by_pid)

        # compile only - ignore linker commands, like gcc func.o main.o -o main
        # or cl /EP /P file.c
        for cmd in cmds:
            if compile_only and not self.is_a_compilation_command(cmd):
                continue

            if compile_only:
                # Remove .o files from compile-and-link commands, like gcc main.c -o main.o func.o
                cmd["in"] = [cmd_in for cmd_in in cmd["in"] if os.path.splitext(os.path.basename(cmd_in))[1] in self.file_extensions]
                if not cmd["in"]:
                    continue

            if with_deps:
                cmd["deps"] = self.load_deps_by_id(cmd["id"])

            yield cmd

    def get_all_pre_files(self):
        pre_files = []

        for cmd in self.load_all_cmds(compile_only=True):
            pre_files.extend(self.get_pre_files_by_id(cmd["id"]))

        return pre_files

    def get_pre_files_by_id(self, id):
        cmd = self.load_cmd_by_id(id)

        pre_files = []

        for cmd_in in cmd["in"]:
            pre_file = self.get_pre_file_by_path(cmd_in, cmd["cwd"])

            if os.path.exists(pre_file):
                pre_files.append(pre_file)

        return pre_files

    def get_pre_file_by_path(self, path, cwd):
        if os.path.isabs(path):
            abs_path = path
        else:
            abs_path = os.path.join(cwd, path)

        pre_file = os.path.splitext(abs_path)[0] + ".i"
        pre_file = self.extensions["Storage"].get_storage_path(pre_file)

        return pre_file
