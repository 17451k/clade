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

from clade.extensions.abstract import Extension


class CDB(Extension):
    requires = ["SrcGraph"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        super().__init__(work_dir, conf)

        self.cdb = []
        # DO NOT put CDB.output option to the presets file
        self.cdb_file = self.conf.get(
            "CDB.output", os.path.join(self.work_dir, "compile_commands.json")
        )

    @Extension.prepare
    def parse(self, cmds_file):
        cmds = self.extensions["SrcGraph"].load_all_cmds(
            with_opts=True, with_raw=True, with_deps=True
        )

        for cmd in cmds:
            for i, cmd_in in enumerate(cmd["in"]):
                arguments = [cmd["command"][0]] + cmd["opts"] + [cmd_in]
                if cmd["out"]:
                    if "-c" in cmd["opts"]:
                        arguments.extend(["-o", cmd["out"][i]])
                    else:
                        arguments.extend(["-o", cmd["out"][0]])

                self.cdb.append(
                    {
                        "directory": cmd["cwd"],
                        "arguments": arguments,
                        "file": cmd_in,
                    }
                )

        self.dump_data(self.cdb, self.cdb_file)

    def load_cdb(self):
        """Load compilation database."""
        return self.load_data(self.cdb_file)
