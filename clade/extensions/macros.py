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

from typing import Generator, NamedTuple

from clade.extensions.abstract import Extension
from clade.types.nested_dict import nested_dict, traverse


class Expansion(NamedTuple):
    name: str
    def_file: str
    def_line: int
    exp_file: str
    exp_line: int


class Macros(Extension):
    requires = ["Info"]

    __version__ = "3"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.macros = nested_dict()
        self.macros_folder = "definitions"

        self.exps = nested_dict()
        self.expansions_folder = "expansions"
        self.reversed_expansions_folder = "reversed_expansions"

        self.args = nested_dict()
        self.args_folder = "args"

    @Extension.prepare
    def parse(self, _):
        self.log("Parsing definitions")
        self.__process_macros_definitions()

        self.log("Parsing expansions")
        self.__process_macros_expansions()

        self.dump_data_by_key(self.macros, self.macros_folder)
        self.macros.clear()

        self.dump_data_by_key(self.exps, self.expansions_folder)
        self.exps.clear()

        self.log("Parsing arguments")
        self.__process_macros_args()

        self.dump_data_by_key(self.args, self.args_folder)
        self.args.clear()

        self.log("Reversing expansions")
        self.__reverse_expansions()
        self.dump_data_by_key(self.exps, self.reversed_expansions_folder)
        self.exps.clear()

    def __process_macros_definitions(self):
        for file, macro, line in self.extensions["Info"].iter_macros_definitions():
            self.debug("Processing definition: " + " ".join([file, macro, line]))

            if file not in self.macros:
                self.macros[file] = list()

            self.macros[file].append({"name": macro, "line": int(line)})

    def __process_macros_expansions(self):
        for exp_file, def_file, macro, exp_line, def_line in self.extensions[
            "Info"
        ].iter_macros_expansions():
            self.debug("Processing expansion: " + " ".join([exp_file, macro, exp_line]))

            exp_val = {
                "exp_line": int(exp_line),
                "def_line": int(def_line),
            }

            if def_file not in self.macros:
                def_file = "unknown"

            if exp_file not in self.exps[def_file][macro]:
                self.exps[def_file][macro][exp_file] = list()

            self.exps[def_file][macro][exp_file].append(exp_val)

    def __process_macros_args(self):
        for exp_file, macro, args in self.extensions["Info"].iter_macros_args():
            # args are excluded from the debug log
            self.debug("Processing args: " + " ".join([exp_file, macro]))

            if macro not in self.args[exp_file]:
                self.args[exp_file][macro] = list()

            if args:
                self.args[exp_file][macro].append(args)

    def __reverse_expansions(self):
        for def_file, macros in self.yield_expansions():
            for macro, exp_file, exp_vals in traverse(macros[def_file], 3):
                self.exps[exp_file][macro][def_file] = exp_vals

    def load_macros(self, files=None):
        """Load json with all information about macros."""
        return self.load_data_by_key(self.macros_folder, files)

    def yield_macros(self, files=None):
        """Yield dictionaries with information about macros."""
        yield from self.yield_data_by_key(self.macros_folder, files)

    def load_expansions(self, files=None):
        """Load json with all information about macro expansions."""
        return self.load_data_by_key(self.expansions_folder, files)

    def yield_expansions(self, files=None):
        """Yield dictionaries with information about macro expansions."""
        yield from self.yield_data_by_key(self.expansions_folder, files)

    def load_reversed_expansions(self, files=None):
        """Load json with all information about reversed macro expansions."""
        return self.load_data_by_key(self.reversed_expansions_folder, files)

    def yield_reversed_expansions(self, files=None):
        """Yield dictionaries with information about reversed macro expansions."""
        yield from self.yield_data_by_key(self.reversed_expansions_folder, files)

    def load_args(self, files=None):
        """Load json with all information about args of macro expansions."""
        return self.load_data_by_key(self.args_folder, files)

    def yield_args(self, files=None):
        """Yield dictionaries with information about args of macro expansions."""
        yield from self.yield_data_by_key(self.args_folder, files)

    def traverse_expansions(self) -> Generator[Expansion, None, None]:
        """Traverse all macro expansions."""

        for exp_file, expansions in self.yield_reversed_expansions():
            for macro, def_file, exp_vals in traverse(
                expansions[exp_file],
                3,
            ):
                for exp_val in exp_vals:
                    yield Expansion(
                        name=macro,
                        def_file=def_file,
                        def_line=exp_val["def_line"],
                        exp_file=exp_file,
                        exp_line=exp_val["exp_line"],
                    )
