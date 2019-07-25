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

from clade.extensions.common import Common


class AS(Common):
    __version__ = "1"

    def parse(self, cmds_file):
        super().parse(cmds_file, self.conf.get("AS.which_list", []))

    def parse_cmd(self, cmd):
        parsed_cmd = super().parse_cmd(cmd, self.name)

        if self.is_bad(parsed_cmd):
            self.dump_bad_cmd_by_id(parsed_cmd["id"], parsed_cmd)
            return

        self.debug("Parsed command: {}".format(parsed_cmd))
        self.dump_cmd_by_id(cmd["id"], parsed_cmd)
