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

from clade.extensions.abstract import Extension
from clade.extensions.utils import common_main


class Macros(Extension):
    requires = ["Info"]

    def __init__(self, work_dir, conf=None, preset="base"):
        super().__init__(work_dir, conf, preset)

        self.define = dict()
        self.define_folder = "define"

        self.expand = dict()
        self.expand_folder = "expand"

    @Extension.prepare
    def parse(self, cmds_file):
        self.__process_macros_definitions()
        self.__process_macros_expansions()

        self.log("Dump parsed data")
        self.dump_data_by_key(self.define, self.define_folder)
        self.dump_data_by_key(self.expand, self.expand_folder)
        self.log("Finish")

    def __process_macros_definitions(self):
        self.log("Processing macros definitions")

        regex = re.compile(r"(\S*) (\S*) (\S*)")

        for line in self.extensions["Info"].iter_macros_definitions():
            m = regex.match(line)

            if not m:
                raise RuntimeError("CIF output has unexpected format")

            file, macro, line = m.groups()

            if file in self.define and macro in self.define[file]:
                self.define[file][macro].append(line)
            elif file in self.define:
                self.define[file][macro] = [line]
            else:
                self.define[file] = {macro: [line]}

    def __process_macros_expansions(self):
        self.log("Processing macros expansions")

        regex = re.compile(r'(\S*) (\S*)(.*)')
        regex2 = re.compile(r' actual_arg\d+=(.*)')

        for line in self.extensions["Info"].iter_macros_expansions():
            m = regex.match(line)

            if not m:
                raise RuntimeError("CIF output has unexpected format")

            file, macro, args_str = m.groups()

            args = list()
            if args_str:
                for arg in args_str.split(','):
                    m_arg = regex2.match(arg)
                    if m_arg:
                        args.append(m_arg.group(1))

            if file in self.expand and macro in self.expand[file]:
                self.expand[file][macro]["args"].append(args)
            elif file in self.expand:
                self.expand[file][macro] = {'args': [args]}
            else:
                self.expand[file] = {macro: {'args': [args]}}

    def load_macros_definitions(self, files=None):
        return self.load_data_by_key(self.define_folder, files)

    def load_macros_expansions(self, files=None):
        return self.load_data_by_key(self.expand_folder, files)


def main(args=sys.argv[1:]):
    common_main(Macros, args)
