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
from clade.extensions.common_info import CommonInfo
from clade.extensions.utils import Location


class Functions(CommonInfo):
    requires = ["SrcGraph", "Info"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.funcs = dict()
        self.funcs_folder = "functions"

        self.funcs_by_file = dict()
        self.funcs_by_file_folder = "functions_by_file"

    @Extension.prepare
    def parse(self, cmds_file):
        self.__process_definitions()
        self.__process_declarations()
        self.__process_exported()
        self.__group_functions_by_file()
        self._clean_warn_log()

        self.dump_data_by_key(self.funcs, self.funcs_folder)
        self.dump_data_by_key(self.funcs_by_file, self.funcs_by_file_folder)

        self.extensions["SrcGraph"].unload_src_graph()
        self.funcs.clear()
        self.funcs_by_file.clear()

    def load_functions(self, funcs=None):
        """Load information about functions."""
        return self.load_data_by_key(self.funcs_folder, funcs)

    def load_functions_by_file(self, files=None):
        """Load information about functions grouped by files."""
        return self.load_data_by_key(self.funcs_by_file_folder, files)

    def yield_functions_by_file(self, files=None):
        yield from self.yield_data_by_key(self.funcs_by_file_folder, files)

    def __process_definitions(self):
        self.log("Parsing definitions")

        for (
            src_file,
            src_cmd_id,
            func,
            def_line,
            func_type,
            signature,
        ) in self.extensions["Info"].iter_definitions():
            self.debug(
                "Processing definition: "
                + " ".join([src_file, func, def_line, func_type, signature])
            )

            if func not in self.funcs:
                self.funcs[func] = []

            for definition in self.funcs[func]:
                if definition["file"] == src_file and definition["line"] == def_line:
                    # There can be some repeated definitions because of
                    # canonical paths: we just skip them here
                    if src_cmd_id not in definition["compiled_in"]:
                        definition["compiled_in"].append(src_cmd_id)
                    break
            else:
                self.funcs[func].append(
                    self.construct_definition(
                        src_file, src_cmd_id, func_type, def_line, signature
                    )
                )

    def __process_declarations(self):
        def get_unknown_val(decl_val, type="extern"):
            return self.construct_definition(
                "unknown", "0", type, None, None, decl_val
            )

        self.log("Parsing declarations")

        for (
            decl_file,
            decl_cmd_id,
            decl_name,
            decl_line,
            decl_type,
            decl_signature,
        ) in self.extensions["Info"].iter_declarations():
            self.debug(
                "Processing declaration: "
                + " ".join([decl_file, decl_name, decl_line, decl_type, decl_signature])
            )

            decl_val = {
                "file": decl_file,
                "signature": decl_signature,
                "line": decl_line,
                "type": decl_type,
                "compiled_in": [decl_cmd_id],
            }

            if decl_name not in self.funcs:
                self.funcs[decl_name] = [get_unknown_val(decl_val, decl_type)]
                self._warning(f"No definition: {decl_name}")
                continue

            found = False

            for definition in self.funcs[decl_name]:
                if definition["file"] == "unknown":
                    continue

                for def_cmd_id in definition["compiled_in"]:
                    if not decl_type == definition["type"]:
                        continue

                    if def_cmd_id == decl_cmd_id or (
                        decl_type == "extern"
                        and self._files_are_linked(
                            Location(definition["file"], def_cmd_id),
                            Location(decl_file, decl_cmd_id),
                        )
                    ):
                        self.__add_declaration(definition, decl_val)
                        found = True

            if not found:
                for definition in self.funcs[decl_name]:
                    if definition["file"] == "unknown":
                        self.__add_declaration(definition, decl_val)
                        break
                else:
                    self.funcs[decl_name].append(get_unknown_val(decl_val, decl_type))

    def __add_declaration(self, definition, decl_val):
        for declaration in definition["declarations"]:
            if (
                declaration["file"] == decl_val["file"]
                and declaration["line"] == decl_val["line"]
            ):
                declaration["compiled_in"].append(decl_val["compiled_in"][0])
                return
        else:
            definition["declarations"].append(decl_val)

    def __process_exported(self):
        # Linux kernel only

        for src_file, func in self.extensions["Info"].iter_exported():
            self.debug("Processing exported functions: " + " ".join([src_file, func]))

            # Variables can also be exported
            if func not in self.funcs:
                continue

            for definition in self.funcs[func]:
                if definition["file"] == src_file:
                    definition["type"] = "exported"

    def __group_functions_by_file(self):
        self.log("Grouping functions by file")

        for func in self.funcs:
            for definition in self.funcs[func]:
                # Make copy of definition, so we can alter it
                definition = dict(definition)

                file = definition["file"]
                del definition["file"]
                definition["name"] = func

                if file not in self.funcs_by_file:
                    self.funcs_by_file[file] = []

                self.funcs_by_file[file].append(definition)

    def construct_definition(
        self, file, cmd_id, type, line=None, signature=None, declaration=None
    ):
        if not declaration:
            declarations = []
        else:
            declarations = [declaration]

        return {
            "file": file,
            "type": type,
            "line": line,
            "signature": signature,
            "compiled_in": [cmd_id],
            "declarations": declarations,
        }
