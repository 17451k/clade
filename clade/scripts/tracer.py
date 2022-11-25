# Copyright (c) 2020 ISP RAS (http://www.ispras.ru)
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

import argparse
import collections
import graphviz
import os
import re
import sys

from typing import List

from clade import Clade

Function = collections.namedtuple("Function", ["name", "path"])


def nested_dict():
    return collections.defaultdict(nested_dict)


class Tracer:
    def __init__(self, build_base):
        self.clade = Clade(build_base)

        if not self.clade.work_dir_ok():
            raise RuntimeError("Specified Clade build base is not valid")

    def find_functions(self, func_names: List[str]):
        functions = set()

        s_regex = re.compile("^" + ("$|^".join(func_names)) + "$")

        for func in self.clade.functions:
            if s_regex.match(func):
                for definition in self.clade.functions[func]:
                    functions.add(Function(func, definition["file"]))

        if not functions:
            raise RuntimeError(
                "Specified functions were not found in the Clade build base"
            )
        elif len(functions) < len(func_names):
            for func_name in [
                x for x in func_names if x not in [y.name for y in functions]
            ]:
                raise RuntimeError(
                    "{!r} function was not found in the Clade build base".format(
                        func_name
                    )
                )

        return list(functions)

    def find_functions_with_prefix(self, prefix):
        functions = set()

        for func in self.clade.functions:
            if re.search(prefix, func, flags=re.I):
                for definition in self.clade.functions[func]:
                    functions.add(Function(func, definition["file"]))

        if not functions:
            raise RuntimeError(
                "Functions with prefix {!r} were not found".format(prefix)
            )

        return list(functions)

    def trace(self, from_func: Function, to_func: Function):
        return self.trace_list([from_func], [to_func])

    def trace_list(self, from_funcs: List[Function], to_funcs: List[Function]):
        trace = dict()

        queue = collections.deque()
        queue.extend(from_funcs)
        visited = set()

        while len(queue) > 0:
            func = queue.pop()

            visited.add(func)

            if not self.__calls_somebody(func):
                continue

            calls = self.clade.callgraph[func.path][func.name]["calls"]
            for called_file in calls:
                for called_func_name in calls[called_file]:
                    called_func = Function(called_func_name, called_file)

                    if func in trace:
                        trace[func].append(called_func)
                    else:
                        trace[func] = [called_func]

                    if called_func not in to_funcs and called_func not in visited:
                        queue.append(called_func)

        trace = self.__reverse_trace(trace)
        trace = self.__filter_trace(trace, to_funcs)
        return trace

    @staticmethod
    def __reverse_trace(trace):
        reversed_trace = dict()

        for func in trace:
            for called_func in trace[func]:
                if called_func in reversed_trace:
                    reversed_trace[called_func].append(func)
                else:
                    reversed_trace[called_func] = [func]

        return reversed_trace

    @staticmethod
    def __filter_trace(trace, to_funcs):
        filtered_trace = dict()

        queue = collections.deque()
        queue.extend(to_funcs)
        visited = set()

        while len(queue) > 0:
            called_func = queue.pop()

            visited.add(called_func)

            if called_func not in trace:
                continue

            for func in trace[called_func]:
                if func in filtered_trace:
                    filtered_trace[func].append(called_func)
                else:
                    filtered_trace[func] = [called_func]

                if func not in visited:
                    queue.append(func)

        return filtered_trace

    @staticmethod
    def print_dot(trace, filename):
        dot = graphviz.Digraph(
            graph_attr={"rankdir": "LR"}, node_attr={"shape": "rectangle"}
        )

        nodes = set()

        for func in trace:
            for called_func in trace[func]:
                if func.name not in nodes:
                    nodes.add(func.name)
                    dot.node(func.name)

                if called_func.name not in nodes:
                    nodes.add(called_func.name)
                    dot.node(called_func.name)

                dot.edge(func.name, called_func.name)

        dot.render(filename)

    def __calls_somebody(self, func):
        if func.path not in self.clade.callgraph:
            return False

        if func.name not in self.clade.callgraph[func.path]:
            return False

        if "calls" not in self.clade.callgraph[func.path][func.name]:
            return False

        return True


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="Create a graph of all call paths between 2 functions."
    )

    parser.add_argument(
        "-f",
        "--from",
        help="name of the function, from which call paths will be searched",
        metavar="NAME",
        default=[],
        action="append",
        dest="from_funcs",
    )

    parser.add_argument(
        "-t",
        "--to",
        help="name of the function, to which call paths will be searched",
        metavar="NAME",
        default=[],
        action="append",
        dest="to_funcs",
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

    args = parse_args(args)

    t = Tracer(args.clade)

    from_funcs = t.find_functions(args.from_funcs)
    to_funcs = t.find_functions(args.to_funcs)

    for from_func in from_funcs:
        for to_func in to_funcs:
            trace = t.trace(from_func, to_func)

            filename = os.path.join(args.output, f"{from_func.name}-{to_func.name}.dot")
            t.print_dot(trace, filename)


if __name__ == "__main__":
    main()
