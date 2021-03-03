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


class Typedefs(Extension):
    requires = ["Info"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.typedefs = dict()
        self.typedefs_folder = "typedefs"

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Parsing typedefs")

        self.__process_typedefs()
        self.dump_data_by_key(self.typedefs, self.typedefs_folder)
        self.typedefs.clear()

    def __process_typedefs(self):
        for scope_file, declaration in self.extensions["Info"].iter_typedefs():
            if scope_file not in self.typedefs:
                self.typedefs[scope_file] = [declaration]
            elif declaration not in self.typedefs[scope_file]:
                self.typedefs[scope_file].append(declaration)

    def load_typedefs(self, files=None):
        return self.load_data_by_key(self.typedefs_folder, files)
