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
from clade.extensions.callgraph import Callgraph


class Variables(Callgraph):
    requires = ["Info", "Functions"]

    __version__ = "2"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.variables = dict()
        self.variables_folder = "variables"

        self.used_in_vars = dict()
        self.used_in_vars_file = "used_in_vars.json"

        self.functions = None
        self.function_name_re = re.compile(r"\(?\s*&?\s*(\w+)\s*\)?$")
        self.possible_functions = set()

    @Extension.prepare
    def parse(self, cmds_file):
        self.functions = self.extensions["Functions"].load_functions()

        self.__process_init_global()

        self.dump_data_by_key(self.variables, self.variables_folder)
        self.dump_data(self.used_in_vars, self.used_in_vars_file)

        self._clean_error_log()

        self.functions.clear()
        self.variables.clear()
        self.used_in_vars.clear()

    def __process_init_global(self):
        if not os.path.isfile(self.extensions["Info"].init_global):
            self.log("There is no global variables to parse")
            return

        self.log("Parsing global variables initializations")
        for c_file, signature, type, json_str in self.extensions["Info"].iter_init_global():
            if c_file not in self.variables:
                self.variables[c_file] = []

            initializations = ujson.loads(json_str)

            self.variables[c_file].append({
                "declaration": signature,
                "path": c_file,
                "type": type,
                "value": initializations
            })

            # Save all functions referred at initialization of this variable
            self.possible_functions = set()
            self.__process_values(initializations)
            self.__process_callv(self.possible_functions, c_file)

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

    def __process_callv(self, functions, context_file):
        functions = {f for f in functions if f in self.functions}
        if not functions:
            return

        options = (
            lambda fs: tuple(f for f in fs if f == context_file),
            lambda fs: tuple(f for f in fs if self._t_unit_is_common(f, context_file)),
            lambda fs: tuple(f for f in fs if self._files_are_linked(f, context_file)),
        )

        for func in functions:
            # For each function call there can be many definitions with the same name, defined in different files.
            # possible_files is a list of them.
            possible_files = tuple(f for f in self.functions[func] if f != "unknown")

            if len(possible_files) == 0:
                self._error("No possible definitions for use: {}".format(func))
                continue

            for category in options:
                files = category(possible_files)
                if len(files) > 0:
                    break
            else:
                self._error("Can't match definition for use: {} {}".format(func, context_file))
                files = ('unknown',)

            if len(files) > 1:
                self._error("Multiple matches for use in vars: {} in {}".format(func, context_file))

            for possible_file in files:
                if func not in self.used_in_vars:
                    self.used_in_vars[func] = {possible_file: [context_file]}
                elif possible_file not in self.used_in_vars[func]:
                    self.used_in_vars[func][possible_file] = [context_file]
                elif context_file not in self.used_in_vars[func][possible_file]:
                    self.used_in_vars[func][possible_file].append(context_file)

    def load_variables(self, files=None):
        return self.load_data_by_key(self.variables_folder, files)

    def load_used_in_vars(self):
        return self.load_data(self.used_in_vars_file)
