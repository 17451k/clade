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

import os
import re

from clade.extensions.common import Common
from clade.extensions.opts import requires_value


class Link(Common):
    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

    def parse(self, cmds_file):
        super().parse(cmds_file, self.conf.get("Link.which_list", []))

    def parse_cmd(self, cmd):
        self.debug("Parse: {}".format(cmd))
        parsed_cmd = self._get_cmd_dict(cmd)

        if self.name not in requires_value:
            raise RuntimeError(
                "Command type '{}' is not supported".format(self.name)
            )

        opts = iter(cmd["command"][1:])

        libpaths = []

        for opt in opts:
            if opt in requires_value[self.name]:
                val = next(opts)
                parsed_cmd["opts"].extend([opt, val])
            elif re.search(r"[/-]out:", opt, re.IGNORECASE):
                parsed_cmd["out"].append(re.sub(r"[/-]OUT:", "", opt, flags=re.I))
            elif re.search(r"^[/-]", opt):
                parsed_cmd["opts"].append(opt)

                m = re.search(r"^[/-]libpath:(.*)", opt)

                if m:
                    libpaths.append(m.group(1))
            else:
                for libpath in libpaths:
                    joined_opt = os.path.join(libpath, opt)

                    if os.path.exists(joined_opt):
                        parsed_cmd["in"].append(joined_opt)
                        break
                else:
                    parsed_cmd["in"].append(opt)

        if self.is_bad(parsed_cmd):
            self.dump_bad_cmd_id(cmd["id"])
            return

        self.dump_cmd_by_id(cmd["id"], parsed_cmd)
