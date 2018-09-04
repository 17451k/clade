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
from clade.extensions.utils import parse_args


class AR(Common):
    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        if "AR.which_list" not in conf:
            self.which_list = ["^/usr/(local/)?bin/[^/]*?ar$"]
        else:
            self.which_list = conf["AR.which_list"]

        super().__init__(work_dir, conf)

    def parse(self, cmds_file):
        super().parse(cmds_file, self.which_list)

    def parse_cmd(self, cmd):
        parsed_cmd = {
            "id": cmd["id"],
            "in": cmd["command"][3:],
            "out": [cmd["command"][2]],
            "opts": cmd["command"][1],
            "cwd": cmd["cwd"],
            "command": cmd["command"][0]
        }

        if self.is_bad(parsed_cmd):
            return

        self.debug("Parsed command: {}".format(parsed_cmd))
        self.dump_cmd_by_id(cmd["id"], parsed_cmd)


def parse(args=sys.argv[1:]):
    conf = parse_args(args)

    c = AR(conf["work_dir"], conf=conf)
    c.parse(conf["cmds_file"])
