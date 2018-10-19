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
import sys

from clade.extensions.abstract import Extension
from clade.extensions.utils import common_main


class Callgraph(Extension):
    requires = ["SrcGraph", "Info", "Functions"]

    def __init__(self, work_dir, conf=None, preset="base"):
        super().__init__(work_dir, conf, preset)

        self.src_graph = dict()
        self.funcs = dict()

        self.err_log = os.path.join(self.work_dir, "err.log")

        self.callgraph = dict()
        self.callgraph_file = "callgraph.json"
        self.callgraph_folder = "callgraph"

        self.calls_by_ptr = dict()
        self.calls_by_ptr_file = "calls_by_ptr.json"

        self.used_in = dict()
        self.used_in_file = "used_in.json"

    @Extension.prepare
    def parse(self, cmds_file):
        self.src_graph = self.extensions["SrcGraph"].load_src_graph()
        self.funcs = self.extensions["Functions"].load_functions()

        self.__process_calls()
        self.__process_calls_by_pointers()
        self.__process_functions_usages()
        self._clean_error_log()

        self.log("Dump parsed data")
        self.dump_data_by_key(self.callgraph, self.callgraph_folder)
        self.dump_data(self.callgraph, self.callgraph_file)
        self.dump_data(self.calls_by_ptr, self.calls_by_ptr_file)
        self.dump_data(self.used_in, self.used_in_file)
        self.log("Finish")

    def load_callgraph(self, files=None):
        if files:
            return self.load_data_by_key(self.callgraph_folder, files)
        else:
            return self.load_data(self.callgraph_file)

    def load_calls_by_ptr(self):
        return self.load_data(self.calls_by_ptr_file)

    def load_used_in(self):
        return self.load_data(self.used_in_file)

    def __process_calls(self):
        self.log("Processing calls")

        regex = re.compile(r'(\S*) (\S*) (\S*) (\S*) (\S*) (.*)')

        is_builtin = re.compile(r'(__builtin)|(__compiletime)')
        is_bad = re.compile(r'__bad')

        args_regex = re.compile(r"actual_arg_func_name(\d+)=\s*(\w+)\s*")

        for line in self.extensions["Info"].iter_calls():
            m = regex.match(line)

            if not m:
                raise RuntimeError("CIF output has unexpected format")

            context_file, context_func, func, call_line, call_type, args = m.groups()

            if is_builtin.match(func) or (is_bad.match(func) and func not in self.callgraph):
                continue

            args = args_regex.findall(args)

            # For each function call there can be many definitions with the same name, defined in different
            # files. Possible_files is a list of them.
            if func in self.funcs:
                possible_files = tuple(f for f in self.funcs[func]
                                       if f is not "unknown" and self.funcs[func][f]["type"] in (call_type, "exported"))
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
                    (f for f in possible_files if self.funcs[func][f]["type"] == "exported") if call_type == "global" else tuple(),
                    (f for f in possible_files if self._files_are_linked(f, context_file) and
                        any(self._t_unit_is_common(cf, context_file) for cf in self.funcs[func][f]["declarations"])) if call_type == "global" else tuple(),
                    (f for f in possible_files if any(self._t_unit_is_common(cf, context_file) for cf in self.funcs[func][f]["declarations"]))
                    if call_type == "global" else tuple(),
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

                if possible_file not in self.callgraph:
                    self.callgraph[possible_file] = dict()

                if func not in self.callgraph[possible_file]:
                    val = {"called_in": dict()}
                    val['called_in'] = {context_file: {context_func: {call_line: call_val}}}
                    self.callgraph[possible_file][func] = val
                elif 'called_in' not in self.callgraph[possible_file][func]:
                    self.callgraph[possible_file][func]['called_in'] = {context_file: {context_func: {call_line: call_val}}}
                elif context_file not in self.callgraph[possible_file][func]['called_in']:
                    self.callgraph[possible_file][func]['called_in'][context_file] = {context_func: {call_line: call_val}}
                elif context_func not in self.callgraph[possible_file][func]['called_in'][context_file]:
                    self.callgraph[possible_file][func]['called_in'][context_file][context_func] = {call_line: call_val}
                else:
                    self.callgraph[possible_file][func]['called_in'][context_file][context_func][call_line] = call_val

                # Create reversed callgraph
                if context_file not in self.callgraph:
                    self.callgraph[context_file] = {context_func: {"calls": {possible_file: {func: {call_line: call_val}}}}}
                elif context_func not in self.callgraph[context_file]:
                    self.callgraph[context_file][context_func] = {"calls": {possible_file: {func: {call_line: call_val}}}}
                elif "calls" not in self.callgraph[context_file][context_func]:
                    self.callgraph[context_file][context_func]["calls"] = {possible_file: {func: {call_line: call_val}}}
                elif possible_file not in self.callgraph[context_file][context_func]["calls"]:
                    self.callgraph[context_file][context_func]["calls"][possible_file] = {func: {call_line: call_val}}
                elif func not in self.callgraph[context_file][context_func]["calls"][possible_file]:
                    self.callgraph[context_file][context_func]["calls"][possible_file][func] = {call_line: call_val}
                else:
                    self.callgraph[context_file][context_func]["calls"][possible_file][func][call_line] = call_val

                if possible_file == "unknown":
                    self._error("Can't match definition: {} {}".format(func, context_file))

        for path, funcs in self.callgraph.items():
            for func, desc in funcs.items():
                if path == 'unknown' and (func not in self.funcs or not self.funcs[func].get(path)):
                    continue
                desc['type'] = self.funcs[func][path].get('type')

    def __process_calls_by_pointers(self):
        self.log("Processing calls by pointers")

        regex = re.compile(r'(\S*) (\S*) (\S*) (\S*)')

        for line in self.extensions["Info"].iter_calls_by_pointers():
            m = regex.match(line)

            if not m:
                raise RuntimeError("CIF output has unexpected format")

            context_file, context_func, func_ptr, call_line = m.groups()

            if context_file not in self.calls_by_ptr:
                self.calls_by_ptr[context_file] = {context_func: dict()}

            if context_func not in self.calls_by_ptr[context_file]:
                self.calls_by_ptr[context_file][context_func] = {func_ptr: [call_line]}

            if func_ptr not in self.calls_by_ptr[context_file][context_func]:
                self.calls_by_ptr[context_file][context_func][func_ptr] = [call_line]
            else:
                self.calls_by_ptr[context_file][context_func][func_ptr].append(call_line)

    def __process_functions_usages(self):
        self.log("Processing functions usages")

        is_builtin = re.compile(r'(__builtin)|(__compiletime)')

        for file_line in self.extensions["Info"].iter_functions_usages():
            m = re.match(r'(\S*) (\S*) (\S*) (\S*)', file_line)
            if m:
                context_file, context_func, func, line = m.groups()

                if is_builtin.match(func):
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
                    if possible_file not in self.used_in:
                        val = {"used_in_file": dict(), "used_in_func": dict()}

                        if context_func:
                            val["used_in_func"][context_file] = {context_func: {line: index}}
                        else:
                            val["used_in_file"] = {context_file: {line: index}}

                        self.used_in[possible_file] = {func: val}
                    else:
                        if func not in self.used_in[possible_file]:
                            self.used_in[possible_file][func] = {"used_in_file": dict(), "used_in_func": dict()}

                        if context_func == "NULL":
                            if context_file in self.used_in[possible_file][func]["used_in_file"]:
                                self.used_in[possible_file][func]["used_in_file"][context_file][line] = index
                            else:
                                self.used_in[possible_file][func]["used_in_file"][context_file] = {line: index}
                        else:
                            if context_file not in self.used_in[possible_file][func]["used_in_func"]:
                                self.used_in[possible_file][func]["used_in_func"][context_file] = {
                                    context_func: {
                                        line: index
                                    }
                                }
                            elif context_func not in self.used_in[possible_file][func]["used_in_func"][context_file]:
                                self.used_in[possible_file][func]["used_in_func"][context_file][context_func] = \
                                    {line: index}
                            else:
                                self.used_in[possible_file][func]["used_in_func"][context_file][context_func][line] = index

                    if possible_file == "unknown":
                        self._error("Can't match definition for use: {} {}".format(func, context_file))

    def _t_unit_is_common(self, file1, file2, cache=dict()):
        file1, file2 = sorted([file1, file2])

        if file1 in cache and file2 in cache[file1]:
            return cache[file1][file2]

        graph = self.src_graph
        result = file1 in graph and file2 in graph and len(set(graph[file1]["compiled_in"]) & set(graph[file2]["compiled_in"])) > 0

        if file1 not in cache:
            cache[file1] = {file2: result}
        else:
            cache[file1][file2] = result

        return result

    def _files_are_linked(self, file1, file2, cache=dict()):
        file1, file2 = sorted([file1, file2])

        if file1 in cache and file2 in cache[file1]:
            return cache[file1][file2]

        graph = self.src_graph
        result = file1 in graph and file2 in graph and len(set(graph[file1]["used_by"]) & set(graph[file2]["used_by"])) > 0

        if file1 not in cache:
            cache[file1] = {file2: result}
        else:
            cache[file1][file2] = result

        return result

    def _error(self, msg):
        """
        Prints an error message
        """
        if not os.path.isdir(self.work_dir):
            os.makedirs(self.work_dir)

        with open(self.err_log, "a") as err_fh:
            err_fh.write("{}\n".format(msg))

    def _clean_error_log(self):
        """
        Removes duplicate error messages
        """
        if not os.path.isfile(self.err_log):
            return

        self.log("Cleaning error log")

        dup_lines = dict()

        with open(self.err_log, "r") as output_fh:
            with open(self.err_log + ".temp", "w") as temp_fh:
                for line in output_fh:
                    if line not in dup_lines:
                        temp_fh.write(line)
                        dup_lines[line] = 1

        os.remove(self.err_log)
        os.rename(self.err_log + ".temp", self.err_log)


def main(args=sys.argv[1:]):
    common_main(Callgraph, args)
