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

import re
import os

from graphviz import Digraph

from clade.cmds import iter_cmds, get_last_id
from clade.extensions.abstract import Extension
from clade.extensions.model import PID


class PidGraph(Extension):
    __version__ = "2"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.graph_dot = os.path.join(self.work_dir, "pid_graph.dot")

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Parsing {} commands".format(get_last_id(cmds_file, raise_exception=True)))

        rows = [(cmd["pid"], ) for cmd in iter_cmds(cmds_file)]

        with self.connect() as db:
            db.create_tables([PID])
            self.insert_many(rows, PID, [PID.pid])

        if rows and self.conf.get("PidGraph.as_picture"):
            self.__print_pid_graph(cmds_file)

    def __print_pid_graph(self, cmds_file):
        dot = Digraph(graph_attr={'rankdir': 'LR'}, node_attr={'shape': 'rectangle'})

        cmds = list(iter_cmds(cmds_file))

        for cmd in iter_cmds(cmds_file):
            cmd_node = "[{}] {}".format(cmd["id"], cmd["which"])
            dot.node(cmd["id"], label=re.escape(cmd_node))

        for cmd in iter_cmds(cmds_file):
            for parent_cmd in [x for x in cmds if x["id"] == cmd["pid"]]:
                dot.edge(parent_cmd["id"], cmd["id"])

        dot.render(self.graph_dot)

    # TODO: repimplement public interface
    # def load_pid_graph(self):
    #     return self.load_data(self.graph_file)

    # def load_pid_by_id(self):
    #     return {str(record.id): str(record.pid) for record in PID.select()}

    def get_all_pids(self, id):
        row = PID.select().where(PID.id == id).first()

        if not row:
            return []

        pid = row.pid
        return [pid] + self.get_all_pids(pid)

    def filter_cmds_by_pid(self, cmds, parsed_ids=None):
        if not parsed_ids:
            parsed_ids = set()
        else:
            parsed_ids = {int(parsed_id) for parsed_id in parsed_ids}

        filtered_cmds = []

        for cmd in sorted(cmds, key=lambda x: int(x["id"])):
            if not (set(self.get_all_pids(cmd["id"])) & parsed_ids):
                filtered_cmds.append(cmd)

            parsed_ids.add(int(cmd["id"]))

        return filtered_cmds
