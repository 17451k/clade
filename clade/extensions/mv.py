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

from clade.extensions.common import Common


class MV(Common):
    __version__ = "1"

    def parse(self, cmds_file):
        super().parse(cmds_file, self.conf.get("MV.which_list", []))

    def parse_cmd(self, cmd):
        parsed_cmd = {
            "id": cmd["id"],
            "in": [],
            "out": [],
            "opts": [],
            "cwd": cmd["cwd"],
            "command": cmd["command"],
        }

        # We assume that 'MV' options always have such the form:
        #     [-opt]... in_file out_file
        for opt in cmd["command"][1:]:
            if re.search(r"^-", opt):
                parsed_cmd["opts"].append(opt)
            elif not parsed_cmd["in"]:
                parsed_cmd["in"].append(os.path.normpath(opt))
            else:
                parsed_cmd["out"].append(os.path.normpath(opt))

        if self.is_bad(parsed_cmd):
            self.dump_bad_cmd_id(cmd["id"])
            return

        self.dump_cmd_by_id(cmd["id"], parsed_cmd)
