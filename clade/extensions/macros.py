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
from clade.extensions.utils import parse_args


class Macros(Extension):
    requires = ["Info"]

    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        super().__init__(work_dir, conf)

        self.expand = dict()
        self.expand_suffix = ".expand.json"

    def parse(self, cmds_file):
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.parse_prerequisites(cmds_file)

        self.__process_macros_expansions()

        self.log("Dump parsed data")
        self.dump_data_by_key(self.expand, self.expand_suffix)
        self.log("Finish")

    def __process_macros_expansions(self):
        self.log("Processing macros expansion")

        all_args = "(?:\sarg\d+='[^']*')*"
        regex = re.compile(r'(\S*) (\S*)({0})'.format(all_args))

        args_extract = r"arg\d+='([^']*)'"
        regex2 = re.compile(args_extract)

        for line in self.extensions["Info"].iter_macros_expansions():
            m = regex.match(line)
            if m:
                file, func, args = m.groups()
                args = regex2.findall(args)

                if file in self.expand and func in self.expand[file]:
                    self.expand[file][func]["args"].append(args)
                elif file in self.expand:
                    self.expand[file][func] = {'args': [args]}
                else:
                    self.expand[file] = {func: {'args': [args]}}

    def load_macros_expansions(self, files=None):
        return self.load_data_by_key(self.expand_suffix, files)


def parse(args=sys.argv[1:]):
    conf = parse_args(args)

    c = Macros(conf["work_dir"], conf=conf)
    c.parse(conf["cmds_file"])
