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


class PidGraph(Extension):
    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.pid_by_id = dict()
        self.pid_by_id_file = "pid_by_id.json"

        self.graph_dot = os.path.join(self.work_dir, "pid_graph.dot")

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Parsing {} commands".format(get_last_id(cmds_file, raise_exception=True)))

        for cmd in iter_cmds(cmds_file):
            self.pid_by_id[cmd["id"]] = cmd["pid"]

        self.dump_data(self.pid_by_id, self.pid_by_id_file)

        if self.pid_by_id and self.conf.get("PidGraph.as_picture"):
            self.__print_pid_graph(cmds_file)

        self.pid_by_id.clear()

    def __print_pid_graph(self, cmds_file):
        self.debug("Preparing dot file")

        dot = Digraph(graph_attr={'rankdir': 'LR'}, node_attr={'shape': 'rectangle'})

        cmds = list(iter_cmds(cmds_file))

        for cmd in cmds:
            cmd_node = "[{}] {}".format(cmd["id"], cmd["which"])
            dot.node(cmd["id"], label=re.escape(cmd_node))

        for cmd in cmds:
            for parent_cmd in [x for x in cmds if x["id"] == cmd["pid"]]:
                dot.edge(parent_cmd["id"], cmd["id"])

        self.debug("Rendering dot file")
        dot.render(self.graph_dot)

    def load_pid_graph(self):
        pid_by_id = self.load_pid_by_id()
        pid_graph = dict()

        for key in sorted(pid_by_id.keys(), key=lambda x: int(x)):
            key = str(key)
            pid_graph[key] = [pid_by_id[key]] + pid_graph.get(pid_by_id[key], [])

        return pid_graph

    def load_pid_by_id(self):
        return self.load_data(self.pid_by_id_file)

    def filter_cmds_by_pid(self, cmds, parsed_ids=None):
        pid_graph = self.load_pid_graph()

        if not parsed_ids:
            parsed_ids = set()
        else:
            parsed_ids = set(parsed_ids)

        filtered_cmds = []

        for cmd in sorted(cmds, key=lambda x: int(x["id"])):
            if not (set(pid_graph[cmd["id"]]) & parsed_ids):
                filtered_cmds.append(cmd)

            parsed_ids.add(cmd["id"])

        self.debug("Filtered out commands: {}".format(list(parsed_ids)))

        return filtered_cmds
