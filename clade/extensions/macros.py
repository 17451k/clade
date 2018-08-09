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

from clade.extensions.callgraph import Callgraph
from clade.extensions.utils import parse_args


class Macros(Callgraph):
    requires = ["Info"]

    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        super().__init__(work_dir, conf)

        self.macros = dict()

    def parse(self, cmds_file):
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.parse_prerequisites(cmds_file)

        self.__process_macros()
        self.dump_macros()

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

    def dump_macros(self):
        self._dump_collection(self.macros, '.macros.json')

    def load_macros(self, files):
        return self._load_collection('.macros.json', files)


def parse(args=sys.argv[1:]):
    conf = parse_args(args)

    c = Macros(conf["work_dir"], conf=conf)
    c.parse(conf["cmds_file"])
