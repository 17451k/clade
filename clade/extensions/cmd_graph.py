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

from clade.extensions.abstract import Extension


class CmdGraph(Extension):
    always_requires = ["PidGraph"]
    requires = always_requires  # exact list is specified in preset.json

    __version__ = "3"

    def __init__(self, work_dir, conf=None):
        conf = conf if conf else dict()

        if "CmdGraph.requires" in conf:
            self.requires = self.always_requires + conf["CmdGraph.requires"]

        super().__init__(work_dir, conf)

        self.graph = dict()
        self.graph_file = "cmd_graph.json"

        self.cmd_type = dict()
        self.cmd_type_file = "cmd_type.json"

        self.out_dict = dict()

        self.pdf_file = os.path.join(self.work_dir, "cmd_graph")

    def load_cmd_graph(self):
        """Load command graph."""
        return self.load_data(self.graph_file)

    def load_cmd_type(self):
        """Load information about command types."""
        return self.load_data(self.cmd_type_file)

    def load_all_cmds(self, with_opts=False, with_raw=False, filter_by_pid=False):
        cmds = list()
        bad_ids = list()
        for ext_name in [x for x in self.extensions if x not in self.always_requires]:
            for cmd in self.extensions[ext_name].load_all_cmds(
                with_opts=with_opts, with_raw=with_raw, filter_by_pid=False
            ):
                cmd["type"] = ext_name
                cmds.append(cmd)
            bad_ids.extend(self.extensions[ext_name].get_bad_ids())

        self.debug("All bad commands: {}".format(bad_ids))

        if self.conf.get("PidGraph.filter_cmds_by_pid", True) or filter_by_pid:
            cmds = self.extensions["PidGraph"].filter_cmds_by_pid(cmds, parsed_ids=bad_ids)

        return cmds

    def load_all_cmds_by_type(self, cmd_type, filter_by_pid=True):
        cmds = self.get_ext_obj(cmd_type).load_all_cmds(filter_by_pid=False)

        if not filter_by_pid:
            return cmds

        if not self.graph:
            cmd_graph = self.load_cmd_graph()
        else:
            cmd_graph = self.graph

        return [cmd for cmd in cmds if cmd["id"] in cmd_graph]

    def load_cmd_by_id(self, cmd_id):
        if not hasattr(self, "cmd_type") or not self.cmd_type:
            self.cmd_type = self.load_cmd_type()

        cmd = self.extensions[self.cmd_type[cmd_id]].load_cmd_by_id(cmd_id)
        cmd["type"] = self.cmd_type[cmd_id]

        return cmd

    @Extension.prepare
    def parse(self, cmds_file):
        cmds = self.load_all_cmds()
        self.log("Parsing {} commands".format(len(cmds)))

        for cmd in sorted(cmds, key=lambda x: int(x["id"])):
            self.__add_to_graph(cmd)

        self.dump_data(self.graph, self.graph_file)
        self.dump_data(self.cmd_type, self.cmd_type_file)

        if self.graph:
            if self.conf.get("CmdGraph.as_picture"):
                self.__print_cmd_graph()
        else:
            self.error("Command graph is empty")
            raise RuntimeError

        self.graph.clear()
        self.cmd_type.clear()

    def __add_to_graph(self, cmd):
        self.cmd_type[cmd["id"]] = cmd["type"]

        out_id = str(cmd["id"])
        if out_id not in self.graph:
            self.graph[out_id] = self.__get_new_value()

        for cmd_in in (i for i in cmd["in"] if i in self.out_dict):
            in_id = self.out_dict[cmd_in]

            if out_id not in self.graph[in_id]["used_by"]:
                self.graph[in_id]["used_by"].append(out_id)
            if in_id not in self.graph[out_id]["using"]:
                self.graph[out_id]["using"].append(in_id)

        # Rewrite out_dict[cmd_out] values to keep the latest used command id
        for cmd_out in cmd["out"]:
            self.out_dict[cmd_out] = out_id

    def __print_cmd_graph(self):
        self.debug("Preparing dot file")

        dot = Digraph(graph_attr={'rankdir': 'LR'}, node_attr={'shape': 'rectangle'})

        for cmd_id in self.graph:
            cmd_type = self.cmd_type[cmd_id]
            cmd = self.extensions[cmd_type].load_cmd_by_id(cmd_id)

            cmd_node = "[{}] {}".format(cmd["id"], cmd_type)
            dot.node(cmd["id"], label=re.escape(cmd_node))

            for using_id in self.graph[cmd_id]["using"]:
                dot.edge(using_id, cmd_id)

        self.debug("Rendering dot file")
        dot.render(self.pdf_file, cleanup=True)

    @staticmethod
    def __get_new_value():
        return {"used_by": list(), "using": list()}

    def get_ext_obj(self, ext_name):
        if ext_name not in self.extensions:
            raise RuntimeError(
                "{!r} extension was not executed during command graph constructing".format(
                    ext_name
                )
            )

        return self.extensions[ext_name]

    def cmd_graph_exists(self):
        '''True if CmdGraph exists and can be used'''
        return self.file_exists(self.graph_file)

    def find_used_by(self, cmd_id):
        '''Find all commands that use (possibly indirectly) output file from the given command'''
        if not self.graph:
            self.graph = self.load_cmd_graph()

        used_by = set()

        if cmd_id not in self.graph:
            return used_by

        for used_by_id in self.graph[cmd_id]["used_by"]:
            used_by.add(used_by_id)
            used_by.update(self.find_used_by(used_by_id))

        return used_by
