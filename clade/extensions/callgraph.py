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
import shutil
import sys

from clade.extensions.abstract import Extension
from clade.extensions.common import parse_args
from clade.extensions.initializations import parse_initialization_functions
from clade.extensions.utils import nested_dict
from clade.cmds import load_cmds


class Callgraph(Extension):
    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        self.requires = ["Info", "SrcGraph"]

        super().__init__(work_dir, conf)

        self.callgraph = nested_dict()
        self.callgraph_file = os.path.join(self.work_dir, "callgraph.json")
        self.callgraph_dir = os.path.join(self.work_dir, "callgraph")

        self.variables = nested_dict()
        self.variables_file = os.path.join(self.work_dir, "variables.json")

        self.macros = nested_dict()
        self.macros_file = os.path.join(self.work_dir, "macros.json")

        self.typedefs = nested_dict()
        self.typedefs_file = os.path.join(self.work_dir, "typedefs.json")

        self.src_graph = dict()
        self._values = set()

        self.allowed_macros = set(self.conf.get('allowed_macros', []))

        self.err_log = os.path.join(self.work_dir, "err.log")

    def parse(self, cmds):
        self.parse_prerequisites(cmds)

        self.src_graph = self.extensions["SrcGraph"].load_src_graph()

        # TODO: many stages below need optimizations, I marked them below
        self.__process_execution()
        self.__process_declarations()
        self.__process_exported()
        self.__process_typedefs()
        # TODO: 7514.2s on Linux. Expensive files determination
        self.__process_call()
        self.__process_callp()
        self.__process_init_global()
        # TODO: 26668.3s on Linux. Need to reimplement collection to check used functions and variables. The code is a mess.
        # And in LKVOG further work with global variables is extremly inefficient.
        self.__process_use_var()
        self.__process_use_func()
        self.__reverse_callgraph()
        self.__clean_error_log()
        self.__process_macros()

        self.dump_callgraph()
        self.dump_data(self.variables, self.variables_file)
        self.dump_data(self.macros, self.macros_file)
        self.dump_data(self.typedefs, self.typedefs_file)

    def __callgraph_file_name(self, file):
        return os.path.join(os.path.normpath(self.callgraph_dir + os.path.sep + os.path.dirname(file)),
                            os.path.basename(file) + '.callgraph.json')

    def dump_callgraph(self):
        self.log("Dump callgraph")

        callgraph = self.callgraph
        out = self.callgraph_dir

        self.debug("Print detailed callgraph to {!r}".format(out))

        index_files = dict()

        if os.path.isdir(out):
            shutil.rmtree(out)

        for func in callgraph:
            for file in callgraph[func]:
                if file not in index_files:
                    index_files[file] = [func]
                else:
                    index_files[file].append(func)

        for file in index_files:
            tmp_dict = {func: {file: callgraph[func][file]} for func in index_files[file]}
            new_name = self.__callgraph_file_name(file)
            os.makedirs(os.path.dirname(new_name), exist_ok=True)

            self.dump_data(tmp_dict, new_name)

        file_name = self.callgraph_file

        self.debug("Print reduced callgraph to {!r}".format(file_name))

        for func in callgraph:
            for file in callgraph[func]:
                for tag in ('defined_on_line', 'signature'):
                    if tag in callgraph[func][file]:
                        del callgraph[func][file][tag]

                if 'called_in' in callgraph[func][file]:
                    for called in callgraph[func][file]['called_in']:
                        for scope in callgraph[func][file]['called_in'][called]:
                            callgraph[func][file]['called_in'][called][scope] = \
                                {'cc_in_file': callgraph[func][file]['called_in'][called][scope]['cc_in_file']}

                if 'calls' in callgraph[func][file]:
                    for called in callgraph[func][file]['calls']:
                        for scope in callgraph[func][file]['calls'][called]:
                            callgraph[func][file]['calls'][called][scope] = {}

        self.dump_data(callgraph, file_name)

    def load_detailed_callgraph(self, files=None):
        final = dict()

        for file in files:
            filename = self.__callgraph_file_name(file)

            if not os.path.isfile(filename):
                self.warning("There is no data for the requested file: {!r}".format(filename))
            else:
                data = self.load_json(filename)

                for func, files_data in data.items():
                    if func not in final:
                        final[func] = files_data
                    else:
                        final[func].update(files_data)

        return final

    def load_callgraph(self):
        return self.load_json(self.callgraph_file)

    def load_variables(self):
        return self.load_json(self.variables_file)

    def load_macros(self):
        return self.load_json(self.macros_file)

    def load_typedefs(self):
        return self.load_json(self.typedefs_file)

    def __process_execution(self):
        # TODO: implement proper getter methods
        execution = self.extensions["Info"].execution

        if not os.path.isfile(execution):
            return

        self.log("Processing function definitions")

        regex = re.compile(r"(\S*) (\S*) signature='([^']*)' (\S*) (\S*)")

        with open(execution, "r") as exe_fh:
            for line in exe_fh:
                m = regex.match(line)
                if m:
                    src_file, func, signature, def_line, func_type = m.groups()

                    if func in self.callgraph and src_file in self.callgraph[func]:
                        self.__error("Function is defined more than once: '{}' '{}'".format(func, src_file))
                        continue

                    self.callgraph[func][src_file]["type"] = func_type
                    self.callgraph[func][src_file]["defined_on_line"] = def_line
                    self.callgraph[func][src_file]["signature"] = signature

    def __process_declarations(self):
        decl = self.extensions["Info"].decl

        if not os.path.isfile(decl):
            return

        self.log("Processing declarations")

        regex = re.compile(r"(\S*) (\S*) signature='([^']*)' (\S*) (\S*)")

        with open(decl, "r") as decl_fh:
            for line in decl_fh:
                m = regex.match(line)
                if m:
                    decl_file, decl_name, signature, def_line, type = m.groups()

                    if decl_name not in self.callgraph:
                        self.callgraph[decl_name]["unknown"]["declared_in"][decl_file] = {
                            'def_line': def_line,
                            'signature': signature,
                            'type': type
                        }
                        continue

                    if decl_file not in self.src_graph:
                        self.__error("Not in source graph: {}".format(decl_file))

                    for src_file in self.callgraph[decl_name]:
                        if src_file not in self.src_graph:
                            self.__error("Not in source graph: {}".format(src_file))

                        if src_file == decl_file:
                            self.callgraph[decl_name][src_file]["declared_in"][decl_file] = {
                                'def_line': def_line,
                                'signature': signature,
                            }
                        elif (src_file in self.src_graph and decl_file in self.src_graph and
                              list(set(self.src_graph[src_file]["compiled_in"]) &
                                   set(self.src_graph[decl_file]["compiled_in"]))):
                            self.callgraph[decl_name][src_file]["declared_in"][decl_file] = {
                                'def_line': def_line,
                                'signature': signature
                            }
                        elif src_file == "unknown":
                            self.callgraph[decl_name]["unknown"]["declared_in"][decl_file] = {
                                'def_line': def_line,
                                'signature': signature
                            }

    def __process_exported(self):
        exported_file = self.extensions["Info"].exported

        if not os.path.isfile(exported_file):
            return

        self.log("Processing exported functions")

        regex = re.compile(r"(\S*) (\S*) signature='([^']*)' (\S*) (\S*)")

        with open(exported_file, "r") as exp_fh:
            for line in exp_fh:
                m = regex.match(line)
                if m:
                    src_file, func = m.groups()

                    # Variables can also be exported
                    if func not in self.callgraph:
                        continue
                    elif src_file not in self.callgraph[func]:
                        continue

                    self.callgraph[func][src_file]["type"] = "exported"

    def __process_macros(self):
        expand_file = self.extensions["Info"].expand

        if not os.path.isfile(expand_file):
            return

        self.log("Processing macros")

        all_args = "(?:\sarg\d+='[^']*')*"
        all_funcs = set(self.callgraph.keys())
        regex = re.compile(r'(\S*) (\S*)({0})'.format(all_args))
        args_extract = r"arg\d+='([^']*)'"
        regex2 = re.compile(args_extract)

        with open(expand_file, "r") as expand_fh:
            for line in expand_fh:
                m = regex.match(line)
                if m:
                    file, func, args = m.groups()

                    args = regex2.findall(args)
                    if func in self.allowed_macros \
                            or set(args) & all_funcs:
                        if file not in self.macros[func]:
                            self.macros[func][file] = {
                                'args': []
                            }

                        self.macros[func][file]["args"].append(args)

    def __process_typedefs(self):
        typedefs_file = self.extensions["Info"].typedefs

        if not os.path.isfile(typedefs_file):
            return

        self.log("Processing typedefs")

        regex = re.compile(r"^declaration: typedef ([^\n]+); path: ([^\n]+)")

        with open(typedefs_file, "r") as fp:
            for line in fp:
                m = regex.match(line)
                if m:
                    declaration, scope_file = m.groups()
                if scope_file not in self.typedefs:
                    self.typedefs[scope_file] = []
                self.typedefs[scope_file].append(declaration)

    def __process_call(self):
        call = self.extensions["Info"].call

        if not os.path.isfile(call):
            return

        self.log("Processing calls")

        all_args = "(?:\sarg\d+='[^']*')*"
        regex = re.compile(r'(\S*) (\S*) (\S*) (\S*) (\S*) (\S*)({0})'.format(all_args))
        args_extract = r"arg\d+='([^']*)'"
        regex1 = re.compile(args_extract)

        with open(call, "r") as call_fh:
            for line in call_fh:
                m = regex.match(line)
                if m:
                    context_file, cc_in_file, context_func, func, call_line, call_type, args = m.groups()
                    args = regex1.findall(args)
                    self.__match_call_and_def(context_file, cc_in_file, context_func, func, call_line, call_type, args)

    def __match_call_and_def(self, context_file, cc_in_file, context_func, func, call_line, call_type, args):
        # TODO: __builtin and __compiletime functions are not included in callgraph. why?
        if re.match(r'(__builtin)|(__compiletime)', func):
            return
        if re.match(r'__bad', func) and func not in self.callgraph:
            return

        if func not in self.callgraph:
            self.callgraph[func]["unknown"]["defined_on_line"] = "unknown"
            self.callgraph[func]["unknown"]["type"] = call_type
            self.callgraph[func]["unknown"]["called_in"][context_func][context_file][call_line] = 0
            self.callgraph[func]["unknown"]["called_in"][context_func][context_file].setdefault("args", [])
            self.callgraph[func]["unknown"]["called_in"][context_func][context_file]["args"].append(args)

            self.__error("Without definition: {}".format(func))
            return

        # For each function call there can be many definitions with the same name, defined in different files.
        # possible_files is a list of them.
        possible_files = []
        for possible_file in self.callgraph[func]:
            if possible_file == "unknown":
                continue
            elif (self.callgraph[func][possible_file]["type"] == call_type or
                  self.callgraph[func][possible_file]["type"] == "exported"):
                possible_files.append(possible_file)

        # If there is no possible definitions:
        if len(possible_files) == 0:
            self.callgraph[func]["unknown"]["defined_on_line"] = "unknown"
            self.callgraph[func]["unknown"]["type"] = call_type
            self.callgraph[func]["unknown"]["called_in"][context_func][context_file][call_line] = 0
            self.callgraph[func]["unknown"]["called_in"][context_func][context_file].setdefault("args", [])
            self.callgraph[func]["unknown"]["called_in"][context_func][context_file]["args"].append(args)

            # It will be a clade's fault until it supports aliases
            if not re.match(r'__mem', func):
                self.__error("No possible definitions: {}".format(func))
        else:
            # Assign priority number for each possible definition. Examples:
            # 5 means that definition is located in the same file as the call
            # 4 - in the same translation unit
            # 3 - in the object file that is linked with the object file that contains the call
            # 2 - reserved for exported functions (Linux kernel only)
            # 1 - TODO: investigate this case
            # 0 - definition is not found
            matched_files = [None] * 6
            for x in range(0, len(matched_files)):
                matched_files[x] = []

            for possible_file in possible_files:
                if self.__files_are_the_same(possible_file, context_file):
                    matched_files[5].append(possible_file)
                elif self.__t_unit_is_common(possible_file, context_file):
                    matched_files[4].append(possible_file)
                elif call_type == "global" and self._files_are_linked(possible_file, context_file):
                    matched_files[3].append(possible_file)
                elif call_type == "global" and self.callgraph[func][possible_file]["type"] == "exported":
                    matched_files[2].append(possible_file)
                elif call_type == "global":
                    for decl_file in self.callgraph[func][possible_file]["declared_in"]:
                        if self.__t_unit_is_common(decl_file, context_file):
                            matched_files[1].append(possible_file)

            matched_files[0].append("unknown")

            for x in range(len(matched_files) - 1, -1, -1):
                if matched_files[x] != []:
                    if len(matched_files[x]) > 1:
                        self.__error("Multiple matches: {} {}".format(func, context_func))
                    for possible_file in matched_files[x]:
                        if context_file not in self.callgraph[func][possible_file]['called_in'][context_func]:
                            self.callgraph[func][possible_file]["called_in"][context_func][context_file] = {
                                'call_line': call_line,
                                'args': [],
                                'cc_in_file': cc_in_file
                            }
                        self.callgraph[func][possible_file]['called_in'][context_func][context_file]['args'].append(args)

                        if possible_file == "unknown":
                            self.callgraph[func][possible_file]["defined_on_line"] = "unknown"
                            self.callgraph[func][possible_file]["type"] = call_type

                            self.__error("Can't match definition: {} {}".format(func, context_file))
                    break

    def __files_are_the_same(self, file1, file2):
        if file1 == file2:
            return True

        return False

    def __t_unit_is_common(self, file1, file2):
        if file1 in self.src_graph and file2 in self.src_graph:
            if list(set(self.src_graph[file1]["compiled_in"]) & set(self.src_graph[file2]["compiled_in"])):
                return True

        return False

    def _files_are_linked(self, file1, file2):
        if file1 in self.src_graph and file2 in self.src_graph:
            if "used_by" in self.src_graph[file1] and "used_by" in self.src_graph[file2]:
                if list(set(self.src_graph[file1]["used_by"]) & set(self.src_graph[file2]["used_by"])):
                    return True

        return False

    def __process_callp(self):
        callp = self.extensions["Info"].callp

        if not os.path.isfile(callp):
            return

        self.log("Processing calls by pointers")

        with open(callp, "r") as callp_fh:
            for line in callp_fh:
                m = re.match(r'(\S*) (\S*) (\S*) (\S*)', line)
                if m:
                    context_file, context_func, func_ptr, call_line = m.groups()

                    self.callgraph[context_func][context_file]["calls_by_pointer"][func_ptr][call_line] = 1

    def __process_init_global(self):
        init_global = self.extensions["Info"].init_global

        if not os.path.isfile(init_global):
            return

        self.log("Processing global variables initializations")

        self.variables = parse_initialization_functions(init_global)

    def __match_var_and_value(self, variables, viewed, var_name, file, origvar_name, original_file):
        if var_name in viewed and file in viewed[var_name]:
            return

        viewed[var_name][file] = 1

        for value in variables[var_name][file]["values"]:
            if variables[var_name][file]["values"][value] == "1":
                self.variables[origvar_name][original_file]["values"][value] = 1
            elif value in variables:
                for possible_file in variables[value]:
                    if self.__files_are_the_same(possible_file, file) or self.__t_unit_is_common(possible_file, file):
                        self.__match_var_and_value(variables, viewed, value, possible_file, origvar_name, original_file)

    def __process_use_func(self):
        use_func = self.extensions["Info"].use_func

        if not os.path.isfile(use_func):
            return

        self.log("Processing functions use")

        with open(use_func, "r") as use_func_fh:
            for file_line in use_func_fh:
                m = re.match(r'(\S*) (\S*) (\S*) (\S*)', file_line)
                if m:
                    context_file = m.group(1)
                    context_func = m.group(2)
                    func = m.group(3)
                    line = m.group(4)

                    self.__match_use_and_def(context_file, context_func, func, line)

    def __process_use_var(self):
        use_var = self.extensions["Info"].use_var

        if not os.path.isfile(use_var):
            return

        self.log("Processing global variables use")

        regex = re.compile(r'(\S*) (\S*) (\S*) (\S*)')

        with open(use_var, "r") as use_var_fh:
            for file_line in use_var_fh:
                m = regex.match(file_line)
                if m:
                    context_file = m.group(1)
                    context_func = m.group(2)
                    var_name = m.group(3)
                    line = m.group(4)

                    # TODO: This is unreachable code that eats a lot of CPU time checking the condition below
                    if var_name in self.variables:
                        for possible_file in self.variables[var_name]:
                            if (self.__files_are_the_same(possible_file, context_file) or
                                    self.__t_unit_is_common(possible_file, context_file) or
                                    self._files_are_linked(possible_file, context_file)):
                                for func in self.variables[var_name][possible_file]["values"]:
                                    self.__match_use_and_def(context_file, context_func, func, line)

    def __match_use_and_def(self, context_file, context_func, func, line):
        if re.match(r'(__builtin)|(__compiletime)', func):
            return

        if func not in self.callgraph:
            self.__error("Use of function without definition: {}".format(func))
            return

        possible_files = []
        for possible_file in self.callgraph[func]:
            if possible_file == "unknown":
                continue
            possible_files.append(possible_file)

        if len(possible_files) == 0:
            self.__error("No possible definitions for use: {}".format(func))
        else:
            matched_files = [None] * 4
            for x in range(0, len(matched_files)):
                matched_files[x] = []

            for possible_file in possible_files:
                if self.__files_are_the_same(possible_file, context_file):
                    matched_files[3].append(possible_file)
                elif self.__t_unit_is_common(possible_file, context_file):
                    matched_files[2].append(possible_file)
                elif self._files_are_linked(possible_file, context_file):
                    matched_files[1].append(possible_file)

            matched_files[0].append("unknown")

            for x in range(len(matched_files) - 1, -1, -1):
                if matched_files[x] != []:
                    if len(matched_files[x]) > 1:
                        self.__error("Multiple matches for use: {} call in {}".format(func, context_func))
                    for possible_file in matched_files[x]:
                        if context_func == "NULL":
                            self.callgraph[func][possible_file]["used_in_file"][context_file][line] = x
                        else:
                            self.callgraph[func][possible_file]["used_in_func"][context_func][context_file][line] = x

                        if possible_file == "unknown":
                            self.__error("Can't match definition for use: {} {}".format(func, context_file))
                    break

    def __reverse_callgraph(self):
        self.log("Creating reversed callgraph")

        for func in self.callgraph:
            for file in self.callgraph[func]:
                if "called_in" in self.callgraph[func][file]:
                    for context_func in self.callgraph[func][file]["called_in"]:
                        for context_file in self.callgraph[func][file]["called_in"][context_func]:
                            if context_func not in self.callgraph:
                                self.debug("There is no context func {0} for 'called_in".format(context_func))
                            self.callgraph[context_func][context_file]["calls"][func][file] = self.callgraph[func][file]["called_in"][context_func][context_file]
                if "used_in_func" in self.callgraph[func][file]:
                    for context_func in self.callgraph[func][file]["used_in_func"]:
                        for context_file in self.callgraph[func][file]["used_in_func"][context_func]:
                            if context_func not in self.callgraph:
                                self.debug("There is no context func {0} for 'used_in_func'".format(context_func))
                            self.callgraph[context_func][context_file]["uses"][func][file] = self.callgraph[func][file]["used_in_func"][context_func][context_file]

    def __error(self, str):
        """
        Prints an error message
        """

        if not os.path.isdir(self.work_dir):
            os.makedirs(self.work_dir)

        with open(self.err_log, "a") as err_fh:
            err_fh.write("{}\n".format(str))

    def __clean_error_log(self):
        """
        Removes duplicate error messages
        """

        if (not os.path.isfile(self.err_log)):
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


def parse(args=sys.argv[1:]):
    args = parse_args(args)

    c = Callgraph(args.work_dir, conf={"log_level": args.log_level})
    if not c.is_parsed():
        c.parse(load_cmds(args.cmds_json))
