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


class Typedefs(Callgraph):
    requires = ["Info"]

    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        super().__init__(work_dir, conf)

        self.typedefs = dict()

    def parse(self, cmds_file):
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.parse_prerequisites(cmds_file)

        self.__process_typedefs()
        self.dump_typedefs()

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

    def dump_typedefs(self):
        self._dump_collection(self.typedefs, '.typedefs.json')

    def load_typedefs(self, files):
        return self._load_collection('.typedefs.json', files)


def parse(args=sys.argv[1:]):
    conf = parse_args(args)

    c = Typedefs(conf["work_dir"], conf=conf)
    c.parse(conf["cmds_file"])
