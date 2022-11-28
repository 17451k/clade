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

import functools
import os
import re
import subprocess

from clade.extensions.linker import Linker
from clade.extensions.common import Common


class LD(Linker):
    __version__ = "1"

    def parse(self, cmds_file):
        Common.parse(self, cmds_file, self.conf.get("LD.which_list", []))

    def parse_cmd(self, cmd):
        parsed_cmd = super().parse_cmd(cmd, self.name)

        if self.is_bad(parsed_cmd):
            self.dump_bad_cmd_id(parsed_cmd["id"])
            return

        self._parse_linker_opts(cmd["which"], parsed_cmd)

        self.dump_cmd_by_id(cmd["id"], parsed_cmd)

    @staticmethod
    @functools.lru_cache()
    def _get_default_searchdirs(which):
        searchdirs = []

        try:
            r = subprocess.run(f"{which} --verbose | grep SEARCH_DIR", shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            for line in r.stdout.split(";"):
                m = re.search(r"SEARCH_DIR\(\"\=(.*)\"\)", line)
                if not m:
                    continue

                if os.path.isdir(m.group(1)):
                    searchdirs.append(m.group(1))
        except Exception:
            return searchdirs

        return searchdirs
