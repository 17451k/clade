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

from clade.extensions.abstract import Extension
from clade.extensions.callgraph import Callgraph
from clade.extensions.utils import nested_dict, traverse


class Functions(Callgraph):
    requires = ["SrcGraph", "Info"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.src_graph = dict()

        self.funcs = nested_dict()
        self.funcs_file = "functions.json"

        self.funcs_by_file = nested_dict()
        self.funcs_by_file_file = "functions_by_file.json"
        self.funcs_by_file_folder = "functions_by_file"

    @Extension.prepare
    def parse(self, cmds_file):
        self.src_graph = self.extensions["SrcGraph"].load_src_graph()

        self.log("Parsing function definitions and declarations")
        self.__process_definitions()
        self.__process_declarations()
        self.__process_exported()
        self.__group_functions_by_file()
        self._clean_error_log()

        self.dump_data(self.funcs, self.funcs_file)
        self.dump_data(self.funcs_by_file, self.funcs_by_file_file)
        self.dump_data_by_key(self.funcs_by_file, self.funcs_by_file_folder)

        self.src_graph.clear()
        self.funcs.clear()
        self.funcs_by_file.clear()

        self.log("Parsing finished")

    def load_functions(self):
        """Load information about functions."""
        return self.load_data(self.funcs_file)

    def load_functions_by_file(self, files=None):
        """Load information about functions grouped by files."""
        if files:
            return self.load_data_by_key(self.funcs_by_file_folder, files)
        else:
            return self.load_data(self.funcs_by_file_file)

    def __process_definitions(self):
        for src_file, func, def_line, func_type, signature in self.extensions["Info"].iter_definitions():
            if func in self.funcs and src_file in self.funcs[func]:
                self._error(
                    "Function is defined more than once: {!r} {!r}".format(
                        func, src_file
                    )
                )
                continue

            self.funcs[func][src_file] = {
                "type": func_type,
                "line": def_line,
                "signature": signature,
                "declarations": dict(),
            }

    def __process_declarations(self):
        def get_unknown_val(decl_file, decl_val):
            return {
                "type": "extern",
                "line": None,
                "signature": None,
                "declarations": {decl_file: decl_val},
            }

        for decl_file, decl_name, decl_line, decl_type, decl_signature in self.extensions["Info"].iter_declarations():
            decl_val = {
                "signature": decl_signature,
                "line": decl_line,
                "type": decl_type,
            }

            if decl_name not in self.funcs:
                self.funcs[decl_name]["unknown"] = get_unknown_val(
                    decl_file, decl_val
                )
                continue

            if decl_file not in self.src_graph:
                self._error("Not in source graph: {}".format(decl_file))

            found = False

            for src_file in self.funcs[decl_name]:
                if src_file not in self.src_graph:
                    self._error("Not in source graph: {}".format(src_file))

                if (
                    src_file == decl_file
                    or self._t_unit_is_common(src_file, decl_file)
                    or (
                        decl_type == "extern"
                        and self._files_are_linked(src_file, decl_file)
                    )
                ):
                    self.funcs[decl_name][src_file]["declarations"][
                        decl_file
                    ] = decl_val
                    found = True
                elif src_file == "unknown":
                    if "unknown" in self.funcs[decl_name]:
                        self.funcs[decl_name]["unknown"]["declarations"][
                            decl_file
                        ] = decl_val
                    else:
                        self.funcs[decl_name]["unknown"] = get_unknown_val(
                            decl_file, decl_val
                        )
                    found = True

            if not found:
                self.funcs[decl_name]["unknown"] = get_unknown_val(
                    decl_file, decl_val
                )

    def __process_exported(self):
        for src_file, func in self.extensions["Info"].iter_exported():
            # Variables can also be exported
            if func not in self.funcs:
                continue
            elif src_file not in self.funcs[func]:
                continue
            self.funcs[func][src_file]["type"] = "exported"

    def __group_functions_by_file(self):
        for func, file in traverse(self.funcs, 2):
            self.funcs_by_file[file][func] = self.funcs[func][file]
