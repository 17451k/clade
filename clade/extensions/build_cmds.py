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

import clade.extensions.model as m


from clade.cmds import iter_cmds, get_last_id
from clade.extensions.abstract import Extension

from peewee import chunked


class BuildCommands(Extension):
    __version__ = "1"

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Parsing {} commands".format(get_last_id(cmds_file, raise_exception=True)))

        with self.connect(atomic=True) as db:
            db.create_tables([m.RawPaths])

            rows = set()
            for cmd in iter_cmds(cmds_file):
                rows.add(cmd["cwd"])
                rows.add(cmd["which"])

            rows = ((path, ) for path in rows)
            self.insert_many(rows, m.RawPaths, [m.RawPaths.path])

        with self.connect(atomic=True) as db:
            for cmd in iter_cmds(cmds_file):
                cwd = m.RawPaths.get(path=cmd["cwd"])
                # which = m.RawPaths.get(path=cmd["which"])

        return

            # db.create_tables([m.BuildCommands])

            # fields = [
            #     m.BuildCommands.pid,
            #     m.BuildCommands.cwd,
            #     m.BuildCommands.which,
            #     m.BuildCommands.command
            # ]

            # for cmds in chunked(iter_cmds(cmds_file), 100):
            #     rows = []

            #     for cmd in cmds:
            #         cwd = m.RawPaths.get(path=cmd["cwd"])
            #         which = m.RawPaths.get(path=cmd["which"])

            #         rows.append((cmd["pid"], cwd, which, cmd["command"]))

            #     m.BuildCommands.insert_many(rows, fields=fields).execute(db)
