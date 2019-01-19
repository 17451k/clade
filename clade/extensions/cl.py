# Copyright (c) 2019 ISP RAS (http://www.ispras.ru)
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

import io
import re

from clade.extensions.abstract import Extension


class CL(Extension):
    def __init__(self, work_dir, conf=None, preset="base"):
        super().__init__(work_dir, conf, preset)

    def read_cmd_file(self, m):
        cmd_file = m.group(1).strip('\"')
        with io.open(cmd_file, "r", encoding="utf-16") as cmd_file_fh:
            return " ".join(cmd_file_fh.readlines())

    def preprocess(self, cmd):
        if len(cmd["command"]) > 0:
            cmd["command"][0] = re.sub(r"@(\S*)", self.read_cmd_file, cmd["command"][0])

    def parse(self, cmds_file):
        return super().parse(cmds_file)
