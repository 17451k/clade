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

from clade.extensions.common import Common


class Copy(Common):
    __version__ = "1"

    def parse(self, cmds_file):
        super().parse(cmds_file, self.conf.get("Copy.which_list", []))

    def parse_cmd(self, cmd):
        parsed_cmd = {
            "id": cmd["id"],
            "in": [],
            "out": [],
            "opts": [],
            "cwd": cmd["cwd"],
            "command": cmd["command"],
        }

        command = cmd["command"][1:]

        if len(cmd["command"]) >= 2:
            if cmd["command"][0].endswith("cmd.exe") and cmd["command"][1] in ["/c", "-c"]:
                try:
                    copy_index = cmd["command"].index("copy")
                    command = cmd["command"][copy_index + 1:]
                except ValueError:
                    return
            else:
                return

        # TODO: support patterns in names (*.h)
        for opt in command:
            # Redirects, like >nul and 2<&1
            if cmd["command"][0].endswith("cmd.exe") and ">" in opt or "<" in opt:
                continue

            if opt.startswith("/") or opt.startswith("-"):
                parsed_cmd["opts"].append(opt)
            elif not parsed_cmd["in"]:
                cmd_in = os.path.normpath(opt)

                if not os.path.exists(cmd_in):
                    return

                parsed_cmd["in"].append(cmd_in)
            else:
                cmd_out = os.path.normpath(opt)

                # workaround for "cmd.exe /c if exist a copy a b" commands
                if os.path.isdir(cmd_out) and parsed_cmd["in"]:
                    cmd_out = os.path.join(cmd_out, os.path.basename(parsed_cmd["in"][0]))
                parsed_cmd["out"].append(cmd_out)

        if self.is_bad(parsed_cmd):
            self.dump_bad_cmd_by_id(cmd["id"], parsed_cmd)
            return

        self.debug("Parsed command: {}".format(parsed_cmd))
        self.dump_cmd_by_id(cmd["id"], parsed_cmd)
