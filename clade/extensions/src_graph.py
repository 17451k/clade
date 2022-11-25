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

from clade.extensions.abstract import Extension


class SrcGraph(Extension):
    __version__ = "2"

    always_requires = ["CmdGraph", "Storage", "Alternatives"]
    requires = always_requires  # exact list is specified in presets.json

    def __init__(self, work_dir, conf=None):
        conf = conf if conf else dict()

        if "SrcGraph.requires" in conf:
            self.requires = self.always_requires + conf["SrcGraph.requires"]

        super().__init__(work_dir, conf)

        self.src_graph = dict()
        self.src_graph_folder = "src_graph"

        self.src_info = dict()
        self.src_info_file = "src_info.json"

    def load_src_graph(self, files=None):
        """Load source graph."""
        return self.load_data_by_key(self.src_graph_folder, files)

    def load_src_info(self):
        """Load information about source files."""
        return self.load_data(self.src_info_file)

    @Extension.prepare
    def parse(self, cmds_file):
        cmds = list(self.load_compilation_cmds())
        cmds_number = len(cmds)

        if cmds_number:
            self.log(f"Parsing {cmds_number} commands")
        else:
            self.error("No compilation commands found")
            raise RuntimeError

        self.__generate_src_graph(cmds)

        if not self.src_graph:
            self.error("Source graph is empty")
            raise RuntimeError

        self.dump_data(self.src_info, self.src_info_file)
        self.dump_data_by_key(self.src_graph, self.src_graph_folder)

        self.src_graph.clear()

    def load_compilation_cmds(self, with_opts=False, with_raw=False, with_deps=False):
        """Get list with all parsed compilation commands (C projects only)"""
        cmds = []

        for ext_name in [x for x in self.extensions if x not in self.always_requires]:
            for cmd in self.extensions[ext_name].load_all_cmds(
                compile_only=True,
                with_opts=with_opts,
                with_raw=with_raw,
                with_deps=with_deps,
            ):
                cmd["type"] = ext_name
                cmds.append(cmd)

        return cmds

    def __generate_src_graph(self, cmds):
        # We can do nothing without command graph
        if not self.extensions["CmdGraph"].cmd_graph_exists():
            return

        for cmd in cmds:
            cmd_id = str(cmd["id"])
            cmd_type = cmd["type"]

            # used_by is a list of commands that use (possibly indirectly)
            # output of the command with ID=cmd_id
            used_by = self.extensions["CmdGraph"].find_used_by(cmd_id)

            if self.conf.get("Compiler.get_deps"):
                src_files = self.extensions[cmd_type].load_deps_by_id(cmd_id)
            else:
                src_files = cmd["in"]

            for src_file in src_files:
                # For each source file, there may be several identical ones,
                # produced by cp, ln, or install commands.
                # Here we replace each path by its canonical path.
                src_file = self.extensions["Alternatives"].get_canonical_path(src_file)

                if src_file not in self.src_graph:
                    self.src_graph[src_file] = dict()
                    self.src_info[src_file] = {"loc": self.__count_file_loc(src_file)}

                if cmd["id"] not in self.src_graph[src_file]:
                    self.src_graph[src_file][cmd_id] = set()

                # The following means: source file src_file is compiled
                # in commaind with id=cmd_id, and is indirectly used by commands
                # from the self.src_graph[src_file][cmd_id] set
                self.src_graph[src_file][cmd_id].update(used_by)

        # Convert sets to lists for json serialization
        for file in self.src_graph:
            for cmd_id in self.src_graph[file]:
                self.src_graph[file][cmd_id] = list(self.src_graph[file][cmd_id])

                self.debug(
                    f"{file!r} is compiled in {cmd_id} and used by {self.src_graph[file][cmd_id]}"
                )

    def __count_file_loc(self, file):
        """Count number of lines of code in the file."""
        if self.conf.get("Compiler.store_deps"):
            file = self.extensions["Storage"].get_storage_path(file)

        try:
            i = -1
            with open(file, "rb") as f:
                for i, _ in enumerate(f):
                    pass

            # Returns 0 if file is empty
            return i + 1
        except FileNotFoundError:
            self.warning("Cannot get size of file {}".format(file))
            return 0

    def in_source_graph(self, file, cmd_id):
        '''Check that file and command_id is indeed present in the source graph'''
        if not hasattr(self, "src_graph") or not self.src_graph:
            self.src_graph = self.load_src_graph()

        return file in self.src_graph and cmd_id in self.src_graph[file]

    def get_used_by(self, file, cmd_id):
        '''Get all commands that use given file'''
        if not hasattr(self, "src_graph") or not self.src_graph:
            self.src_graph = self.load_src_graph()

        if self.in_source_graph(file, cmd_id):
            return self.src_graph[file][cmd_id]

        return []

    def unload_src_graph(self):
        '''Unload source graph from the memory.'''

        # Generally, this is not necessary, unless you want
        # to try to manually manage memory consumtion
        if hasattr(self, "src_graph") and self.src_graph:
            del self.src_graph
