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


class Typedefs(Extension):
    requires = ["Info"]

    def __init__(self, work_dir, conf=None, preset="base"):
        super().__init__(work_dir, conf, preset)

        self.typedefs = dict()
        self.typedefs_folder = "typedefs"

    @Extension.prepare
    def parse(self, cmds_file):
        self.__process_typedefs()
        self.dump_data_by_key(self.typedefs, self.typedefs_folder)
        self.log("Finish")

    def __process_typedefs(self):
        self.log("Processing typedefs")

        regex = re.compile(r'(\S*) typedef (.*)')
        typedefs = self.typedefs

        for line in self.extensions["Info"].iter_typedefs():
            m = regex.match(line)

            if not m:
                raise RuntimeError("CIF output has unexpected format")

            scope_file, declaration = m.groups()

            if scope_file not in self.typedefs:
                typedefs[scope_file] = [declaration]
            elif declaration not in typedefs[scope_file]:
                typedefs[scope_file].append(declaration)

    def load_typedefs(self, files=None):
        return self.load_data_by_key(self.typedefs_folder, files)


def main(args=sys.argv[1:]):
    common_main(Typedefs, args)
