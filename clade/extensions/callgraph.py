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

import functools
import os
import re

from clade.extensions.abstract import Extension
from clade.types.nested_dict import nested_dict, traverse


class Callgraph(Extension):
    requires = ["SrcGraph", "Info", "Functions"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.src_graph = dict()
        self.funcs = dict()

        self.err_log = os.path.join(self.work_dir, "err.log")

        self.callgraph = nested_dict()
        self.callgraph_archive = "callgraph.zip"

        self.calls_by_ptr = nested_dict()
        self.calls_by_ptr_file = "calls_by_ptr.json"

        self.used_in = nested_dict()
        self.used_in_file = "used_in.json"

        self.is_builtin = re.compile(r'(__builtin)|(__compiletime)')

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Generating callgraph")

        self.src_graph = self.extensions["SrcGraph"].load_src_graph()
        self.funcs = self.extensions["Functions"].load_functions()

        self.__process_calls()
        self.__process_calls_by_pointers()
        self.__process_functions_usages()
        self._clean_error_log()

        self.dump_data_by_key(self.callgraph, self.callgraph_archive)
        self.dump_data(self.calls_by_ptr, self.calls_by_ptr_file)
        self.dump_data(self.used_in, self.used_in_file)

        self.src_graph.clear()
        self.funcs.clear()
        self.callgraph.clear()
        self.used_in.clear()

    def load_callgraph(self, files=None):
        return self.load_data_by_key(self.callgraph_archive, files)

    def yield_callgraph(self, files=None):
        yield from self.yield_data_by_key(self.callgraph_archive, files)

    def load_calls_by_ptr(self):
        return self.load_data(self.calls_by_ptr_file)

    def load_used_in(self):
        return self.load_data(self.used_in_file)

    def __process_calls(self):
        is_bad = re.compile(r'__bad')

        for context_file, context_func, func, call_line, call_type, args in self.extensions["Info"].iter_calls():
            # args are excluded from the debug log
            self.debug("Processing function calls: " + " ".join(
                [context_file, context_func, func, call_line, call_type])
            )

            if self.is_builtin.match(func) or (is_bad.match(func) and func not in self.callgraph):
                self.debug("Function {} is bad".format(func))
                continue

            # For each function call there can be many definitions with the same name, defined in different
            # files. Possible_files is a list of them.
            if func in self.funcs:
                possible_files = tuple(f for f in self.funcs[func]
                                       if f != "unknown" and self.funcs[func][f]["type"] in (call_type, "exported"))
            else:
                self._error("Can't find '{}' in Functions".format(func))
                possible_files = []

            # Assign priority number for each possible definition. Examples:
            # 5 means that definition is located in the same file as the call
            # 4 - in the same translation unit
            # 3 - reserved for exported functions (Linux kernel only)
            # 2 - in the object file that is linked with the object file that contains the call
            # 1 - TODO: investigate this case
            # 0 - definition is not found
            index = 5
            for files in (
                    (f for f in possible_files if f == context_file),
                    (f for f in possible_files if self._t_unit_is_common(f, context_file)),
                    (f for f in possible_files if self.funcs[func][f]["type"] == "exported") if call_type == "extern" else tuple(),
                    (f for f in possible_files if self._files_are_linked(f, context_file) and
                        any(self._t_unit_is_common(cf, context_file) for cf in self.funcs[func][f]["declarations"])) if call_type == "extern" else tuple(),
                    (f for f in possible_files if any(self._t_unit_is_common(cf, context_file) for cf in self.funcs[func][f]["declarations"]))
                    if call_type == "extern" else tuple(),
                    ['unknown']):
                matched_files = tuple(files)
                if matched_files:
                    break
                index -= 1

            if len(matched_files) > 1:
                self._error("Multiple matches: {} {}".format(func, context_func))

            for possible_file in matched_files:
                call_val = {
                    'match_type': index,
                }

                if args:
                    call_val["args"] = args

                self.debug("Fuction {} from {} is called in {}:{} in {}".format(
                    func, possible_file, context_file, call_line, context_func
                ))

                self.callgraph[possible_file][func]['called_in'][context_file][context_func][call_line] = call_val

                # Create reversed callgraph
                self.callgraph[context_file][context_func]["calls"][possible_file][func][call_line] = call_val

                if possible_file == "unknown":
                    self._error("Can't match definition: {} {}".format(func, context_file))

        # Keep function types in the callgraph
        for path, func in traverse(self.callgraph, 2):
            if path == "unknown" and (func not in self.funcs or not self.funcs[func].get(path)):
                continue

            self.callgraph[path][func]["type"] = self.funcs[func][path]["type"]

    def __process_calls_by_pointers(self):
        for context_file, context_func, func_ptr, call_line in self.extensions["Info"].iter_calls_by_pointers():
            self.debug("Processing calls by pointers: " + " ".join(
                [context_file, context_func, func_ptr, call_line])
            )

            if func_ptr not in self.calls_by_ptr[context_file][context_func]:
                self.calls_by_ptr[context_file][context_func][func_ptr] = [call_line]
            else:
                self.calls_by_ptr[context_file][context_func][func_ptr].append(call_line)

    def __process_functions_usages(self):
        for context_file, context_func, func, line in self.extensions["Info"].iter_functions_usages():
            self.debug("Processing function usages: " + " ".join(
                [context_file, context_func, func, line])
            )

            if self.is_builtin.match(func):
                continue

            if func not in self.funcs:
                self._error("Use of function without definition: {}".format(func))
                continue

            # For each function call there can be many definitions with the same name, defined in different files.
            # possible_files is a list of them.
            possible_files = tuple(f for f in self.funcs[func] if f != "unknown")

            if len(possible_files) == 0:
                self._error("No possible definitions for use: {}".format(func))
                continue

            # Assign priority number for each possible definition. Examples:
            # 3 means that definition is located in the same file as the call
            # 2 - in the same translation unit
            # 1 - in the object file that is linked with the object file that contains the call
            # 0 - definition is not found
            index = 3
            for files in (
                    (f for f in possible_files if f == context_file),
                    (f for f in possible_files if self._t_unit_is_common(f, context_file)),
                    (f for f in possible_files if self._files_are_linked(f, context_file)),
                    ['unknown']):
                matched_files = tuple(files)
                if matched_files:
                    break
                index -= 1
            else:
                raise RuntimeError("We do not expect any other file class")

            if len(matched_files) > 1:
                self._error("Multiple matches for use: {} call in {}".format(func, context_func))

            for possible_file in matched_files:
                if func not in self.used_in[possible_file]:
                    self.used_in[possible_file][func] = {"used_in_file": nested_dict(), "used_in_func": nested_dict()}

                if context_func == "NULL":
                    self.used_in[possible_file][func]["used_in_file"][context_file][line] = index
                else:
                    self.used_in[possible_file][func]["used_in_func"][context_file][context_func][line] = index

                if possible_file == "unknown":
                    self._error("Can't match definition for use: {} {}".format(func, context_file))

    @functools.lru_cache()
    def _t_unit_is_common(self, file1, file2):
        r = (
            file1 in self.src_graph
            and file2 in self.src_graph
            and len(
                set(self.src_graph[file1]["compiled_in"])
                & set(self.src_graph[file2]["compiled_in"])
            )
            > 0
        )

        self.debug("{!r} and {!r} are from the same translation unit".format(
            file1, file2)
        )

        return r

    @functools.lru_cache()
    def _files_are_linked(self, file1, file2):
        r = (
            file1 in self.src_graph
            and file2 in self.src_graph
            and len(
                set(self.src_graph[file1]["used_by"])
                & set(self.src_graph[file2]["used_by"])
            )
            > 0
        )

        self.debug("{!r} and {!r} are linked".format(file1, file2))

        return r

    def _error(self, msg):
        """Print an error message."""
        self.debug(msg)

        os.makedirs(self.work_dir, exist_ok=True)

        with open(self.err_log, "a") as err_fh:
            err_fh.write("{}\n".format(msg))

    def _clean_error_log(self):
        """Remove duplicate error messages."""

        if not os.path.isfile(self.err_log):
            return

        dup_lines = dict()

        with open(self.err_log, "r") as output_fh:
            with open(self.err_log + ".temp", "w") as temp_fh:
                for line in output_fh:
                    if line not in dup_lines:
                        temp_fh.write(line)
                        dup_lines[line] = 1

        os.remove(self.err_log)
        os.rename(self.err_log + ".temp", self.err_log)
