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
import ujson

from clade.extensions.abstract import Extension
from clade.extensions.common_info import CommonInfo


class Variables(CommonInfo):
    requires = ["Info", "Functions", "SrcGraph"]

    __version__ = "2"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.variables = dict()
        self.variables_folder = "variables"

        self.used_in_vars = dict()
        self.used_in_vars_file = "used_in_vars.json"

        self.funcs = None
        self.function_name_re = re.compile(r"\(?\s*&?\s*(\w+)\s*\)?$")
        self.possible_functions = set()

    @Extension.prepare
    def parse(self, cmds_file):
        self.funcs = self.extensions["Functions"].load_functions()

        self.__process_init_global()

        self.dump_data_by_key(self.variables, self.variables_folder)
        self.dump_data(self.used_in_vars, self.used_in_vars_file)

        self._clean_warn_log()

        self.funcs.clear()
        self.variables.clear()
        self.used_in_vars.clear()

    def __process_init_global(self):
        if not os.path.isfile(self.extensions["Info"].init_global):
            self.log("There is no global variables to parse")
            return

        self.log("Parsing global variables initializations")
        for c_file, signature, cmd_id, type, json_str in self.extensions[
            "Info"
        ].iter_init_global():
            if c_file not in self.variables:
                self.variables[c_file] = []

            initializations = ujson.loads(json_str)

            self.variables[c_file].append(
                {
                    "declaration": signature,
                    "path": c_file,
                    "type": type,
                    "value": initializations,
                }
            )

            # Save all functions referred at initialization of this variable
            self.possible_functions = set()
            self.__process_values(initializations)
            self.__process_callv(c_file, cmd_id)

    def __process_values(self, value):
        if isinstance(value, str):
            self.__add_possible_function_name(value)
        elif isinstance(value, dict):
            self.__process_values(value["value"])
        elif isinstance(value, list):
            [self.__process_values(v) for v in value]
        else:
            raise RuntimeError(f"Unknown value: {value}")

    def __add_possible_function_name(self, value):
        # Check that the explicit value is a function reference
        m = self.function_name_re.fullmatch(value)

        if m:
            function_name = m.group(1)
            self.possible_functions.add(function_name)

    def __process_callv(self, context_file, context_cmd_id):
        functions = {f for f in self.possible_functions if f in self.funcs}

        if not functions:
            return

        context_definition = self.extensions["Functions"].construct_definition(
            context_file, context_cmd_id, None, None
        )

        for func in functions:
            # For each function call there can be many definitions with the same name, defined in different
            # files. possible_definitions is a list of them.
            possible_definitions = []
            if func in self.funcs:
                for definition in self.funcs[func]:
                    possible_definitions.append(definition)

            if not possible_definitions:
                continue

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

            if len(matched_files) > 1:
                self._warning(f"Multiple matches: {func}", context_file)

            for possible_file in matched_files:
                if func not in self.used_in_vars:
                    self.used_in_vars[func] = {possible_file: [context_file]}
                elif possible_file not in self.used_in_vars[func]:
                    self.used_in_vars[func][possible_file] = [context_file]
                elif context_file not in self.used_in_vars[func][possible_file]:
                    self.used_in_vars[func][possible_file].append(context_file)

                if possible_file == "unknown":
                    self._warning(f"Can't match definition: {func}", context_file)

    def load_variables(self, files=None):
        return self.load_data_by_key(self.variables_folder, files)

    def load_used_in_vars(self):
        return self.load_data(self.used_in_vars_file)
