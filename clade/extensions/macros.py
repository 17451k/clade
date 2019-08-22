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

from clade.extensions.abstract import Extension
from clade.extensions.utils import nested_dict, traverse


class Macros(Extension):
    requires = ["Info"]

    __version__ = "2"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.def_regex = re.compile(r"\"(.*?)\" (\S*) (\S*)")
        self.exp_regex = re.compile(r'\"(.*?)\" \"(.*?)\" (\S*) (\S*) (\S*)(.*)')
        self.arg_regex = re.compile(r' actual_arg\d+=(.*)')

        self.macros = nested_dict()
        self.macros_file = "macros.json"
        self.macros_folder = "macros"

        self.exps = nested_dict()
        self.exps_file = "expansions.json"
        self.expansions_folder = "expansions"

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Parsing macros")

        self.__process_macros_definitions()
        self.__process_macros_expansions()
        self.__reverse_expansions()

        self.dump_data(self.macros, self.macros_file)
        self.dump_data(self.exps, self.exps_file)
        self.dump_data_by_key(self.macros, self.macros_folder)
        self.dump_data_by_key(self.exps, self.expansions_folder)

        self.macros.clear()
        self.log("Parsing finished")

    def __process_macros_definitions(self):
        for line in self.extensions["Info"].iter_macros_definitions():
            m = self.def_regex.match(line)

            if not m:
                raise SyntaxError("CIF output has unexpected format: {!r}".format(line))

            file, macro, line = m.groups()

            self.macros[file][macro][line] = nested_dict()

    def __process_macros_expansions(self):
        for line in self.extensions["Info"].iter_macros_expansions():
            m = self.exp_regex.match(line)

            if not m:
                raise SyntaxError("CIF output has unexpected format: {!r}".format(line))

            file, def_file, macro, line, def_line, args_str = m.groups()

            args = list()
            if args_str:
                for arg in args_str.split(','):
                    m_arg = self.arg_regex.match(arg)
                    if m_arg:
                        args.append(m_arg.group(1))

            if def_file not in self.macros:
                def_file = "unknown"

            if not args:
                self.macros[def_file][macro][def_line][file][line] = []
            elif self.macros[def_file][macro][def_line][file][line]:
                self.macros[def_file][macro][def_line][file][line].append(args)
            else:
                self.macros[def_file][macro][def_line][file][line] = [args]

    def __reverse_expansions(self, allow_smaller=True):
        for def_file, macro, def_line, exp_file, exp_line, args in traverse(self.macros, 6):
            self.exps[exp_file][macro][exp_line][def_file][def_line] = args

    def load_macros(self, files=None):
        """Load json with all information about macros."""

        if files:
            return self.load_data_by_key(self.macros_folder, files)
        else:
            return self.load_data(self.macros_file)

    def load_expansions(self, files=None):
        """Load json with all information about macro expansions."""

        return self.load_data_by_key(self.expansions_folder, files)
