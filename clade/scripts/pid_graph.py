# Copyright (c) 2022 Ilya Shchepetkov
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

import argparse
import os
import re
import sys

from graphviz import Digraph

from clade.cmds import iter_cmds


class PidGraph:
    def __init__(self, args):
        self.output = args.output
        self.cmds_file = args.cmds_file

    def print(self):
        dot = Digraph(graph_attr={"rankdir": "LR"}, node_attr={"shape": "rectangle"})

        cmds = list(iter_cmds(self.cmds_file))

        for cmd in cmds:
            cmd_node = "[{}] {}".format(cmd["id"], cmd["which"])
            dot.node(cmd["id"], label=re.escape(cmd_node))

        for cmd in cmds:
            for parent_cmd in [x for x in cmds if x["id"] == cmd["pid"]]:
                dot.edge(parent_cmd["id"], cmd["id"])

        dot.render("pid_graph", directory=self.output, cleanup=True)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="Create a pid graph based on ids and parent ids of intercepted commands."
    )

    parser.add_argument(
        "-o",
        "--output",
        help="path to the output directory where generated graphs will be saved",
        metavar="DIR",
        default=os.path.curdir,
    )

    parser.add_argument(
        "cmds_file",
        help="path to the Clade cmds.txt file",
        metavar="FILE",
    )

    args = parser.parse_args(args)

    return args


def main(args=None):
    if not args:
        args = sys.argv[1:]

    f = PidGraph(parse_args(args))
    f.print()


if __name__ == "__main__":
    main()
