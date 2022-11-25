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
from clade.types.nested_dict import nested_dict, traverse


class Macros(Extension):
    requires = ["Info"]

    __version__ = "2"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.macros = nested_dict()
        self.macros_folder = "macros"

        self.exps = nested_dict()
        self.exps_folder = "expansions"

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Parsing definitions")
        self.__process_macros_definitions()

        self.log("Parsing expansions")
        self.__process_macros_expansions()

        self.dump_data_by_key(self.macros, self.macros_folder)
        self.macros.clear()

        self.log("Reversing expansions")
        self.__reverse_expansions()

        self.dump_data_by_key(self.exps, self.exps_folder)
        self.exps.clear()

    def __process_macros_definitions(self):
        for file, macro, line in self.extensions["Info"].iter_macros_definitions():
            self.debug("Processing definition: " + " ".join(
                [file, macro, line])
            )

            self.macros[file][macro][line] = nested_dict()

    def __process_macros_expansions(self):
        for exp_file, def_file, macro, exp_line, def_line, args in self.extensions["Info"].iter_macros_expansions():
            # args are excluded from the debug log

            self.debug("Processing expansions: " + " ".join(
                [exp_file, def_file, macro, exp_line, def_line])
            )

            if def_file not in self.macros:
                def_file = "unknown"

            if not args:
                self.macros[def_file][macro][def_line][exp_file][exp_line] = []
            elif self.macros[def_file][macro][def_line][exp_file][exp_line]:
                self.macros[def_file][macro][def_line][exp_file][exp_line].append(args)
            else:
                self.macros[def_file][macro][def_line][exp_file][exp_line] = [args]

    def __reverse_expansions(self):
        for def_file, macros in self.yield_macros():
            for macro, def_line, exp_file, exp_line, args in traverse(macros[def_file], 5):
                self.exps[exp_file][macro][exp_line][def_file][def_line] = args

    def load_macros(self, files=None):
        """Load json with all information about macros."""

        return self.load_data_by_key(self.macros_folder, files)

    def yield_macros(self, files=None):
        """Yeild dictionaries with information about macros."""
        yield from self.yield_data_by_key(self.macros_folder, files)

    def load_expansions(self, files=None):
        """Load json with all information about macro expansions."""

        return self.load_data_by_key(self.exps_folder, files)

    def yield_expansions(self, files=None):
        """Yeild dictionaries with information about macro expansions."""
        yield from self.yield_data_by_key(self.exps_folder, files)
