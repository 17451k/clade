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

import hashlib
import re
import os
import sys

from graphviz import Digraph

from clade.extensions.abstract import Extension
from clade.extensions.utils import common_main, merge_preset_to_conf


class CmdGraph(Extension):
    always_requires = ["PidGraph", "Path"]
    requires = always_requires + ["CC", "LD", "AR"]

    def __init__(self, work_dir, conf=None, preset="base"):
        conf = conf if conf else dict()
        conf = merge_preset_to_conf(preset, conf)

        if "CmdGraph.requires" in conf:
            self.requires = self.always_requires + conf["CmdGraph.requires"]

        super().__init__(work_dir, conf, preset)

        self.graph = dict()
        self.graph_file = "cmd_graph.json"

        self.graph_dot = os.path.join(self.work_dir, "cmd_graph.dot")

    def load_cmd_graph(self):
        """Load command graph."""
        return self.load_data(self.graph_file)

    def load_all_cmds(self, filter_by_pid=False):
        cmds = list()
        for ext_name in [x for x in self.extensions if x not in self.always_requires]:
            for cmd in self.extensions[ext_name].load_all_cmds(filter_by_pid=False):
                cmd["type"] = ext_name
                cmds.append(cmd)

        if self.conf.get("PidGraph.filter_cmds_by_pid", True) or filter_by_pid:
            cmds = self.extensions["PidGraph"].filter_cmds_by_pid(cmds)

        return cmds

    def load_all_cmds_by_type(self, cmd_type, filter_by_pid=True):
        ext_obj = self.get_ext_obj(cmd_type)

        return ext_obj.load_all_cmds(filter_by_pid=filter_by_pid)

    def normalize_all_paths(self, cmds):
        for cmd in cmds:
            self.extensions["Path"].normalize_abs_path(cmd["cwd"])
            self.extensions["Path"].normalize_rel_paths(cmd["in"], cmd["cwd"])
            self.extensions["Path"].normalize_rel_paths(cmd["out"], cmd["cwd"])

            if hasattr(self.extensions[cmd["type"]], "load_deps_by_id"):
                for src_file in self.extensions[cmd["type"]].load_deps_by_id(cmd["id"]):
                    self.extensions["Path"].normalize_rel_path(src_file, cmd["cwd"])

        self.extensions["Path"].dump_paths()

    @Extension.prepare
    def parse(self, cmds_file):
        cmds = self.load_all_cmds()
        self.log("Parsing {} commands".format(len(cmds)))

        self.normalize_all_paths(cmds)

        for cmd in sorted(cmds, key=lambda x: int(x["id"])):
            self.__add_to_graph(cmd)

        self.dump_data(self.graph, self.graph_file)

        if self.graph:
            if self.conf.get("CmdGraph.as_picture"):
                self.__print_source_graph(cmds_file)
        else:
            self.warning("Command graph is empty")

        self.graph.clear()

    def __add_to_graph(self, cmd, out_dict=dict()):
        out_id = str(cmd["id"])
        if out_id not in self.graph:
            self.graph[out_id] = self.__get_new_value(cmd["type"])

        for cmd_in in (i for i in self.extensions["Path"].get_rel_paths(cmd["in"], cmd["cwd"]) if i in out_dict):
            in_id = out_dict[cmd_in]
            self.graph[in_id]["used_by"].add(out_id)
            self.graph[out_id]["using"].add(in_id)

        # Rewrite out_dict[cmd_out] values to keep the latest used command id
        for cmd_out in self.extensions["Path"].get_rel_paths(cmd["out"], cmd["cwd"]):
            out_dict[cmd_out] = out_id

    def __print_source_graph(self, cmds_file):
        dot = Digraph(graph_attr={'rankdir': 'LR'}, node_attr={'shape': 'rectangle'})

        added_nodes = dict()

        graph = self.graph
        for cmd_id in graph:
            cmd_type = graph[cmd_id]["type"]
            cmd = self.extensions[cmd_type].load_cmd_by_id(cmd_id)

            for cmd_out in self.extensions["Path"].get_rel_paths(cmd["out"], cmd["cwd"]):
                # TODO: Replace hash by file_id
                cmd_out_hash = hashlib.md5(cmd_out.encode('utf-8')).hexdigest()

                if cmd_out not in added_nodes:
                    dot.node(cmd_out_hash, label=re.escape(cmd_out))
                    added_nodes[cmd_out] = 1

                for cmd_in in self.extensions["Path"].get_rel_paths(cmd["in"], cmd["cwd"]):
                    cmd_in_hash = hashlib.md5(cmd_in.encode('utf-8')).hexdigest()

                    if cmd_in not in added_nodes:
                        dot.node(cmd_in_hash, label=re.escape(cmd_in))
                        added_nodes[cmd_in] = 1

                    dot.edge(cmd_in_hash, cmd_out_hash, label="{}({})".format(cmd_type, cmd_id))

        dot.render(self.graph_dot)

    @staticmethod
    def __get_new_value(cmd_type):
        return {
            "used_by": set(),
            "using": set(),
            "type": cmd_type
        }

    def get_ext_obj(self, ext_name):
        if ext_name not in self.extensions:
            raise RuntimeError("{!r} extension was not executed during command graph constructing".format(ext_name))

        return self.extensions[ext_name]


def main(args=sys.argv[1:]):
    common_main(CmdGraph, args)
