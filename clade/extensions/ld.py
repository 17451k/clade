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

import sys

from clade.extensions.common import Common
from clade.extensions.utils import common_main


class LD(Common):
    def __init__(self, work_dir, conf=None, preset="base"):
        super().__init__(work_dir, conf, preset)

        if "LD.which_list" not in self.conf:
            self.which_list = ["^.*?ld$"]
        else:
            self.which_list = self.conf["LD.which_list"]

    def parse(self, cmds_file):
        super().parse(cmds_file, self.which_list)

    def parse_cmd(self, cmd):
        parsed_cmd = super().parse_cmd(cmd, self.name)

        if self.is_bad(parsed_cmd):
            return

        self.debug("Parsed command: {}".format(parsed_cmd))
        self.dump_cmd_by_id(cmd["id"], parsed_cmd)


def main(args=sys.argv[1:]):
    common_main(LD, args)
