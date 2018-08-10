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

from clade.extensions.info import Info
from clade.extensions.cc import CC
from clade.extensions.ld import LD
from clade.extensions.cmd_graph import CmdGraph
from clade.extensions.src_graph import SrcGraph
from clade.extensions.callgraph import Callgraph
from clade.extensions.macros import Macros
from clade.extensions.variables import Variables
from clade.extensions.typedefs import Typedefs

workdir = None
configuration = None


def setup(work_dir, conf=None):
    global workdir
    global configuration
    workdir = work_dir
    configuration = conf


def initialize_extensions(work_dir, cmd_file, conf=None):
    setup(work_dir, conf)
    for cls in (CmdGraph, SrcGraph, Info, Callgraph, Variables, Macros, Typedefs):
        inst = cls(workdir, configuration)
        inst.parse(cmd_file)


def get_cc(identifier):
    return CC(workdir).load_cmd_by_id(identifier)


def get_cc_opts(identifier):
    return CC(workdir).load_opts_by_id(identifier)


def get_cc_deps(identifier):
    return CC(workdir).load_deps_by_id(identifier)


def get_ld(identifier):
    return LD(workdir).load_cmd_by_id(identifier)


class CommandGraph:

    def __init__(self):
        self.graph = CmdGraph(workdir, configuration).load_cmd_graph()

    @property
    def LDs(self):
        return ((desc['id'], desc) for desc in LD(workdir).load_all_cmds())

    def get_ccs_for_ld(self, identifier):
        ccs = dict()
        identifier = str(identifier)
        todo_commands = list(self.graph[identifier]['using'])
        while todo_commands:
            current = todo_commands.pop(0)
            current_type = self.graph[current]['type']

            if current_type == 'CC':
                desc = get_cc(current)
                if not any(f.endswith('.S') for f in desc['in']):
                    ccs[current] = desc
            todo_commands.extend(self.graph[current]['using'])
        return list(ccs.items())


class SourceGraph:

    def __init__(self):
        self.graph = SrcGraph(workdir, configuration).load_src_graph()

    def get_sizes(self, files):
        return {f: self.graph[f]['loc'] for f in files}

    def get_ccs_by_file(self, file):
        ccs = (get_cc(identifier) for identifier in self.graph[file]['compiled_in'])
        return [cc for cc in ccs if cc['in'][0] == file]


class CallGraph:

    def __init__(self):
        self.graph = Callgraph(workdir, configuration).load_callgraph()


class TypeDefinitions:

    def __init__(self, files):
        self.graph = Typedefs(workdir, configuration).load_typedefs(files)



