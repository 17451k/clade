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

from typing import List, Dict
from clade import Clade

Function = collections.namedtuple("Function", ["name", "path"])
Trace = Dict[Function, List[Function]]


def nested_dict():
    return collections.defaultdict(nested_dict)


class Tracer:
    def __init__(self, build_base):
        self.clade = Clade(build_base)

        if not self.clade.work_dir_ok():
            raise RuntimeError("Specified Clade build base is not valid")

    def find_functions(self, func_names: List[str]) -> List[Function]:
        # Find functions in the Clade build base, and convert list of strings
        # to a list of Function objects required by most Tracer methods

        if not func_names:
            return list()

        functions = set()

        for func in func_names:
            definitions = self.clade.load_definitions(func)

            for definition in definitions:
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

    def load_all_functions(self) -> List[Function]:
        # Return all available functions from the Clade builds base.

        functions = set()

        # Loading all available functions
        for func, funcs in self.clade.Functions.yield_functions():
            for definition in funcs[func]:
                functions.add(Function(func, definition["file"]))

        return list(functions)

    def find_functions_with_prefix(self, prefix: str) -> List[Function]:
        # Find functions in the Clade build base whose name match the
        # specified prefix, and convert them to a list of Function
        # objects required by most Tracer methods

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

    def trace(
        self, from_func: Function, to_func: Function
    ) -> Dict[Function, List[Function]]:
        # Get all call traces between 'from_func' and 'to_func' functions.
        return self.trace_list([from_func], [to_func])

    def trace_list(self, from_funcs: List[Function], to_funcs: List[Function]) -> Trace:
        # Get all call traces between 2 groups of functions (from_funcs and to_funcs).

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

        if to_funcs:
            trace = self.__remove_extra_paths(trace, to_funcs)

        return trace

    def trace_full(self) -> Trace:
        # Get full callgraph from the Clade database, in the Trace format.

        trace = dict()

        for call in self.clade.Callgraph.traverse_calls():
            from_func = Function(name=call.from_func, path=call.from_file)
            to_func = Function(name=call.to_func, path=call.to_file)

            if from_func not in trace:
                trace[from_func] = set()

            trace[from_func].add(to_func)

        return trace

    @staticmethod
    def __reverse_trace(trace: Trace) -> Trace:
        # Reverse a trace, so it can be more easily filtered later.

        reversed_trace = dict()

        for func in trace:
            for called_func in trace[func]:
                if called_func in reversed_trace:
                    reversed_trace[called_func].append(func)
                else:
                    reversed_trace[called_func] = [func]

        return reversed_trace

    @staticmethod
    def __remove_extra_paths(trace: Trace, from_funcs: List[Function]) -> Trace:
        # Remove all paths from the trace, which are not started from one
        # of the "from_funcs" functions

        reversed_trace = Tracer.__reverse_trace(trace)
        trimmed_trace = dict()

        queue = collections.deque()
        queue.extend(from_funcs)
        visited = set()

        while len(queue) > 0:
            called_func = queue.pop()

            visited.add(called_func)

            if called_func not in reversed_trace:
                continue

            for func in reversed_trace[called_func]:
                if func in trimmed_trace:
                    trimmed_trace[func].append(called_func)
                else:
                    trimmed_trace[func] = [called_func]

                if func not in visited:
                    queue.append(func)

        return trimmed_trace

    @staticmethod
    def print_dot(trace: Trace, filename: str) -> None:
        # Print trace to a pdf file

        dot = graphviz.Digraph(
            graph_attr={"rankdir": "LR"}, node_attr={"shape": "rectangle"}
        )

        nodes = set()

        for func in trace:
            func_node_name = Tracer.__func_to_node_name(func)

            if func.name not in nodes:
                nodes.add(func.name)
                dot.node(func_node_name)

            for called_func in trace[func]:
                called_func_node_name = Tracer.__func_to_node_name(called_func)

                if called_func.name not in nodes:
                    nodes.add(called_func.name)
                    dot.node(called_func_node_name)

                dot.edge(func_node_name, called_func_node_name)

        dot.render(filename, cleanup=True)

    @staticmethod
    def __func_to_node_name(func: Function) -> str:
        # Construct a name for the Graphviz node
        # that represents a Function object.

        return f"[{os.path.basename(func.path)}]\n{func.name}"

    def __calls_somebody(self, func: Function) -> bool:
        # Check that a function contains function calls in its body.
        if func.path not in self.clade.callgraph:
            return False

        if func.name not in self.clade.callgraph[func.path]:
            return False

        if "calls" not in self.clade.callgraph[func.path][func.name]:
            return False

        return True

    def filter_trace_from(self, trace: Trace, from_filter=List[Function]) -> Trace:
        # Remove all paths from the trace that start with one of the "from_filter"
        # functions.

        if not from_filter:
            return trace

        from_trace = self.trace_list(from_filter, list())

        for key in from_filter:
            del trace[key]

        for key in trace:
            trace[key] = [f for f in trace[key] if f not in from_trace.get(key, [])]

        return trace

    def filter_trace_to(self, trace: Trace, to_filter=List[Function]) -> Trace:
        # Remove all paths from the trace that finish with one of the "from_filter"
        # functions.

        if not to_filter:
            return trace

        to_trace = self.trace_list(self.load_all_functions(), to_filter)

        for key in to_filter:
            del trace[key]

        for key in trace:
            trace[key] = [
                f for f in trace[key] if f not in f not in to_trace.get(key, [])
            ]

        return trace


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="Create a graph of all call paths between specified functions."
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
        "--from-filter",
        help="name of the function, from which call paths will not be included in the callgraph",
        metavar="NAME",
        default=[],
        action="append",
        dest="from_filter",
    )

    parser.add_argument(
        "--to-filter",
        help="name of the function, to which call paths will not be included in the callgraph",
        metavar="NAME",
        default=[],
        action="append",
        dest="to_filter",
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

    if not args.from_funcs and not args.to_funcs:
        trace = t.trace_full()
    else:
        if args.from_funcs:
            from_funcs = t.find_functions(args.from_funcs)
        else:
            from_funcs = t.load_all_functions()

        if args.to_funcs:
            to_funcs = t.find_functions(args.to_funcs)
        else:
            to_funcs = list()

        trace = t.trace_list(from_funcs, to_funcs)

    if not trace:
        sys.exit("Something is wrong: callgraph is empty")

    trace = t.filter_trace_from(trace, t.find_functions(args.from_filter))
    trace = t.filter_trace_to(trace, t.find_functions(args.to_filter))

    t.print_dot(trace, "callgraph")


if __name__ == "__main__":
    main()
