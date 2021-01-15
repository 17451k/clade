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

import ujson
import os
import shutil

from clade.utils import get_logger, merge_preset_to_conf
from clade.intercept import intercept
from clade.extensions.abstract import Extension
from clade.types.nested_dict import nested_dict, traverse


class Clade:
    """Interface to all functionality available in Clade.

    Args:
        work_dir: A path to the working directory where all output files will be stored
        cmds_file: A path to the file where intercepted commands are or will be saved
        conf: A dictionary with optional arguments
        preset: Name of one of the available preset configurations

    Raises:
        RuntimeError: You did something wrong
        PermissionError: You do not have permissions to create or access working directory

    TODO:
        Check that command was already intercepted
        Check that intercept() argument is list, not string
    """

    def __init__(self, work_dir="clade", cmds_file=None, conf=None, preset="base"):
        self.work_dir = os.path.abspath(str(work_dir))

        if not cmds_file:
            self.cmds_file = os.path.join(self.work_dir, "cmds.txt")
        else:
            self.cmds_file = os.path.abspath(cmds_file)

        self.conf = conf if conf else dict()
        self.conf = merge_preset_to_conf(preset, self.conf)
        self.conf_file = os.path.join(self.work_dir, "conf.json")

        # "Name -> Object" storage of all available extensions
        self.extensions = dict()

        self.__prepare_to_init()

        # logger needs working directory, so it must be created after cleaning
        self.logger = get_logger("clade-api", with_name=False, conf=self.conf)

        self._cmd_graph = None
        self._cmd_type = None
        self._src_graph = None
        self._src_info = None
        self._pid_graph = None
        self._pid_by_id = None
        self._callgraph = None
        self._functions = None
        self._functions_by_file = None
        self._cdb = None

    def __prepare_to_init(self):
        # Clean working directory
        if self.conf.get("force") and os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

        # Check that Clade has permission to read the working directory (if it exists)
        if os.path.exists(self.work_dir):
            if not os.access(self.work_dir, os.R_OK):
                self.logger.error("Permission error: can't read files from the working directory")
                raise PermissionError

    def __check_write_to_parent_dir(self, path):
        # dirname can be empty if cmds_file is located in the current directory
        parent_path = os.path.dirname(path)

        if not parent_path:
            parent_path = os.getcwd()

        self.__check_write_to_dir(parent_path)

    def __check_write_to_dir(self, path):
        if path and os.path.exists(path):
            if not os.access(path, os.X_OK | os.W_OK):
                self.logger.error("Permission error: can't write files to the {!r} directory".format(path))
                raise PermissionError

    def __prepare_to_intercept(self):
        # Check that Clade has permission to create the cmds.txt file
        self.__check_write_to_parent_dir(self.cmds_file)

        # Create path to the cmds.txt file
        cmds_file_dirname = os.path.dirname(self.cmds_file)

        if not cmds_file_dirname:
            cmds_file_dirname = os.getcwd()

        os.makedirs(cmds_file_dirname, exist_ok=True)

    def __dump_conf(self):
        # Overwrite this file each time
        with open(self.conf_file, "w") as fh:
            ujson.dump(
                self.conf,
                fh,
                sort_keys=True,
                indent=4,
                ensure_ascii=False,
                escape_forward_slashes=False,
            )

    def __prepare_to_parse(self):
        self.__check_write_to_parent_dir(self.work_dir)

        os.makedirs(self.work_dir, exist_ok=True)

        self.__dump_conf()

    def intercept(self, command, cwd=os.getcwd(), append=False, use_wrappers=False, intercept_open=False):
        """Execute intercepting of build commands.

        Args:
            command: A list of strings representing build command to run and intercept
            cwd: A path to the directory where build command will be executed
            append: A boolean allowing to append intercepted commands to already existing file with commands
            use_wrappers: A boolean enabling intercepting mode based on wrappers

        Returns:
            0 if everything went successful and error code otherwise
        """

        self.__prepare_to_intercept()

        return intercept(
            command=command,
            cwd=cwd,
            output=self.cmds_file,
            append=append,
            use_wrappers=use_wrappers,
            intercept_open=intercept_open,
            conf=self.conf
        )

    def __get_ext_obj(self, ext_name):
        """Return object of specified extension."""

        if ext_name in self.extensions:
            return self.extensions[ext_name]

        ext_objs = self.__get_ext_obj_list([ext_name])

        for e in ext_objs:
            if e.name == ext_name:
                return e
        else:
            raise RuntimeError("Cant find required extension {!r}".format(ext_name))

    def are_parsed(self, ext_name):
        """Check whether build commands are parsed or not.

        Args:
            ext_name: An extension name, like "Callgraph"

        Returns:
            True if specified extension already parsed build commands and False otherwise
        """

        e = self.__get_ext_obj(ext_name)
        return e.is_parsed()

    def parse(self, ext_name, clean=False):
        """Execute parse() method of a specified Clade extension.

        Args:
            ext_name: An extension name, like "Callgraph"
            clean: Clean working directory of specified extension before parsing

        Returns:
            An extension object
        """

        return self.parse_list([ext_name], clean=clean)[0]

    def parse_list(self, ext_names, clean=False):
        """Execute parse() method of several Clade extensions.

        Args:
            ext_names: List of extension names, like ["Callgraph", "SrcGraph"]
            clean: Clean working directory of specified extensions before parsing

        Returns:
            List of extension objects
        """

        self.__prepare_to_parse()

        # Get list of extension objects to parse, including implicitly required ones
        ext_objs = self.__get_ext_obj_list(ext_names)

        for ext_obj in ext_objs:
            ext_obj.debug("Extension requirements: {!r}".format(ext_obj.requires))

            if clean and ext_obj.name in ext_names and os.path.isdir(ext_obj.work_dir):
                shutil.rmtree(ext_obj.work_dir)

            # Check that working directory is not corrupted
            ext_obj.check_corrupted()

            # Check that working directory was creating with the extension of correct version
            ext_obj.check_ext_version()

            if ext_obj.is_parsed():
                ext_obj.check_conf_consistency()
            else:
                ext_obj.parse(self.cmds_file)

        return [e for e in ext_objs if e.name in ext_names]

    def __get_ext_obj_list(self, ext_names):
        """Return correctly initialised list of extension objects
        for the given list of extension names.

        List includes extensions that are required implicitly.
        """
        ext_objs = []

        for ext_name in ext_names:
            already_initialized = [x.name for x in ext_objs]
            ext_objs.extend(self.__create_ext_obj_list(ext_name, already_initialized))

        for ext_obj in [e for e in ext_objs if e.name not in self.extensions]:
            # Correctly initialise .extensions variable for each extension object,
            # without creating additional objects
            ext_obj.extensions = self.__map_ext_names(ext_obj, ext_objs)
            # Store extension object for future use
            self.extensions[ext_obj.name] = ext_obj

        return ext_objs

    def __create_ext_obj_list(self, ext_name, already_initialized=None):
        """Return list of extension objects for the given list of extension names.

        List can be filtered using already_initialized argument.
        """

        if not already_initialized:
            already_initialized = []

        if ext_name in already_initialized:
            return []

        e = self.__create_ext_obj(ext_name)

        ext_objs = []

        for req_name in e.requires:
            already_initialized += [x.name for x in ext_objs]
            r_ext_objs = self.__create_ext_obj_list(req_name, already_initialized)
            ext_objs.extend(r_ext_objs)

        ext_objs.append(e)

        return ext_objs

    def __map_ext_names(self, ext_obj, ext_objs):
        """Return dictionary of extension objects that a given extension requires."""
        return {e.name: e for e in ext_objs if e.name in ext_obj.requires}

    def __create_ext_obj(self, ext_name):
        """Create or return extension object of a given name."""
        if ext_name in self.extensions:
            return self.extensions[ext_name]

        try:
            ext_class = Extension.find_subclass(ext_name)
        except NotImplementedError:
            Extension._import_extension_modules()
            ext_class = Extension.find_subclass(ext_name)
        return ext_class(self.work_dir, conf=self.conf)

    @property
    def CmdGraph(self):
        """Object of "CmdGraph" extension."""
        return self.__get_ext_obj("CmdGraph")

    @property
    def cmd_graph(self):
        """Command graph connects commands by their input and output files."""
        if not self._cmd_graph:
            self._cmd_graph = self.CmdGraph.load_cmd_graph()

        return self._cmd_graph

    @property
    def cmd_type(self):
        """Information about command types."""
        if not self._cmd_type:
            self._cmd_type = self.CmdGraph.load_cmd_type()

        return self._cmd_type

    @property
    def cmd_ids(self):
        """List of identifiers of all parsed commands."""
        return self.cmd_graph.keys()

    @property
    def cmds(self):
        """List of all parsed commands."""
        return self.CmdGraph.load_all_cmds()

    def get_cmds(self, with_opts=False, with_raw=False):
        """Get list with all parsed commands."""
        return self.CmdGraph.load_all_cmds(with_opts=with_opts, with_raw=with_raw)

    @property
    def compilation_cmds(self):
        """List of all parsed compilation commands (C projects only)."""
        return self.SrcGraph.load_all_cmds()

    def get_compilation_cmds(self, with_opts=False, with_raw=False, with_deps=False):
        """Get list with all parsed compilation commands (C projects only)."""
        return self.SrcGraph.load_all_cmds(
            with_opts=with_opts, with_raw=with_raw, with_deps=with_deps)

    def get_cmd_type(self, cmd_id):
        """Get type of a command by its identifier."""
        return self.cmd_type[cmd_id]

    def get_cmd(self, cmd_id, cmd_type=None, with_opts=False, with_raw=False, with_deps=False):
        """Get command by its identifier and type (optionally)."""

        if not cmd_type:
            cmd_type = self.get_cmd_type(cmd_id)

        if with_deps and cmd_type not in ["CC", "CL"]:
            raise RuntimeError("Only compiler commands have dependencies")

        ext_obj = self.CmdGraph.get_ext_obj(cmd_type)
        cmd = ext_obj.load_cmd_by_id(cmd_id)

        if with_opts:
            cmd["opts"] = self.get_cmd_opts(cmd_id, cmd_type=cmd_type)

        if with_raw:
            cmd["command"] = self.get_cmd_raw(cmd_id, cmd_type=cmd_type)

        if with_deps:
            cmd["deps"] = self.get_cmd_deps(cmd_id, cmd_type=cmd_type)

        return cmd

    def get_cmd_opts(self, cmd_id, cmd_type=None):
        """Get list of options of a command by its identifier and type (optionally)."""
        if not cmd_type:
            cmd_type = self.get_cmd_type(cmd_id)

        ext_obj = self.CmdGraph.get_ext_obj(cmd_type)

        return ext_obj.load_opts_by_id(cmd_id)

    def get_cmd_raw(self, cmd_id, cmd_type=None):
        """Get raw intercepted command by its identifier and type (optionally)."""
        if not cmd_type:
            cmd_type = self.get_cmd_type(cmd_id)

        ext_obj = self.CmdGraph.get_ext_obj(cmd_type)

        return ext_obj.load_raw_by_id(cmd_id)

    def get_cmd_deps(self, cmd_id, cmd_type=None):
        """Get list of dependencies of a compiler command by its identifier and type (optionally)."""
        if not cmd_type:
            cmd_type = self.get_cmd_type(cmd_id)

        if cmd_type not in ["CC", "CL"]:
            raise RuntimeError("Only compiler commands have dependencies")

        cc_obj = self.CmdGraph.get_ext_obj(cmd_type)

        return cc_obj.load_deps_by_id(cmd_id)

    def get_all_cmds_by_type(self, cmd_type):
        """Get list of all parsed commands filtered by their type."""
        return self.CmdGraph.load_all_cmds_by_type(cmd_type)

    def get_root_cmds(self, cmd_id):
        """Get list of identifiers of all root commands from a command graph of a given command identifier."""
        if cmd_id not in self.cmd_graph:
            raise KeyError("Can't find {!r} id in the command graph".format(cmd_id))

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
            raise KeyError("Can't find {!r} id in the command graph".format(cmd_id))

        used_by = self.cmd_graph[cmd_id]["used_by"]

        indirect_used_by = []
        for used_by_id in used_by:
            indirect_used_by.extend(self.get_leaf_cmds(used_by_id))

        used_by.extend(indirect_used_by)
        return used_by

    @property
    def SrcGraph(self):
        """Object of "SrcGraph" extension."""
        return self.__get_ext_obj("SrcGraph")

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
        return (cmd_id for cmd_id in self.SrcGraph.load_src_graph([file])[file]["compiled_in"])

    def get_compilation_cmds_by_file(self, file):
        """Get list of compilation commands in which the file was compiled.

        Args:
            file: A name of the source file from the source graph
        """
        return (self.get_cmd(cmd_id) for cmd_id in self.get_compilation_cmds_ids_by_file(file))

    @property
    def PidGraph(self):
        """Object of "PidGraph" extension."""
        return self.__get_ext_obj("PidGraph")

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
    def Storage(self):
        """Object of "Storage" extension."""
        return self.__get_ext_obj("Storage")

    @property
    def storage_dir(self):
        """Name of a directory where CC and CL extensions has copied source files."""
        return self.Storage.get_storage_dir()

    def add_file_to_storage(self, file, storage_filename=None, encoding=None):
        """Add file to the storage.

        Args:
            file: Path to the file
            storage_filename: Name by which the file will be stored
            encoding: encoding of the file, which may be required if you want
                      to convert it to UTF-8 using 'Storage.convert_to_utf8'
                      option
        """

        return self.Storage.add_file(file, storage_filename=storage_filename, encoding=encoding)

    def get_storage_path(self, path):
        """Get path to the file or directory from the storage."""
        return self.Storage.get_storage_path(path)

    @property
    def Callgraph(self):
        """Object of "Callgraph" extension."""
        return self.__get_ext_obj("Callgraph")

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
                files.add("unknown")

        return self.Callgraph.load_callgraph(files)

    @property
    def Functions(self):
        """Object of "Functions" extension."""
        return self.__get_ext_obj("Functions")

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
                files.add("unknown")

        return self.Functions.load_functions_by_file(files)

    def get_typedefs(self, files=None):
        """Get dictionary with type definitions (C only)."""
        t = self.__get_ext_obj("Typedefs")

        return t.load_typedefs(files)

    @property
    def Macros(self):
        """Object of "Macros" extension."""
        return self.__get_ext_obj("Macros")

    def get_macros_expansions(self, files=None, macros_names=None):
        """Get dictionary with macros expansions (C only).

        DEPRECATED: use get_expansions() instead.

        Args:
            files: A list of files to narrow down returned dictionary
            macros_names: A list of macros names to find and return
        """

        exps = self.Macros.load_expansions(files)
        expansions = nested_dict()

        # Map new format of macros to the old one
        for exp_file, macro, _, _, _, args in traverse(exps, 6):
            if expansions[exp_file][macro]["args"]:
                expansions[exp_file][macro]["args"].extend(args)
            else:
                expansions[exp_file][macro]["args"] = args

        if macros_names:
            filtered_expansions = nested_dict()

            for file, macros in traverse(expansions, 2):
                if macros in macros_names:
                    filtered_expansions[file][macros] = expansions[file][macros]

            return filtered_expansions

        return expansions

    def get_macros_definitions(self, files=None, macros_names=None):
        """Get dictionary with macros definitions (C only).

        DEPRECATED: use get_macros() instead.

        Args:
            files: A list of files to narrow down returned dictionary
            macros_names: A list of macros names to find and return
        """

        macros = self.Macros.load_macros(files)

        definitions = nested_dict()

        # Map new format of macros to the old one
        for file, macro, line in traverse(macros, 3):
            if definitions[file][macro]:
                definitions[file][macro].append(line)
            else:
                definitions[file][macro] = [line]

        # Filter macro definitions by names
        if macros_names:
            filtered_definitions = nested_dict()

            for file, macros in traverse(definitions, 2):
                if macros in macros_names:
                    filtered_definitions[file][macros] = definitions[file][macros]

            return filtered_definitions

        return definitions

    def get_macros(self, files=None):
        """Get all information about macros."""

        return self.Macros.load_macros(files)

    def get_expansions(self, files):
        """Get information about macro expansions"""

        return self.Macros.load_expansions(files)

    @property
    def Variables(self):
        """Object of "Variables" extension."""
        return self.__get_ext_obj("Variables")

    def get_variables(self, files=None):
        """Get dictionary with variables (C only)."""
        return self.Variables.load_variables(files)

    def get_used_in_vars_functions(self):
        return self.Variables.load_used_in_vars()

    @property
    def CDB(self):
        """Object of "CDB" extension."""
        return self.__get_ext_obj("CDB")

    @property
    def compilation_database(self):
        """List of commands that represent compilation database."""
        if not self._cdb:
            self._cdb = self.CDB.load_cdb()

        return self._cdb

    @property
    def Path(self):
        """Object of "Path" extension."""
        return self.__get_ext_obj("Path")

    def get_meta(self):
        """Get meta information about Clade working directory"""
        if not self.are_parsed("PidGraph"):
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
        meta = self.get_meta()

        if "versions" in meta:
            return meta["versions"]["clade"]
        else:
            return meta.get("clade_version", "unknown")

    def get_meta_by_key(self, key):
        """Get meta information by its key"""
        return self.get_meta()[key]

    def get_uuid(self):
        """Get the universally unique identifier (uuid) of the Clade working directory"""
        return self.get_meta()["uuid"]

    def add_meta_by_key(self, key, data):
        """Add new meta information by key"""
        if not self.are_parsed("PidGraph"):
            raise RuntimeError("Clade working directory is empty")

        self.PidGraph.add_data_to_global_meta(key, data)

    def work_dir_ok(self, log=False):
        """Check that Clade working directory exists and not corrupted.

        Returns:
            True if everything is OK and False otherwise
        """

        p = self.__get_ext_obj("PidGraph")

        if not os.path.exists(self.work_dir) or not p.is_parsed():
            if log:
                self.logger.error("Working directory does not exist")
            return False

        ext_names = [f for f in os.listdir(self.work_dir) if os.path.isdir(os.path.join(self.work_dir, f))]
        ext_objs = [ext_obj for ext_obj in self.__get_ext_obj_list(ext_names) if ext_obj.name in ext_names]

        if ext_objs:
            if not ext_objs[0].load_global_meta():
                if log:
                    self.logger.error("Working directory does not contain file with global meta information")
                return False

        for ext_obj in ext_objs:
            try:
                ext_obj.check_corrupted()
            except RuntimeError:
                return False

            try:
                ext_obj.check_ext_version()
            except RuntimeError:
                return False

        if log:
            self.logger.info(
                "Working directory is OK and contains data from the following extensions: {}".format(", ".join(ext_names))
            )
        return True

    @property
    def CrossRef(self):
        """Object of "CrossRef" extension."""
        return self.__get_ext_obj("CrossRef")

    def get_ref_to(self, files=None):
        """Dictionary with references to definitions and declarations.

        Args:
            files: A list of files to narrow down data
            add_unknown: Add functions without known definition
        """
        if isinstance(files, set) or isinstance(files, list):
            files = set(files)

        return self.CrossRef.load_ref_to_by_file(files)

    def get_ref_from(self, files=None):
        """Dictionary with references to usages.

        Args:
            files: A list of files to narrow down data
        """
        if isinstance(files, set) or isinstance(files, list):
            files = set(files)

        return self.CrossRef.load_ref_from_by_file(files)
