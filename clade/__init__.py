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

import os
import sys

from clade.intercept import intercept
from clade.extensions.abstract import Extension
from clade.extensions.cdb import CDB
from clade.extensions.functions import Functions
from clade.extensions.callgraph import Callgraph
from clade.extensions.cmd_graph import CmdGraph
from clade.extensions.macros import Macros
from clade.extensions.pid_graph import PidGraph
from clade.extensions.src_graph import SrcGraph
from clade.extensions.storage import Storage
from clade.extensions.typedefs import Typedefs
from clade.extensions.variables import Variables
from clade.extensions.path import Path
from clade.extensions.utils import parse_args


class Clade:
    """Interface to all functionality available in Clade.

    Args:
        work_dir: A path to the working directory where all output files will be stored
        cmds_file: A path to the file where intercepted commands are or will be saved
        conf: A dictionary with optional arguments
        preset: Name of one of the available preset configurations

    Raises:
        RuntimeError: You did something wrong

    TODO:
        Check that command was already intercepted
        Check that intercept() argument is list, not string
    """

    def __init__(self, work_dir="clade", cmds_file="cmds.txt", conf=None, preset="base"):
        self.work_dir = os.path.abspath(str(work_dir))
        self.cmds_file = os.path.abspath(cmds_file)
        self.conf = conf if conf else dict()
        self.preset = preset

        self._CmdGraph = None
        self._cmd_graph = None

        self._SrcGraph = None
        self._src_graph = None
        self._src_info = None

        self._PidGraph = None
        self._pid_graph = None
        self._pid_by_id = None

        self._Storage = Storage(self.work_dir, self.conf, self.preset)

        self._Callgraph = None
        self._callgraph = None

        self._Functions = None
        self._functions = None
        self._functions_by_file = None

        self._CDB = None
        self._cdb = None

        self._Path = None

    def intercept(self, command, cwd=os.getcwd(), append=False, use_wrappers=False):
        """Execute intercepting of build commands.

        Args:
            command: A list of strings representing build command to run and intercept
            cwd: A path to the directory where build command will be executed
            append: A boolean allowing to append intercepted commands to already existing file with commands
            use_wrappers: A boolean enabling intercepting mode based on wrappers

        Returns:
            0 if everything went successful and error code otherwise
        """

        return intercept(command=command, cwd=cwd, output=self.cmds_file, append=append, use_wrappers=use_wrappers)

    def parse_all(self, cmds_file=None):
        """Execute parse() method of all extensions available in Clade.

        It can be done only for projects written in C.
        """
        if cmds_file:
            self.cmds_file = cmds_file

        self.parse("Callgraph")

        # Backup "force" options
        force_current = self.conf.get("force_current", False)
        force = self.conf.get("force", False)

        # If  "force" is True, then set "force_current" to True
        # and "force" to False
        self.conf["force_current"] = self.conf.get("force", False)
        self.conf["force"] = False

        extensions = ("Variables", "Macros", "Typedefs")
        for ext_name in extensions:
            self.parse(ext_name)

        # Restore "force" options
        self.conf["force_current"] = force_current
        self.conf["force"] = force

    def parse(self, ext_name):
        """Execute parse() method of a specified Clade extension.

        Args:
            ext_name: An extension name, like "Callgraph"

        Returns:
            An extension object
        """
        ext_class = Extension.find_subclass(ext_name)

        e = ext_class(self.work_dir, conf=self.conf, preset=self.preset)
        e.parse(self.cmds_file)

        return e

    @property
    def CmdGraph(self):
        """Object of "CmdGraph" extension."""
        if not self._CmdGraph:
            self._CmdGraph = CmdGraph(self.work_dir, self.conf, self.preset)

        if not self._CmdGraph.is_parsed():
            self.parse("CmdGraph")

        return self._CmdGraph

    @property
    def cmd_graph(self):
        """Command graph connects commands by their input and output files."""
        if not self._cmd_graph:
            self._cmd_graph = self.CmdGraph.load_cmd_graph()

        return self._cmd_graph

    @property
    def cmd_ids(self):
        """List of identifiers of all parsed commands."""
        return self.cmd_graph.keys()

    @property
    def cmds(self):
        """List of all parsed commands."""
        cmds = self.CmdGraph.load_all_cmds()
        return [self.__normalize_cmd(cmd) for cmd in cmds]

    def get_cmds(self, with_opts=False, with_raw=False):
        """Get list with all parsed commands."""
        cmds = self.CmdGraph.load_all_cmds(with_opts=with_opts, with_raw=with_raw)
        return [self.__normalize_cmd(cmd) for cmd in cmds]

    @property
    def compilation_cmds(self):
        """List of all parsed compilation commands (C projects only)."""
        cmds = self.SrcGraph.load_all_cmds()
        return [self.__normalize_cmd(cmd) for cmd in cmds]

    def get_compilation_cmds(self, with_opts=False, with_raw=False, with_deps=False):
        """Get list with all parsed compilation commands (C projects only)."""
        cmds = self.SrcGraph.load_all_cmds()

        for cmd in cmds:
            if with_opts:
                cmd["opts"] = self.get_cmd_opts(cmd["id"])

            if with_raw:
                cmd["command"] = self.get_cmd_raw(cmd["id"])

            if with_deps:
                cmd["deps"] = self.get_cmd_deps(cmd["id"])

        return [self.__normalize_cmd(cmd) for cmd in cmds]

    def get_cmd_type(self, cmd_id):
        """Get type of a command by its identifier."""
        if cmd_id not in self.cmd_graph:
            raise RuntimeError("Can't find {!r} id in the command graph".format(cmd_id))

        return self.cmd_graph[cmd_id]["type"]

    def get_cmd(self, cmd_id, with_opts=False, with_raw=False, with_deps=False):
        """Get command by its identifier."""
        cmd_type = self.get_cmd_type(cmd_id)

        if with_deps and cmd_type not in ["CC", "CL"]:
            raise RuntimeError("Only compiler commands have dependencies")

        ext_obj = self.CmdGraph.get_ext_obj(cmd_type)
        cmd = ext_obj.load_cmd_by_id(cmd_id)

        if with_opts:
            cmd["opts"] = self.get_cmd_opts(cmd_id)

        if with_raw:
            cmd["command"] = self.get_cmd_raw(cmd_id)

        if with_deps:
            cmd["deps"] = self.get_cmd_deps(cmd_id)

        cmd = self.__normalize_cmd(cmd)

        return cmd

    def get_cmd_opts(self, cmd_id):
        """Get list of options of a command by its identifier."""
        cmd_type = self.get_cmd_type(cmd_id)
        ext_obj = self.CmdGraph.get_ext_obj(cmd_type)

        return ext_obj.load_opts_by_id(cmd_id)

    def get_cmd_raw(self, cmd_id):
        """Get raw intercepted command by its identifier."""
        cmd_type = self.get_cmd_type(cmd_id)
        ext_obj = self.CmdGraph.get_ext_obj(cmd_type)

        return ext_obj.load_raw_by_id(cmd_id)

    def get_cmd_deps(self, cmd_id):
        """Get list of dependencies of a compiler command by its identifier."""
        cmd_type = self.get_cmd_type(cmd_id)

        if cmd_type not in ["CC", "CL"]:
            raise RuntimeError("Only compiler commands have dependencies")

        cc_obj = self.CmdGraph.get_ext_obj(cmd_type)

        deps = cc_obj.load_deps_by_id(cmd_id)
        cwd = cc_obj.load_cmd_by_id(cmd_id)["cwd"]
        return self.__normalize_deps(deps, cwd)

    def get_all_cmds_by_type(self, cmd_type):
        """Get list of all parsed commands filtered by their type."""
        cmds = self.CmdGraph.load_all_cmds_by_type(cmd_type)
        return [self.__normalize_cmd(cmd) for cmd in cmds]

    def get_root_cmds(self, cmd_id):
        """Get list of identifiers of all root commands from a command graph of a given command identifier."""
        if cmd_id not in self.cmd_graph:
            raise RuntimeError("Can't find {!r} id in the command graph".format(cmd_id))

        using = self.cmd_graph[cmd_id]["using"]

        indirect_using = []
        for using_id in using:
            indirect_using.extend(self.get_root_cmds(using_id))

        using.extend(indirect_using)
        return using

    def get_root_cmds_by_type(self, cmd_id, cmd_type):
        return [x for x in self.get_root_cmds(cmd_id) if self.get_cmd_type(x) == cmd_type]

    def get_leaf_cmds(self, cmd_id):
        """Get list of identifiers of all leaf commands from a command graph of a given command identifier."""
        if cmd_id not in self.cmd_graph:
            raise RuntimeError("Can't find {!r} id in the command graph".format(cmd_id))

        used_by = self.cmd_graph[cmd_id]["used_by"]

        indirect_used_by = []
        for used_by_id in used_by:
            indirect_used_by.extend(self.get_leaf_cmds(used_by_id))

        used_by.extend(indirect_used_by)
        return used_by

    @property
    def SrcGraph(self):
        """Object of "SrcGraph" extension."""
        if not self._SrcGraph:
            self._SrcGraph = SrcGraph(self.work_dir, self.conf, self.preset)

        if not self._SrcGraph.is_parsed():
            self.parse("SrcGraph")

        return self._SrcGraph

    @property
    def src_graph(self):
        """Source graph.

        For a given source file it can show in which commands this file is compiled,
        and in which commands it is indirectly used.
        """
        if not self._src_graph:
            self._src_graph = self.SrcGraph.load_src_graph()

        return self._src_graph

    @property
    def src_info(self):
        """Dictionary that contain number of lines of code for all source files."""
        if not self._src_info:
            self._src_info = self.SrcGraph.load_src_info()

        return self._src_info

    def get_file_size(self, file):
        """Get a number of lines of code for a given file.

        Args:
            file: A name of the source file from the source graph
        """

        try:
            return int(self.src_info[file]["loc"])
        except KeyError:
            raise RuntimeError("Can't find {!r} file in the source graph".format(file))

    def get_compilation_cmds_ids_by_file(self, file):
        """Get list of identifiers of compilation commands in which the file was compiled.

        Args:
            file: A name of the source file from the source graph
        """
        return (cmd_id for cmd_id in self.SrcGraph.load_src_graph([file])[file]['compiled_in'])

    def get_compilation_cmds_by_file(self, file):
        """Get list of compilation commands in which the file was compiled.

        Args:
            file: A name of the source file from the source graph
        """
        return (self.get_cmd(cmd_id) for cmd_id in self.get_compilation_cmds_ids_by_file(file))

    @property
    def PidGraph(self):
        """Object of "PidGraph" extension."""
        if not self._PidGraph:
            self._PidGraph = PidGraph(self.work_dir, self.conf, self.preset)

        if not self._PidGraph.is_parsed():
            self.parse("PidGraph")

        return self._PidGraph

    @property
    def pid_graph(self):
        """Pid graph connects parent and child commands by their identifiers."""
        if not self._pid_graph:
            self._pid_graph = self.PidGraph.load_pid_graph()

        return self._pid_graph

    @property
    def pid_by_id(self):
        """Dictionary

        For a given command identifier it can show which command is its parent.
        """
        if not self._pid_by_id:
            self._pid_by_id = self.PidGraph.load_pid_by_id()

        return self._pid_by_id

    @property
    def storage_dir(self):
        """Name of a directory where CC and CL extensions has copied source files."""
        return self._Storage.get_storage_dir()

    def add_file_to_storage(self, file, storage_filename=None):
        """Add file to the storage.

        Args:
            file: Path to the file
            storage_filename: Name by which the file will be stored
        """
        self._Storage.add_file(file, storage_filename=storage_filename)

    def get_storage_path(self, path):
        """Get path to the file or directory from the storage."""
        return self._Storage.get_storage_path(path)

    @property
    def Callgraph(self):
        """Object of "Callgraph" extension."""
        if not self._Callgraph:
            self._Callgraph = Callgraph(self.work_dir, self.conf, self.preset)

        if not self._Callgraph.is_parsed():
            self.parse("Callgraph")

        return self._Callgraph

    @property
    def callgraph(self):
        """Function call graph (C only)."""
        if not self._callgraph:
            self._callgraph = self.Callgraph.load_callgraph()

        return self._callgraph

    def get_callgraph(self, files=None, add_unknown=True):
        """Get function call graph (C only).

        Args:
            files: A list of files to narrow down call graph
            add_unknown: Add functions without known definition
        """
        if isinstance(files, set) or isinstance(files, list):
            files = set(files)

            if add_unknown:
                files.add('unknown')

        return self.Callgraph.load_callgraph(files)

    @property
    def Functions(self):
        """Object of "Functions" extension."""
        if not self._Functions:
            self._Functions = Functions(self.work_dir, self.conf, self.preset)

        if not self._Functions.is_parsed():
            self.parse("Functions")

        return self._Functions

    @property
    def functions(self):
        """Dictionary with definition of C functions."""
        if not self._functions:
            self._functions = self.Functions.load_functions()

        return self._functions

    @property
    def functions_by_file(self):
        """Dictionary with definition of C functions."""
        if not self._functions_by_file:
            self._functions_by_file = self.Functions.load_functions_by_file()

        return self._functions_by_file

    def get_functions_by_file(self, files=None, add_unknown=True):
        """Get definitions of functions (C only).

        Args:
            files: A list of files to narrow down returned dictionary
            add_unknown: Add functions without known definition
        """

        if isinstance(files, set) or isinstance(files, list):
            files = set(files)

            if add_unknown:
                files.add('unknown')

        return self.Functions.load_functions_by_file(files)

    def get_typedefs(self, files=None):
        """Get dictionary with type definitions (C only)."""
        t = Typedefs(self.work_dir, self.conf, self.preset)

        if not t.is_parsed():
            self.parse("Typedefs")

        return t.load_typedefs(files)

    def get_macros_expansions(self, files=None, macros_names=None):
        """Get dictionary with macros expansions (C only).

        Args:
            files: A list of files to narrow down returned dictionary
            macros_names: A list of macros names to find and return
        """
        m = Macros(self.work_dir, self.conf, self.preset)

        if not m.is_parsed():
            self.parse("Macros")

        expansions = m.load_macros_expansions(files)

        if macros_names:
            filtered_expansions = dict()
            for file in expansions:
                for macros in expansions[file]:
                    if macros in macros_names:
                        if file not in filtered_expansions:
                            filtered_expansions[file] = {macros: expansions[file][macros]}
                        else:
                            filtered_expansions[file][macros] = expansions[file][macros]

            return filtered_expansions

        return expansions

    def get_macros_definitions(self, files=None, macros_names=None):
        """Get dictionary with macros definitions (C only).

        Args:
            files: A list of files to narrow down returned dictionary
            macros_names: A list of macros names to find and return
        """
        m = Macros(self.work_dir, self.conf, self.preset)

        if not m.is_parsed():
            self.parse("Macros")

        definitions = m.load_macros_definitions(files)

        if macros_names:
            filtered_definitions = dict()
            for file in definitions:
                for macros in definitions[file]:
                    if macros in macros_names:
                        if file not in filtered_definitions:
                            filtered_definitions[file] = {macros: definitions[file][macros]}
                        else:
                            filtered_definitions[file][macros] = definitions[file][macros]

            return filtered_definitions

        return definitions

    def get_variables(self, files=None):
        """Get dictionary with variables (C only)."""
        v = Variables(self.work_dir, self.conf, self.preset)

        if not v.is_parsed():
            self.parse("Variables")

        return v.load_variables(files)

    def get_used_in_vars_functions(self):
        v = Variables(self.work_dir, self.conf, self.preset)

        if not v.is_parsed():
            self.parse("Variables")

        return v.load_used_in_vars()

    @property
    def CDB(self):
        """Object of "CDB" extension."""
        if not self._CDB:
            self._CDB = CDB(self.work_dir, self.conf, self.preset)

        if not self._CDB.is_parsed():
            self.parse("CDB")

        return self._CDB

    @property
    def compilation_database(self):
        """List of commands that represent compilation database."""
        if not self._cdb:
            self._cdb = self.CDB.load_cdb()

        return self._cdb

    @property
    def Path(self):
        """Object of "Path" extension."""
        if not self._Path:
            self._Path = Path(self.work_dir, self.conf, self.preset)

        return self._Path

    def __normalize_cmd(self, cmd):
        if "cwd" in cmd and "in" in cmd:
            cmd["in"] = [self.Path.get_rel_path(cmd_in, cmd["cwd"]) for cmd_in in cmd["in"]]

        if "cwd" in cmd and "out" in cmd:
            cmd["out"] = [self.Path.get_rel_path(cmd_out, cmd["cwd"]) for cmd_out in cmd["out"]]

        # deps are normalized separately

        if "cwd" in cmd:
            cmd["cwd"] = self.Path.get_abs_path(cmd["cwd"])

        return cmd

    def __normalize_deps(self, deps, cwd):
        return [self.Path.get_rel_path(d, cwd) for d in deps]

    def get_meta(self):
        """Get meta information about Clade working directory"""
        if not self.PidGraph.is_parsed():
            raise RuntimeError("Clade working directory is empty")

        return self.PidGraph.load_global_meta()

    def get_build_dir(self):
        """Get the directory where the build process was performed."""
        return self.get_meta()["build_dir"]

    def get_conf(self):
        """Get the configuration of Clade that was used to create specified working directory."""
        return self.get_meta()["conf"]

    def get_version(self):
        """Get the version of Clade that was used to create specified working directory."""
        return self.get_meta()["clade_version"]

    def get_meta_by_key(self, key):
        """Get meta information by its key"""
        return self.get_meta()[key]

    def get_uuid(self):
        """Get the universally unique identifier (uuid) of the Clade working directory"""
        return self.get_meta()["uuid"]

    def add_meta_by_key(self, key, data):
        """Add new meta information by key"""
        if not self.PidGraph.is_parsed():
            raise RuntimeError("Clade working directory is empty")

        self.PidGraph.add_data_to_global_meta(key, data)


def parse_all_main(args=sys.argv[1:]):
    conf = parse_args(args)

    c = Clade(conf["work_dir"], conf["cmds_file"], conf, conf["preset"])
    c.parse_all()
