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

from clade import Clade
from clade.extensions.utils import get_string_hash


class DotWithFiles:
    def __init__(self, include_files, exclude_files):
        self.dot = Digraph(
            graph_attr={"rankdir": "LR"}, node_attr={"shape": "rectangle"}
        )
        self.added_nodes = set()
        self.include_regex = None
        self.exclude_regex = None

        if include_files:
            self.include_regex = re.compile(
                "(" + ")|(".join(include_files) + ")"
            )

        if exclude_files:
            self.exclude_regex = re.compile(
                "(" + ")|(".join(exclude_files) + ")"
            )

    def add_node(self, file):
        if self.__filter_file(file):
            return

        file_hash = get_string_hash(file)

        if file not in self.added_nodes:
            self.dot.node(file_hash, label=re.escape(file))
            self.added_nodes.add(file)

    def add_edge(self, in_file, out_file, label):
        if self.__filter_file(in_file) or self.__filter_file(out_file):
            return

        in_hash = get_string_hash(in_file)
        out_hash = get_string_hash(out_file)

        self.dot.edge(
            in_hash,
            out_hash,
            label=label,
        )

    def __filter_file(self, file):
        if self.include_regex and not self.include_regex.search(file):
            return True

        if self.exclude_regex and self.exclude_regex.search(file):
            return True

        return False


class FileGraph:
    def __init__(self, args):
        self.clade = Clade(args.clade)

        if not self.clade.work_dir_ok():
            raise RuntimeError("Specified Clade build base is not valid")

        self.output = args.output
        self.exclude_cmd_types = args.exclude_cmd_types
        self.exclude_files = args.exclude_files
        self.include_files = args.include_files
        self.include_deps = args.include_deps

    def print(self):
        cmd_graph = self.clade.cmd_graph

        dot = DotWithFiles(self.include_files, self.exclude_files)

        for cmd_id in cmd_graph:
            cmd = self.clade.CmdGraph.load_cmd_by_id(cmd_id)

            if cmd["type"] in self.exclude_cmd_types:
                continue

            for i, cmd_out in enumerate(cmd["out"]):
                dot.add_node(cmd_out)

                # Properly print compiler commands with "-c" option
                if cmd["type"] in ["CC", "CL", "LN"]:
                    if not cmd["in"]:
                        continue
                    cmd_ins = [cmd["in"][i]]
                else:
                    cmd_ins = cmd["in"]

                for cmd_in in cmd_ins:
                    dot.add_node(cmd_in)
                    dot.add_edge(cmd_in, cmd_out, f'{cmd["type"]} ({cmd_id})')

                    if not self.include_deps:
                        continue

                    try:
                        deps = self.clade.CmdGraph.extensions[
                            cmd["type"]
                        ].load_deps_by_id(cmd["id"])
                    except AttributeError:
                        continue

                    for dep in deps:
                        if dep in cmd["in"]:
                            continue

                        dot.add_node(dep)
                        dot.add_edge(dep, cmd_in, f"Include ({cmd_id})")

        dot.dot.render("file_graph", directory=self.output, cleanup=True)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="Create a file graph based on input and output of intercepted commands."
    )

    parser.add_argument(
        "--include-deps",
        help="include header files to the graph",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--exclude-file",
        help="remove nodes from the resulted graph that match this regular expression",
        metavar="REGEXP",
        default=[],
        action="append",
        dest="exclude_files",
    )

    parser.add_argument(
        "--include-file",
        help="include only those nodes that match this regular expression",
        metavar="REGEXP",
        default=[],
        action="append",
        dest="include_files",
    )

    parser.add_argument(
        "--exclude",
        help="remove nodes from the resulted graph that came from commands of specified type",
        metavar="CMD_TYPE",
        default=[],
        action="append",
        dest="exclude_cmd_types",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="path to the output directory where generated graphs will be saved",
        metavar="DIR",
        default=os.path.curdir,
    )

    parser.add_argument(
        "clade",
        help="path to the Clade build base",
        metavar="DIR",
    )

    args = parser.parse_args(args)

    return args


def main(args=None):
    if not args:
        args = sys.argv[1:]

    f = FileGraph(parse_args(args))
    f.print()


if __name__ == "__main__":
    main()
