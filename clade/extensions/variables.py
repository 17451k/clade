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
# TODO: You can remove it as it will work with ujson everywhere (almost)
import json

from clade.extensions.abstract import Extension
from clade.extensions.callgraph import Callgraph
from clade.extensions.initializations import parse_variables_initializations


class Variables(Callgraph):
    requires = ["SrcGraph", "Info", "Functions"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.variables = dict()
        self.variables_archive = "variables.zip"

        self.used_in_vars = dict()
        self.used_in_vars_file = "used_in_vars.json"

        self.functions = None
        self.src_graph = None

    @Extension.prepare
    def parse(self, cmds_file):
        self.functions = self.extensions["Functions"].load_functions()
        self.src_graph = self.extensions["SrcGraph"].load_src_graph()

        self.__process_init_global()
        self._clean_error_log()

        self.dump_data_by_key(self.variables, self.variables_archive)
        self.dump_variables_data(self.used_in_vars, self.used_in_vars_file, indent=4)

        self.functions.clear()
        self.src_graph.clear()
        self.variables.clear()
        self.used_in_vars.clear()

    # TODO: Remove this as problem with ujson dump will be solved
    def dump_variables_data(self, data, file_name, indent=0):
        """Dump data to a json file in the object working directory."""

        if not os.path.isabs(file_name):
            file_name = os.path.join(self.work_dir, file_name)

        os.makedirs(os.path.dirname(file_name), exist_ok=True)

        self.debug("Dump {}".format(file_name))

        try:
            with open(file_name, "w") as fh:
                json.dump(data, fh, sort_keys=True, indent=indent, ensure_ascii=False)
        except RecursionError:
            # todo: This is a workaround but it is required rarely
            self.warning("Do not print data to file due to recursion limit {}".format(file_name))

    def __process_init_global(self):
        if not os.path.isfile(self.extensions["Info"].init_global):
            self.log("There is no global variables to parse")
            return

        self.log("Parsing global variables initializations")
        self.variables = parse_variables_initializations(
            self.extensions["Info"].iter_init_global,
            self.functions,
            self.__process_callv,
            self.work_dir
        )

    def __process_callv(self, functions, context_file):
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
        return self.load_data_by_key(self.variables_archive, files)

    def load_used_in_vars(self):
        return self.load_data(self.used_in_vars_file)
