# Copyright (c) Ilya Shchepetkov
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


class LN(Common):
    __version__ = "1"

    def parse(self, cmds_file):
        super().parse(cmds_file, self.conf.get("LN.which_list", []))

    def parse_cmd(self, cmd):
        parsed_cmd = {
            "id": cmd["id"],
            "in": [],
            "out": [],
            "opts": [],
            "cwd": cmd["cwd"],
            "command": cmd["command"],
        }

        # 'ln' options always have the following forms:
        #     [-options] in_file
        #     [-options] in_file out_file
        #     [-options] in_file ... out_dir

        # Output directory, where symlinks will be created
        # By default it is current working directory
        out = None

        opts = iter(cmd["command"][1:])
        for opt in opts:
            if re.search(r"^-", opt):
                if opt == "-t":
                    # Value is the next option.
                    out = os.path.normpath(next(opts))
                elif opt.startswith("--target-directory="):
                    out = opt.replace("--target-directory=", "")
                else:
                    parsed_cmd["opts"].append(opt)
            elif os.path.isfile(opt):
                if out is not None or not parsed_cmd["in"] or opt != cmd["command"][-1]:
                    parsed_cmd["in"].append(os.path.normpath(opt))
                else:
                    parsed_cmd["out"].append(os.path.normpath(opt))
            elif os.path.isdir(opt):
                out = os.path.normpath(opt)
            else:
                self.error(f"Files from the command {cmd} probably do not exist anymore")
                return

        # If no output parsed, then it is created in current directory
        if not parsed_cmd["out"] and not out:
            out = parsed_cmd["cwd"]

        if (parsed_cmd["out"] and out):
            self.error(f"ln command {cmd} is incorrectly parsed: {parsed_cmd}")
            return

        if out:
            for cmd_in in parsed_cmd["in"]:
                parsed_cmd["out"].append(os.path.join(out, os.path.basename(cmd_in)))

        if self.is_bad(parsed_cmd):
            self.dump_bad_cmd_id(cmd["id"])
            return

        self.dump_cmd_by_id(cmd["id"], parsed_cmd)

        return parsed_cmd
