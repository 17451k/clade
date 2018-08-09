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
import sys

from clade.extensions.callgraph import Callgraph
from clade.extensions.utils import parse_args


class Functions(Callgraph):
    requires = ["Info", "SrcGraph"]

    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        self.src_graph = dict()

        super().__init__(work_dir, conf)

        self.funcs = dict()
        self.funcs_file = "functions.json"

        self.funcs_by_file = dict()
        self.funcs_by_file_file = "functions_by_file.json"

    def parse(self, cmds_file):
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.parse_prerequisites(cmds_file)
        self.src_graph = self.extensions["SrcGraph"].load_src_graph()

        self.__process_definitions()
        self.__process_declarations()
        self.__process_exported()
        self.__group_functions_by_file()
        self._clean_error_log()

        self.log("Dump parsed data")
        self.dump_data(self.funcs, self.funcs_file)
        self.dump_data(self.funcs_by_file, self.funcs_by_file_file)
        self.log("Finish")

    def load_functions(self):
        """Load information about functions."""
        if self.funcs:
            return self.funcs
        else:
            return self.load_data(self.funcs_file)

    def load_functions_by_file(self):
        """Load information about functions grouped by files."""
        if self.funcs:
            return self.funcs
        else:
            return self.load_data(self.funcs_file)

    def __process_definitions(self):
        self.log("Processing function definitions")

        regex = re.compile(r"(\S*) (\S*) signature='([^']*)' (\S*) (\S*)")

        for line in self.extensions["Info"].iter_definitions():
            m = regex.match(line)
            if m:
                src_file, func, signature, def_line, func_type = m.groups()

                if func in self.funcs and src_file in self.funcs[func]:
                    self._error("Function is defined more than once: '{}' '{}'".format(func, src_file))
                    continue

                val = self._get_initial_value()
                val.update({"type": func_type, "defined_on_line": def_line, "signature": signature})

                if func in self.funcs:
                    self.funcs[func][src_file] = val
                else:
                    self.funcs[func] = {src_file: val}

    def __process_declarations(self):
        self.log("Processing declarations")

        regex = re.compile(r"(\S*) (\S*) signature='([^']*)' (\S*) (\S*)")

        def get_unknown_val(decl_file, dec_val):
            val = self._get_initial_value()
            val["declared_in"][decl_file] = dec_val
            return val

        for line in self.extensions["Info"].iter_declarations():
            m = regex.match(line)
            if m:
                decl_file, decl_name, decl_signature, decl_line, decl_type = m.groups()

                dec_val = {
                    'signature': decl_signature,
                    'def_line': decl_line,
                    'type': decl_type,
                }

                if decl_name not in self.funcs:
                    self.funcs[decl_name] = {"unknown": get_unknown_val(decl_file, dec_val)}
                    continue

                if decl_file not in self.src_graph:
                    self._error("Not in source graph: {}".format(decl_file))

                for src_file in self.funcs[decl_name]:
                    if src_file not in self.src_graph:
                        self._error("Not in source graph: {}".format(src_file))

                    if src_file == decl_file or self._t_unit_is_common(src_file, decl_file):
                        self.funcs[decl_name][src_file]["declared_in"][decl_file] = dec_val
                    elif src_file == "unknown":
                        if "unknown" in self.funcs[decl_name]:
                            self.funcs[decl_name]["unknown"]["declared_in"][decl_file] = dec_val
                        else:
                            self.funcs[decl_name]["unknown"] = get_unknown_val(decl_file, dec_val)

    def __process_exported(self):
        self.log("Processing exported functions")

        regex = re.compile(r"(\S*) (\S*) signature='([^']*)' (\S*) (\S*)")

        for line in self.extensions["Info"].iter_exported():
            m = regex.match(line)
            if m:
                src_file, func = m.groups()

                # Variables can also be exported
                if func not in self.funcs:
                    continue
                elif src_file not in self.funcs[func]:
                    continue
                self.funcs[func][src_file]["type"] = "exported"

    @staticmethod
    def _get_initial_value():
        return {
            "type": None,
            "defined_on_line": None,
            "signature": None,
            "declared_in": dict()
        }

    def __group_functions_by_file(self):
        self.log("Split functions by file")

        for func in self.funcs:
            for file in self.funcs[func]:
                if file in self.funcs_by_file:
                    self.funcs_by_file[file][func] = self.funcs[func][file]
                else:
                    self.funcs_by_file[file] = {func: self.funcs[func][file]}


def parse(args=sys.argv[1:]):
    conf = parse_args(args)

    c = Functions(conf["work_dir"], conf=conf)
    c.parse(conf["cmds_file"])
