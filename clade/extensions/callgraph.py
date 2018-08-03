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
import time

from clade.extensions.abstract import Extension
from clade.extensions.common import parse_args
from clade.extensions.initializations import parse_initialization_functions
from clade.cmds import load_cmds


is_buildin = re.compile(r'(__builtin)|(__compiletime)')
is_bad = re.compile(r'__bad')


class Callgraph(Extension):

    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        self.requires = ["Info", "SrcGraph"]

        super().__init__(work_dir, conf)

        self.callgraph = dict()
        self.variables = dict()
        self.macros = dict()
        self.typedefs = dict()
        self.src_graph = dict()

        self.err_log = os.path.join(self.work_dir, "err.log")
        self.callgraph_dir = os.path.join(self.work_dir, "callgraph")
        self.callgraph_file = os.path.join(self.work_dir, "callgraph.json")

    def parse(self, cmds):
        def evaluate(stage_method, name):
            begin_time = time.time()
            stage_method()
            work_time = round(time.time() - begin_time, 2)
            self.log("Stage of {} finished and lasted {}s".format(name, work_time))

        self.parse_prerequisites(cmds)
        self.src_graph = self.extensions["SrcGraph"].load_src_graph()
        stages = [
            (self.__process_execution, "processing functions definitions"),
            (self.__process_declarations, "processing functions declarations"),
            (self.__process_exported, "processing export funcitons"),
            (self.__process_call, "processing explicit function calls"),
            (self.__process_callp, "processing function pointer calls"),
            (self.__process_use_func, "processing function pointers arithmetic"),
            (self.__process_init_global, "processing global variables initializations"),
            (self.dump_variables, "dumping global variables initializations to disk"),
            (self.dump_callgraph, "dumping callgraph to disk"),
            (self.__clean_error_log, "clean errors log"),
            (self.__process_macros, "processing macros"),
            (self.dump_macros, "dumping macros to disk"),
            (self.__process_typedefs, "processing type definitions"),
            (self.dump_typedefs, "dumping type definitions to disk")
        ]

        for method, stage in stages:
            evaluate(method, stage)

    def dump_callgraph(self):
        self.log("Dump callgraph")

        callgraph = self.callgraph
        out = self.callgraph_dir

        self.debug("Print detailed callgraph to {!r}".format(out))

        index_files = dict()

        if os.path.isdir(out):
            shutil.rmtree(out)

        # Collect reversed information about files
        for func in callgraph:
            for file in callgraph[func]:
                if file not in index_files:
                    index_files[file] = [func]
                else:
                    index_files[file].append(func)

        # Save full data with arguments
        for file in index_files:
            tmp_dict = {func: {file: callgraph[func][file]} for func in index_files[file]}
            new_name = self.__src_related_file_name(file, '.callgraph.json')
            os.makedirs(os.path.dirname(new_name), exist_ok=True)
            self.dump_data(tmp_dict, new_name)
        file_name = self.callgraph_file

        self.debug("Print reduced callgraph to {!r}".format(file_name))
        for func in callgraph:
            for file in callgraph[func]:
                for tag in ('defined_on_line', 'signature', 'uses', 'used_in_file', 'used_in_func', 'used_in_vars',
                            'calls_by_pointer'):
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
        del self.callgraph

    def load_callgraph(self):
        return self.load_data(self.callgraph_file)

    def load_detailed_callgraph(self, files):
        final = dict()

        for file in files:
            filename = self.__src_related_file_name(file, '.callgraph.json')
            if not os.path.isfile(filename):
                self.warning("There is no data for the requested file: {!r}".format(filename))
            else:
                data = self.load_data(filename)
                for func, files_data in data.items():
                    if func not in final:
                        final[func] = files_data
                    else:
                        final[func].update(files_data)
        return final

    def load_variables(self, files):
        return self.__load_collection('.vars.json', files)

    def dump_variables(self):
        self.__dump_collection(self.variables, '.vars.json')

    def load_macros(self, files):
        return self.__load_collection('.macros.json', files)

    def dump_macros(self):
        self.__dump_collection(self.macros, '.macros.json')

    def load_typedefs(self, files):
        return self.__load_collection('.typedefs.json', files)

    def dump_typedefs(self):
        self.__dump_collection(self.typedefs, '.typedefs.json')

    def __process_execution(self):
        # TODO: implement proper getter methods
        execution = self.extensions["Info"].execution

        if not os.path.isfile(execution):
            return

        self.log("Processing function definitions")
        regex = re.compile(r"(\S*) (\S*) signature='([^']*)' (\S*) (\S*)")

        initial_data = self.__cg_initial_value
        with open(execution, "r") as exe_fh:
            for line in exe_fh:
                m = regex.match(line)
                if m:
                    src_file, func, signature, def_line, func_type = m.groups()

                    if func in self.callgraph and src_file in self.callgraph[func]:
                        self.__error("Function is defined more than once: '{}' '{}'".format(func, src_file))
                    else:
                        val = initial_data()
                        val.update({"type": func_type, "defined_on_line": def_line, "signature": signature})
                        if func in self.callgraph:
                            self.callgraph[func][src_file] = val
                        else:
                            self.callgraph[func] = {src_file: val}

    def __process_declarations(self):
        decl = self.extensions["Info"].decl
        if not os.path.isfile(decl):
            return

        self.log("Processing declarations")

        regex = re.compile(r"(\S*) (\S*) signature='([^']*)' (\S*) (\S*)")

        # This helps improve performance
        init_value = self.__cg_initial_value
        src_graph = self.src_graph
        callgraph = self.callgraph
        is_common = self.__t_unit_is_common
        with open(decl, "r") as decl_fh:
            for line in decl_fh:
                m = regex.match(line)
                if m:
                    decl_file, decl_name, decl_signature, decl_line, decl_type = m.groups()
                    dec_val = {
                        'signature': decl_signature,
                        'def_line': decl_line,
                        'type': decl_type,
                        "used_in_func": dict(),
                    }
                    if decl_name not in callgraph:
                        val = init_value()
                        val["declared_in"][decl_file] = dec_val
                        callgraph[decl_name] = {"unknown": val}
                        continue

                    if decl_file not in src_graph:
                        self.__error("Not in source graph: {}".format(decl_file))

                    for src_file in callgraph[decl_name]:
                        if src_file not in src_graph:
                            self.__error("Not in source graph: {}".format(src_file))

                        if src_file == decl_file or is_common(src_file, decl_file):
                            callgraph[decl_name][src_file]["declared_in"][decl_file] = dec_val
                        elif src_file == "unknown":
                            if "unknown" in callgraph[decl_name]:
                                callgraph[decl_name]["unknown"]["declared_in"][decl_file] = dec_val
                            else:
                                val = init_value()
                                val["declared_in"][decl_file] = dec_val
                                callgraph[decl_name]["unknown"] = val

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

    def __process_typedefs(self):
        typedefs_file = self.extensions["Info"].typedefs
        if not os.path.isfile(typedefs_file):
            return

        self.log("Processing typedefs")
        regex = re.compile(r"^declaration: typedef ([^\n]+); path: ([^\n]+)")
        typedefs = self.typedefs
        with open(typedefs_file, "r") as fp:
            for line in fp:
                m = regex.match(line)
                if m:
                    declaration, scope_file = m.groups()
                    if scope_file not in self.typedefs:
                        typedefs[scope_file] = [declaration]
                    elif declaration not in typedefs[scope_file]:
                        typedefs[scope_file].append(declaration)

    def __process_call(self):
        call = self.extensions["Info"].call

        if not os.path.isfile(call):
            return

        self.log("Processing calls")
        all_args = "(?:\sarg\d+='[^']*')*"
        regex = re.compile(r'(\S*) (\S*) (\S*) (\S*) (\S*) (\S*)({0})'.format(all_args))
        args_extract = r"arg\d+='([^']*)'"
        regex1 = re.compile(args_extract)

        callgraph = self.callgraph
        init_val = self.__cg_initial_value
        is_common = self.__t_unit_is_common
        are_linked = self.__files_are_linked
        with open(call, "r") as call_fh:
            cached = dict()
            for line in call_fh:
                m = regex.match(line)
                if m:
                    context_file, cc_in_file, context_func, func, call_line, call_type, args = m.groups()
                    if is_buildin.match(func) or (is_bad.match(func) and func not in callgraph):
                        continue
                    args = regex1.findall(args)
                    args = args if any(map(lambda i: i != '0', args)) else None
                    if func not in callgraph:
                        val = init_val()
                        description = callgraph.setdefault(func, {'unknown': val})
                    else:
                        description = callgraph[func]
                    if func in cached and context_file in cached[func] and call_type in cached[func][context_file]:
                        files = cached[func][context_file][call_type]
                    else:
                        # For each function call there can be many definitions with the same name, defined in different
                        # files. Possible_files is a list of them.
                        possible_files = tuple(f for f in description if
                                               f != "unknown" and description[f]["type"] in (call_type, "exported"))

                        # Assign priority number for each possible definition. Examples:
                        # 5 means that definition is located in the same file as the call
                        # 4 - in the same translation unit
                        # 3 - in the object file that is linked with the object file that contains the call
                        # 2 - reserved for exported functions (Linux kernel only)
                        # 1 - TODO: investigate this case
                        # 0 - definition is not found
                        for matched_files in (files for files in (
                                tuple(f for f in possible_files if f == context_file),
                                tuple(f for f in possible_files if is_common(f, context_file)),
                                tuple(f for f in possible_files if are_linked(f, context_file))
                                if call_type == "global" else tuple(),
                                tuple(f for f in possible_files if description[f]["type"] == "exported")
                                if call_type == "global" else tuple(),
                                tuple(f for f in possible_files
                                      if any(is_common(cf, context_file) for cf in description[f]["declared_in"]))
                                if call_type == "global" else tuple(),
                                ('unknown',)) if len(files) > 0):
                            files = matched_files
                            break

                        # Save cache
                        if func not in cached:
                            cached[func] = {context_file: {call_type: files}}
                        elif context_file not in cached[func]:
                            cached[func][context_file] = {call_type: files}
                        elif call_type not in cached[func][context_file]:
                            cached[func][context_file][call_type] = files

                    if len(files) > 1:
                        self.__error("Multiple matches: {} {}".format(func, context_func))
                    for possible_file in files:
                        if possible_file in description and \
                                context_func in description[possible_file]['called_in'] and \
                                context_file in description[possible_file]['called_in'][context_func] and \
                                args is not None:
                            description[possible_file]['called_in'][context_func][context_file]['args'].append(args)
                        else:
                            call_val = {
                                'used_in_func': dict(),
                                'call_line': call_line,
                                'cc_in_file': cc_in_file,
                                'args': [] if args is None else [args]
                            }
                            if possible_file not in description:
                                val = init_val()
                                val['called_in'] = {context_func: {context_file: call_val}}
                                description[possible_file] = val
                            elif context_func not in description[possible_file]['called_in']:
                                description[possible_file]['called_in'][context_func] = {context_file: call_val}
                            else:
                                description[possible_file]['called_in'][context_func][context_file] = call_val

                        # Set the same object if it is not there already
                        calls = self.callgraph[context_func][context_file]["calls"]
                        if func not in calls:
                            calls[func] = {possible_file: description[possible_file]["called_in"][context_func][context_file]}
                        elif possible_file not in calls[func]:
                            calls[func][possible_file] = description[possible_file]["called_in"][context_func][context_file]

                        if possible_file == "unknown":
                            description[possible_file]["defined_on_line"] = "unknown"
                            description[possible_file]["type"] = call_type
                            self.__error("Can't match definition: {} {}".format(func, context_file))

    def __process_callp(self):
        callp = self.extensions["Info"].callp
        if not os.path.isfile(callp):
            return

        self.log("Processing calls by pointers")
        callgraph = self.callgraph
        init_val = self.__cg_initial_value
        with open(callp, "r") as callp_fh:
            for line in callp_fh:
                m = re.match(r'(\S*) (\S*) (\S*) (\S*)', line)
                if m:
                    context_file, context_func, func_ptr, call_line = m.groups()
                    if context_func not in callgraph:
                        val = init_val()
                        description = callgraph.setdefault(context_func, {'unknown': val})
                    else:
                        description = callgraph[context_func]

                    if context_file not in description:
                        val = init_val()
                        description[context_file] = val
                        val["calls_by_pointer"] = {func_ptr: {call_line: 1}}
                    elif func_ptr not in description[context_file]["calls_by_pointer"]:
                        description[context_file]["calls_by_pointer"][func_ptr] = {call_line: 1}
                    else:
                        description[context_file]["calls_by_pointer"][func_ptr][call_line] = 1

    def __process_use_func(self):
        use_func = self.extensions["Info"].use_func

        if not os.path.isfile(use_func):
            return

        self.log("Processing functions use")

        cached = dict()
        # This helps performance
        callgraph = self.callgraph
        is_common = self.__t_unit_is_common
        are_linked = self.__files_are_linked
        init_val = self.__cg_initial_value
        with open(use_func, "r") as use_func_fh:
            for file_line in use_func_fh:
                m = re.match(r'(\S*) (\S*) (\S*) (\S*)', file_line)
                if m:
                    context_file = m.group(1)
                    context_func = m.group(2)
                    func = m.group(3)
                    line = m.group(4)
                    if is_buildin.match(func):
                        continue
                    if func not in callgraph:
                        self.__error("Use of function without definition: {}".format(func))
                        continue
                    else:
                        description = callgraph[func]

                    if func in cached and context_file in cached[func]:
                        files, index = cached[func][context_file]
                    else:
                        # For each function call there can be many definitions with the same name, defined in different files.
                        # possible_files is a list of them.
                        possible_files = tuple(f for f in description if f != "unknown")
                        if len(possible_files) == 0:
                            self.__error("No possible definitions for use: {}".format(func))
                            continue

                        # Assign priority number for each possible definition. Examples:
                        # 5 means that definition is located in the same file as the call
                        # 4 - in the same translation unit
                        # 3 - in the object file that is linked with the object file that contains the call
                        # 2 - reserved for exported functions (Linux kernel only)
                        # 1 - TODO: investigate this case
                        # 0 - definition is not found
                        for i, matched_files in enumerate((fls for fls in (
                                tuple(f for f in possible_files if f == context_file),
                                tuple(f for f in possible_files if is_common(f, context_file)),
                                tuple(f for f in possible_files if are_linked(f, context_file)),
                                ('unknown',)) if len(fls) > 0)):
                            files = matched_files
                            index = i
                            break
                        else:
                            raise RuntimeError("We do not expect any other file class")
                        if len(files) > 1:
                            self.__error("Multiple matches for use: {} call in {}".format(func, context_func))

                        if func in cached:
                            cached[func][context_file] = (files, index)
                        else:
                            cached[func] = {context_file: (files, index)}

                    for possible_file in files:
                        if possible_file not in description:
                            val = init_val()
                            if context_func == "NULL":
                                val["used_in_file"] = {context_file: {line: index}}
                            else:
                                val["used_in_func"][context_func] = {context_file: {line: index}}
                            description[possible_file] = val
                        else:
                            if context_func == "NULL":
                                if context_file in description[possible_file]["used_in_file"]:
                                    description[possible_file]["used_in_file"][context_file][line] = index
                                else:
                                    description[possible_file]["used_in_file"][context_file] = {line: index}
                            else:
                                if context_func not in description[possible_file]["used_in_func"]:
                                    description[possible_file]["used_in_func"][context_func] = {
                                        context_file: {
                                            line: index
                                        }
                                    }
                                elif context_file not in description[possible_file]["used_in_func"][context_func]:
                                    description[possible_file]["used_in_func"][context_func][context_file] = \
                                        {line: index}
                                else:
                                    description[possible_file]["used_in_func"][context_func][context_file][line] = index

                        uses = self.callgraph[context_func][context_file]["uses"]
                        if func not in uses:
                            uses[func] = {context_file: callgraph[func][possible_file]["used_in_func"][context_func][context_file]}
                        elif context_file not in uses[func]:
                            uses[func][context_file] = callgraph[func][possible_file]["used_in_func"][context_func][context_file]

                        if possible_file == "unknown":
                            self.__error("Can't match definition for use: {} {}".format(func, context_file))

    def __process_callv(self, functions, context_file):
        pass
        # This helps performance
        callgraph = self.callgraph
        options = (
            lambda fs: tuple(f for f in fs if f == context_file),
            lambda fs: tuple(f for f in fs if self.__t_unit_is_common(f, context_file)),
            lambda fs: tuple(f for f in fs if self.__files_are_linked(f, context_file)),
        )
        for func in functions:
            description = callgraph[func]
            # For each function call there can be many definitions with the same name, defined in different files.
            # possible_files is a list of them.
            possible_files = tuple(f for f in description if f != "unknown")
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
                description['unknown'] = self.__cg_initial_value()
            if len(files) > 1:
                    self.__error("Multiple matches for use in vars: {} in {}".format(func, context_file))

            for possible_file in files:
                if context_file not in description[possible_file]["used_in_vars"]:
                    description[possible_file]["used_in_vars"].append(context_file)

    def __process_init_global(self):
        init_global = self.extensions["Info"].init_global

        if not os.path.isfile(init_global):
            return

        self.log("Processing global variables initializations")
        self.variables = parse_initialization_functions(init_global, self.callgraph, self.__process_callv)

    def __process_macros(self):
        expand_file = self.extensions["Info"].expand

        if not os.path.isfile(expand_file):
            return

        self.log("Processing macros")

        all_args = "(?:\sarg\d+='[^']*')*"
        regex = re.compile(r'(\S*) (\S*)({0})'.format(all_args))
        args_extract = r"arg\d+='([^']*)'"
        regex2 = re.compile(args_extract)
        with open(expand_file, "r") as expand_fh:
            for line in expand_fh:
                m = regex.match(line)
                if m:
                    file, func, args = m.groups()
                    args = regex2.findall(args)
                    if file in self.macros and func in self.macros[file]:
                        self.macros[file][func]["args"].append(args)
                    elif file in self.macros:
                        self.macros[file][func] = {'args': [args]}
                    else:
                        self.macros[file] = {func: {'args': [args]}}

    def __dump_collection(self, collection, suffix):
        for file in list(collection.keys()):
            data = collection.pop(file)
            file_name = self.__src_related_file_name(file, suffix)
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
            self.dump_data(data, file_name)

    def __load_collection(self, suffix, files):
        merged_data = dict()
        for file in files:
            file_name = self.__src_related_file_name(file, suffix)
            if not os.path.isfile(file_name):
                self.warning("There is no data for the requested file: {!r}".format(file_name))
            else:
                data = self.load_data(file_name)
                merged_data[file] = data
        return merged_data

    def __src_related_file_name(self, file, postfix):
        return os.path.join(os.path.normpath(self.callgraph_dir + os.path.sep + os.path.dirname(file)),
                            os.path.basename(file) + postfix)

    def __t_unit_is_common(self, file1, file2):
        graph = self.src_graph
        return file1 in graph and file2 in graph and len(set(graph[file1]["compiled_in"]) & set(graph[file2]["compiled_in"])) > 0

    def __files_are_linked(self, file1, file2):
        graph = self.src_graph
        return file1 in graph and file2 in graph and len(set(graph[file1]["used_by"]) & set(graph[file2]["used_by"])) > 0

    def __error(self, msg):
        """
        Prints an error message
        """
        if not os.path.isdir(self.work_dir):
            os.makedirs(self.work_dir)

        with open(self.err_log, "a") as err_fh:
            err_fh.write("{}\n".format(msg))

    @staticmethod
    def __cg_initial_value():
        return {
            "calls": dict(),
            "uses": dict(),
            "used_in_file": dict(),
            "used_in_func": dict(),
            "used_in_vars": list(),
            "called_in": dict(),
            "calls_by_pointer": dict(),
            "declared_in": dict()
        }

    def __clean_error_log(self):
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


def parse(args=sys.argv[1:]):
    args = parse_args(args)

    c = Callgraph(args.work_dir, conf={"log_level": args.log_level})
    if not c.is_parsed():
        c.parse(load_cmds(args.cmds_json))
