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

import re

from clade.extensions.abstract import Extension
from clade.extensions.common_info import CommonInfo
from clade.types.nested_dict import nested_dict, traverse


class Callgraph(CommonInfo):
    requires = ["SrcGraph", "Info", "Functions"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.funcs = dict()

        self.callgraph = nested_dict()
        self.callgraph_folder = "callgraph"

        self.is_builtin = re.compile(r"(__builtin)|(__compiletime)")

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Generating callgraph")

        self.funcs = self.extensions["Functions"].load_functions()

        self.__process_calls()
        self.__add_types()
        self._clean_warn_log()

        if not self.callgraph:
            self.warning("Callgraph is empty")
            return

        self.dump_data_by_key(self.callgraph, self.callgraph_folder)

        self.extensions["SrcGraph"].unload_src_graph()
        self.funcs.clear()
        self.callgraph.clear()

    def load_callgraph(self, files=None):
        return self.load_data_by_key(self.callgraph_folder, files)

    def yield_callgraph(self, files=None):
        yield from self.yield_data_by_key(self.callgraph_folder, files)

    def __process_calls(self):
        # TODO: Linux kernel cpecific, move to the configuration
        is_bad = re.compile(r"__bad")

        for (
            context_file,
            context_cmd_id,
            context_func,
            func,
            call_line,
            call_type,
            args,
        ) in self.extensions["Info"].iter_calls():
            # args are excluded from the debug log
            self.debug(
                "Processing function calls: "
                + " ".join(
                    [
                        context_file,
                        context_cmd_id,
                        context_func,
                        func,
                        call_line,
                        call_type,
                    ]
                )
            )

            if self.is_builtin.match(func) or (
                is_bad.match(func) and func not in self.callgraph
            ):
                self.debug("Function {} is bad".format(func))
                continue

            context_definition = self.extensions["Functions"].construct_definition(
                context_file, context_cmd_id, call_type, call_line
            )

            matched_files, index = self.__get_definitions(func, context_definition)

            if len(matched_files) > 1:
                self._warning(f"Multiple matches: {func}", context_file)

            for possible_file in matched_files:
                call_val = {
                    "match_type": index,
                }

                if args:
                    call_val["args"] = args

                self.callgraph[possible_file][func]["called_in"][context_file][
                    context_func
                ][call_line] = call_val

                # Create reversed callgraph
                self.callgraph[context_file][context_func]["calls"][possible_file][
                    func
                ][call_line] = call_val

                if possible_file == "unknown" and index == 0:
                    self._warning(f"Can't match definition: {func}", context_file)
                else:
                    self.debug(
                        "Function {} from {} is called in {}:{} in {}".format(
                            func, possible_file, context_file, call_line, context_func
                        )
                    )

    def __add_types(self):
        # Keep function types in the callgraph
        for path, func in traverse(self.callgraph, 2):
            if path == "unknown" and func not in self.funcs:
                continue

            for definition in self.funcs[func]:
                # Warning: may be innacurate
                if definition["file"] == path:
                    self.callgraph[path][func]["type"] = definition["type"]
                    break
            else:
                self.callgraph[path][func]["type"] = "extern"

    def __get_definitions(self, func, context_definition):
        # For each function call there can be many definitions with the same name, defined in different
        # files. possible_definitions is a list of them.
        possible_definitions = []
        if func in self.funcs:
            for definition in self.funcs[func]:
                if definition["type"] in (context_definition["type"], "exported"):
                    possible_definitions.append(definition)
        else:
            self._warning(f"Can't find '{func}' in Functions")

        matched_files = []
        # Assign priority number for each possible definition (see index variable)
        index = 5

        for files in (
            # 5: definition is located in the same file as the call
            (
                d["file"]
                for d in possible_definitions
                if self._in_the_same_file(d, context_definition)
            ),
            # 4: definition is located in the same translation unit
            (
                d["file"]
                for d in possible_definitions
                if self._in_the_same_tu(d, context_definition)
            ),
            # 3: definition is an exported function (Linux kernel only)
            (
                d["file"]
                for d in possible_definitions
                if self._definition_is_exported(d, context_definition)
            ),
            # 2: definition is in the object file that is linked with the object file that contains the call
            (
                d["file"]
                for d in possible_definitions
                if self._definition_is_linked(d, context_definition)
            ),
            # 1: header files with declaration is included into the object file that contains the call
            (
                d["file"]
                for d in possible_definitions
                if self._declaration_is_in_the_same_tu(d, context_definition)
            ),
            # 0: definition is not found
            ["unknown"],
        ):
            matched_files = tuple(files)

            if matched_files:
                break
            index -= 1

        return matched_files, index
