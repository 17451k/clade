# Copyright (c) 2022 Ilya Shchepetkov
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

import re

from clade.extensions.abstract import Extension
from clade.extensions.common_info import CommonInfo
from clade.types.nested_dict import nested_dict


class UsedIn(CommonInfo):
    requires = ["SrcGraph", "Info", "Functions"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.funcs = dict()

        self.used_in = nested_dict()
        self.used_in_file = "used_in.json"

        self.is_builtin = re.compile(r"(__builtin)|(__compiletime)")

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Processing function usages")

        self.funcs = self.extensions["Functions"].load_functions()

        self.__process_functions_usages()
        self._clean_warn_log()

        self.extensions["SrcGraph"].unload_src_graph()
        self.dump_data(self.used_in, self.used_in_file)

        self.used_in.clear()

    def load_used_in(self):
        return self.load_data(self.used_in_file)

    def __process_functions_usages(self):
        for context_file, context_cmd_id, context_func, func, line, context_type in self.extensions[
            "Info"
        ].iter_functions_usages():
            self.debug(
                "Processing function usages: "
                + " ".join([context_file, context_cmd_id, context_func, func, line, context_type])
            )

            if self.is_builtin.match(func):
                continue

            context_definition = self.extensions["Functions"].construct_definition(
                context_file, context_cmd_id, context_type, line
            )

            # For each function call there can be many definitions with the same name, defined in different
            # files. possible_definitions is a list of them.
            possible_definitions = []
            if func in self.funcs:
                for definition in self.funcs[func]:
                    if definition["type"] in (context_definition["type"], "exported"):
                        possible_definitions.append(definition)
            else:
                self._warning(f"Can't find '{func}' in Functions")

            # Assign priority number for each possible definition (see index variable)
            index = 3
            matched_files = []

            for files in (
                # 3: definition is located in the same file as the call
                (
                    d["file"]
                    for d in possible_definitions
                    if self._in_the_same_file(d, context_definition)
                ),
                # 2: definition is located in the same translation unit
                (
                    d["file"]
                    for d in possible_definitions
                    if self._in_the_same_tu(d, context_definition)
                ),
                # 1: definition is in the object file that is linked with the object file that contains the call
                (
                    d["file"]
                    for d in possible_definitions
                    if self._definition_is_linked(d, context_definition)
                ),
                # 0: definition is not found
                ["unknown"],
            ):
                matched_files = tuple(files)
                if matched_files:
                    break
                index -= 1

            if len(matched_files) > 1:
                self._warning(f"Multiple matches for use: {func}", context_file)

            for possible_file in matched_files:
                if func not in self.used_in[possible_file]:
                    self.used_in[possible_file][func] = {
                        "used_in_file": nested_dict(),
                        "used_in_func": nested_dict(),
                    }

                if context_func == "NULL":
                    self.used_in[possible_file][func]["used_in_file"][context_file][
                        line
                    ] = index
                else:
                    self.used_in[possible_file][func]["used_in_func"][context_file][
                        context_func
                    ][line] = index

                if possible_file == "unknown" and index == 0:
                    self._warning(
                        f"Can't match definition: {func}", context_file
                    )
