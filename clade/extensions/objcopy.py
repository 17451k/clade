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

from clade.extensions.common import Common, parse_args
from clade.cmds import load_cmds


def unwrap(arg, **kwarg):
    return Objcopy.parse_cmd(*arg, **kwarg)


class Objcopy(Common):
    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        if "Objcopy.which_list" not in conf:
            self.which_list = ["/usr/bin/objcopy"]
        else:
            self.which_list = conf["Objcopy.which_list"]

        super().__init__(work_dir, conf)

    def parse(self, cmds):
        super().parse(cmds, self.which_list, unwrap)

    def parse_cmd(self, cmd):
        parsed_cmd = super().parse_cmd(cmd, self.name)

        # objcopy has only one input file and no more than one output file.
        # out file is the same as in file if it didn't specified.
        if len(parsed_cmd["in"]) == 2:
            parsed_cmd["out"] = parsed_cmd["in"][-1]
            parsed_cmd["in"] = parsed_cmd["in"][:-1]
        elif len(parsed_cmd["in"]) > 2:
            parsed_cmd["out"] = parsed_cmd["in"][-1]

        self.debug("Parsed command: {}".format(parsed_cmd))
        self.dump_cmd_by_id(cmd["id"], parsed_cmd)


def parse(args=sys.argv[1:]):
    args = parse_args(args)

    c = Objcopy(args.work_dir, conf={"log_level": args.log_level})
    if not c.is_parsed():
        c.parse(load_cmds(args.cmds_json))
