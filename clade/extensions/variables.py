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

from clade.extensions.callgraph import Callgraph
from clade.extensions.initializations import parse_initialization_functions


class Variables(Callgraph):
    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        self.requires = ["Info", "Callgraph", "SrcGraph"]

        super().__init__(work_dir, conf)

        self.variables = dict()
        self.variables_suffix = ".vars.json"

        self.used_in_vars = dict()
        self.used_in_vars_file = "used_in_vars.json"

    def parse(self, cmds_file):
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.parse_prerequisites(cmds_file)

        self.callgraph = self.extensions["Callgraph"].load_callgraph()
        self.src_graph = self.extensions["SrcGraph"].load_src_graph()

        self.__process_init_global()
        self.dump_variables()
        self.dump_data(self.used_in_vars, self.used_in_vars_file)

    def __process_init_global(self):
        init_global = self.extensions["Info"].init_global

        if not os.path.isfile(init_global):
            return

        self.log("Processing global variables initializations")
        self.variables = parse_initialization_functions(init_global, self.callgraph, self.__process_callv)

    def __process_callv(self, functions, context_file):
        # This helps performance
        callgraph = self.callgraph
        used_in_vars = self.used_in_vars
        options = (
            lambda fs: tuple(f for f in fs if f == context_file),
            lambda fs: tuple(f for f in fs if self._t_unit_is_common(f, context_file)),
            lambda fs: tuple(f for f in fs if self._files_are_linked(f, context_file)),
        )

        for func in functions:
            # For each function call there can be many definitions with the same name, defined in different files.
            # possible_files is a list of them.
            possible_files = tuple(f for f in callgraph[func] if f != "unknown")

            if len(possible_files) == 0:
                self.__error("No possible definitions for use: {}".format(func))
                continue

            for category in options:
                files = category(possible_files)
                if len(files) > 0:
                    break
            else:
                self.__error("Can't match definition for use: {} {}".format(func, context_file))
                files = ('unknown',)

            if len(files) > 1:
                    self.__error("Multiple matches for use in vars: {} in {}".format(func, context_file))

            for possible_file in files:
                if func not in used_in_vars:
                    used_in_vars[func] = {possible_file: [context_file]}
                elif possible_file not in used_in_vars[func]:
                    used_in_vars[func][possible_file] = [context_file]
                elif context_file not in used_in_vars[func][possible_file]:
                    used_in_vars[func][possible_file].append(context_file)

    def dump_variables(self):
        self._dump_collection(self.variables, self.variables_suffix)

    def load_variables(self, files):
        return self._load_collection(self.variables_suffix, files)

    def load_used_in_vars(self):
        return self.load_data(self.used_in_vars_file)
