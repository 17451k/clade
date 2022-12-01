# Copyright (c) 2019 ISP RAS (http://www.ispras.ru)
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

import codecs
import os
import re


from clade.extensions.abstract import Extension
from clade.extensions.common_info import CommonInfo
from clade.types.nested_dict import nested_dict, traverse


class CrossRef(CommonInfo):
    requires = ["Functions", "Callgraph", "Storage", "Macros"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.funcs = None

        self.ref_to_folder = "ref_to"
        self.ref_from_folder = "ref_from"

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Loading data")
        self.funcs = self.extensions["Functions"].load_functions_by_file()

        self.log("Calculating raw locations")
        raw_locations = self.__get_raw_locations()

        self.log("Parsing files")
        locations = dict()
        for file in raw_locations:
            locations[file] = self.__parse_file(file, raw_locations)

        self.log("Calculating 'to' references")
        self.__gen_ref_to(locations)

        self.log("Calculating 'from' references")
        self.__gen_ref_from(locations)

    def load_ref_to_by_file(self, files=None):
        """Load references to definitions and declarations grouped by files."""
        return self.load_data_by_key(self.ref_to_folder, files)

    def load_ref_from_by_file(self, files=None):
        """Load references to usages grouped by files."""
        return self.load_data_by_key(self.ref_from_folder, files)

    def __get_raw_locations(self):
        raw_locations = dict()

        raw_locations = self.__get_raw_func_locations(raw_locations)
        raw_locations = self.__get_raw_macro_locations(raw_locations)

        return raw_locations

    def __get_raw_func_locations(self, raw_locations):
        for file in self.funcs:
            for definition in self.funcs[file]:
                if definition["line"]:
                    val = (definition["line"], definition["name"], "def_func")

                    if val not in raw_locations.get(file, []):
                        self.__add_raw_loc(raw_locations, file, val)

                for declaration in definition["declarations"]:
                    val = (declaration["line"], definition["name"], "decl_func")

                    if val not in raw_locations.get(declaration["file"], []):
                        self.__add_raw_loc(raw_locations, declaration["file"], val)

        for context_file, callgraph in self.extensions["Callgraph"].yield_callgraph():
            for _, _, file, func, line in traverse(callgraph[context_file], 5, {2: "calls"}):
                val = (line, func, "call")
                self.__add_raw_loc(raw_locations, context_file, val)

        return raw_locations

    def __get_raw_macro_locations(self, raw_locations):
        for exp_file, expansions in self.extensions["Macros"].yield_expansions():
            for macro, exp_line in traverse(expansions[exp_file], 2):
                val = (exp_line, macro, "expand")
                self.__add_raw_loc(raw_locations, exp_file, val)

        # Load macros dictionary independetly for each file
        for def_file, macros in self.extensions["Macros"].yield_macros():
            for macro, def_line in traverse(macros[def_file], 2):
                if def_file == "unknown":
                    continue

                val = (def_line, macro, "def_macro")
                self.__add_raw_loc(raw_locations, def_file, val)

        return raw_locations

    def __add_raw_loc(self, raw_locations, file, val):
        if file in raw_locations:
            raw_locations[file].append(val)
        else:
            raw_locations[file] = [val]

    def __parse_file(self, file, raw_locations, ignore_errors=False, encoding="utf8"):
        storage_file = self.extensions["Storage"].get_storage_path(file)

        if not os.path.exists(storage_file):
            # There may be some header files from CIF that are not in the storage
            if os.path.exists(file):
                self.extensions["Storage"].add_file(file)
            else:
                return None

        locations = nested_dict()

        sorted_locs = sorted(raw_locations[file], key=lambda x: int(x[0]))
        sorted_pos = 0

        try:
            if ignore_errors:
                fp = codecs.open(storage_file, "r", encoding=encoding, errors="ignore")
            else:
                fp = open(storage_file, "r", encoding=encoding)

            for i, s in enumerate(fp):
                if sorted_pos >= len(sorted_locs):
                    break

                while (sorted_pos < len(sorted_locs) and int(sorted_locs[sorted_pos][0]) <= i + 1):
                    if i == int(sorted_locs[sorted_pos][0]) - 1:
                        line = int(sorted_locs[sorted_pos][0])
                        name = sorted_locs[sorted_pos][1]
                        ctype = sorted_locs[sorted_pos][2]

                        for lowest_index in self.__find_all(s, name):
                            val = (line, lowest_index, lowest_index + len(name))
                            if name in locations[ctype]:
                                locations[ctype][name].append(val)
                            else:
                                locations[ctype][name] = [val]

                            # Only one macro definition can be on a single line
                            if ctype == "def_macro":
                                break
                            # TODO: there may be a function call inside macro expansion

                    sorted_pos += 1

            return locations
        except UnicodeDecodeError:
            return self.__parse_file(file, raw_locations, ignore_errors=True)
        finally:
            fp.close()

    def __find_all(self, s, name):
        for m in re.finditer(r"\w+", s):
            if name == m.group(0):
                yield m.start()

    def __gen_ref_to(self, locations):
        self.__gen_ref_to_func(locations)
        self.__gen_ref_to_macro(locations)

    def __gen_ref_to_func(self, locations):
        for context_file, callgraph in self.extensions["Callgraph"].yield_callgraph():
            calls = set()

            for context_func, _, file in traverse(callgraph[context_file], 3, {2: "calls"}):
                if file not in self.funcs:
                    self._warning("Can't find file: {!r}".format(file))
                    continue

                for func in callgraph[context_file][context_func]["calls"][file]:
                    if func not in locations[context_file]["call"]:
                        # Probably because of macro expansion
                        continue

                    for definition in self.funcs[file]:
                        if definition["name"] == func:
                            break
                    else:
                        self._warning(f"Can't find function: {func} {file}")
                        continue

                    calls.add((file, func))

            ref_to = nested_dict()

            for file, func in calls:
                loc_list = locations[context_file]["call"][func]

                for definition in self.funcs[file]:
                    if definition["name"] != func:
                        continue

                    if definition["line"]:
                        def_line = int(definition["line"])

                        for loc_el in loc_list:
                            val = (loc_el, (file, def_line))
                            self.__add_ref(ref_to, context_file, "def_func", val)

                    for declaration in definition["declarations"]:
                        decl_line = int(declaration["line"])

                        for loc_el in loc_list:
                            val = (loc_el, (declaration["file"], decl_line))
                            self.__add_ref(ref_to, context_file, "decl_func", val)

            self.__dump_ref_to(ref_to)

    def __gen_ref_to_macro(self, locations):
        for exp_file, expansions in self.extensions["Macros"].yield_expansions():
            if exp_file == "unknown" or "expand" not in locations[exp_file]:
                continue

            ref_to = nested_dict()

            for macro, loc_list in traverse(locations[exp_file]["expand"], 2):
                for loc_el in loc_list:
                    exp_line = str(loc_el[0])

                    for def_file, def_line in traverse(expansions[exp_file][macro][exp_line], 2):
                        if def_file == "unknown":
                            continue

                        val = (loc_el, (def_file, int(def_line)))
                        self.__add_ref(ref_to, exp_file, "def_macro", val)

            self.__dump_ref_to(ref_to)

    def __add_ref(self, ref, file, key, val):
        if ref[file][key]:
            ref[file][key].add(val)
        else:
            ref[file][key] = {val}

    def __dump_ref_to(self, ref_to):
        if not ref_to:
            return

        local_ref_to = self.load_ref_to_by_file(list(ref_to))

        for file in ref_to:
            if file not in local_ref_to:
                continue
            ref_to[file].update(local_ref_to[file])

        self.__convert_sets_to_lists(ref_to)
        self.dump_data_by_key(ref_to, self.ref_to_folder)

    def __gen_ref_from(self, locations):
        self.__gen_ref_from_func(locations)
        self.__gen_ref_from_macro(locations)

    def __gen_ref_from_func(self, locations):
        for file, callgraph in self.extensions["Callgraph"].yield_callgraph():
            ref_from = nested_dict()

            for definition in self.funcs[file]:
                context_locs = self.__get_context_locs(file, definition["name"], callgraph)

                if file != "unknown" and definition["name"] in locations[file]["def_func"]:
                    loc_list = locations[file]["def_func"][definition["name"]]

                    for context_file, lines in context_locs:
                        for loc_el in loc_list:
                            val = (loc_el, (context_file, lines))
                            self.__add_ref(ref_from, file, "call", val)

                for declaration in definition["declarations"]:
                    if definition["name"] in locations[declaration["file"]]["decl_func"]:
                        loc_list = locations[declaration["file"]]["decl_func"][definition["name"]]

                        for context_file, lines in context_locs:
                            for loc_el in loc_list:
                                val = (loc_el, (context_file, lines))
                                self.__add_ref(ref_from, declaration["file"], "call", val)

            self.__dump_ref_from(ref_from)

    def __get_context_locs(self, file, func, callgraph):
        locs = []

        if func not in callgraph[file] or "called_in" not in callgraph[file][func]:
            return locs

        called_in = callgraph[file][func]["called_in"]

        for context_file in called_in:
            lines = []

            for _, line in traverse(called_in[context_file], 2):
                lines.append(int(line))

            locs.append((context_file, tuple(lines)))

        return locs

    def __gen_ref_from_macro(self, locations):
        for def_file, macros in self.extensions["Macros"].yield_macros():
            if def_file == "unknown" or "def_macro" not in locations[def_file]:
                continue

            ref_from = nested_dict()

            for macro, loc_list in traverse(locations[def_file]["def_macro"], 2):
                for loc_el in loc_list:
                    def_line = str(loc_el[0])

                    for exp_file in macros[def_file][macro][def_line]:
                        exp_lines = [int(l) for l in macros[def_file][macro][def_line][exp_file]]
                        val = (loc_el, (exp_file, tuple(exp_lines)))
                        self.__add_ref(ref_from, def_file, "expand", val)

            self.__dump_ref_from(ref_from)

    def __dump_ref_from(self, ref_from):
        if not ref_from:
            return

        local_ref_from = self.load_ref_from_by_file(list(ref_from))

        for file in ref_from:
            if file not in local_ref_from:
                continue

            if "call" in local_ref_from[file]:
                if ref_from[file]["call"]:
                    ref_from[file]["call"] = list(ref_from[file]["call"])
                    ref_from[file]["call"].extend(local_ref_from[file]["call"])
                else:
                    ref_from[file]["call"] = local_ref_from[file]["call"]

            if "expand" in local_ref_from[file]:
                if ref_from[file]["expand"]:
                    ref_from[file]["expand"] = list(ref_from[file]["expand"])
                    ref_from[file]["expand"].extend(local_ref_from[file]["expand"])
                else:
                    ref_from[file]["expand"] = local_ref_from[file]["expand"]

        self.__convert_sets_to_lists(ref_from)
        self.dump_data_by_key(ref_from, self.ref_from_folder)

    def __convert_sets_to_lists(self, ref):
        for file, key in traverse(ref, 2):
            ref[file][key] = list(ref[file][key])
