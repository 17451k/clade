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

from clade.extensions.common import Common, parse_args
from clade.cmds import load_cmds


def unwrap(arg, **kwarg):
    return MV.parse_cmd(*arg, **kwarg)


class MV(Common):
    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        if "MV.which_list" not in conf:
            self.which_list = ["/bin/mv"]
        else:
            self.which_list = conf["MV.which_list"]

        super().__init__(work_dir, conf)

    def parse(self, cmds):
        super().parse(cmds, self.which_list, unwrap)

    def parse_cmd(self, cmd):
        parsed_cmd = {
            "id": cmd["id"],
            "in": [],
            "out": None,
            "opts": [],
            "cwd": cmd["cwd"],
            "command": cmd["command"][0]
        }

        # We assume that 'MV' options always have such the form:
        #     [-opt]... in_file out_file
        for opt in cmd["command"][1:]:
            if re.search(r"^-", opt):
                parsed_cmd["opts"].append(opt)
            elif not parsed_cmd["in"]:
                parsed_cmd["in"].append(os.path.normpath(opt))
            else:
                parsed_cmd["out"] = os.path.normpath(opt)

        self.debug("Parsed command: {}".format(parsed_cmd))
        self.dump_cmd_by_id(cmd["id"], parsed_cmd)


def parse(args=sys.argv[1:]):
    args = parse_args(args)

    c = MV(args.work_dir, conf={"log_level": args.log_level})
    if not c.is_parsed():
        c.parse(load_cmds(args.cmds_json))
