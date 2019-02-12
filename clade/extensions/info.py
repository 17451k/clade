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

import codecs
import concurrent.futures
import hashlib
import os
import re
import shutil
import subprocess
import sys

from clade.extensions.abstract import Extension
from clade.extensions.opts import filter_opts
from clade.extensions.utils import common_main


def unwrap(*args, **kwargs):
    return Info._run_cif(*args, **kwargs)


def unwrap_normalize(*args, **kwargs):
    return Info._normilize_file(*args, **kwargs)


class Info(Extension):
    always_requires = ["SrcGraph", "Path", "Storage"]
    requires = always_requires + ["CC", "CL"]

    def __init__(self, work_dir, conf=None, preset="base"):
        if not conf:
            conf = dict()

        # Without this option it will be difficult to link data coming from Info and by CC extensions
        conf["CC.with_system_header_files"] = True

        if "SrcGraph.requires" in conf:
            self.requires = self.always_requires + conf["SrcGraph.requires"]

        super().__init__(work_dir, conf, preset)

        self.aspect = os.path.join(os.path.dirname(__file__), "info", "info.aspect")

        self.execution = os.path.join(self.work_dir, "execution.txt")  # Info about function definitions
        self.call = os.path.join(self.work_dir, "call.txt")  # Info about function calls
        self.decl = os.path.join(self.work_dir, "declare_func.txt")  # Info about function declarations
        self.callp = os.path.join(self.work_dir, "callp.txt")  # Info about function calls via a function pointer
        self.use_func = os.path.join(self.work_dir, "use_func.txt")  # Info about using function names in pointers (in function context only)
        self.use_var = os.path.join(self.work_dir, "use_var.txt")  # Info about using global variables in function context
        self.init_global = os.path.join(self.work_dir, "init_global.txt")  # Info about init values of global variables
        self.define = os.path.join(self.work_dir, "define.txt")  # Info about macro functions
        self.expand = os.path.join(self.work_dir, "expand.txt")  # Info about macros
        self.exported = os.path.join(self.work_dir, "exported.txt")  # Info about exported functions (Linux kernel only)
        self.typedefs = os.path.join(self.work_dir, "typedefs.txt")  # Info about typedefs

        self.files = [self.execution, self.call, self.decl,
                      self.callp, self.use_func, self.use_var,
                      self.init_global, self.define,
                      self.expand, self.exported,
                      self.typedefs]

        self.unsupported_opts_regex = re.compile(r"unrecognized command line option [‘«\"](.*?)[’»\"]")
        self.unsupported_opts_file = os.path.join(self.work_dir, "unsupported_opts.log")
        self.err_log = os.path.join(self.work_dir, "err.log")  # Path to file containing CIF error log

    @Extension.prepare
    def parse(self, cmds_file):
        if not shutil.which("cif"):
            raise RuntimeError("Can't find CIF in PATH")

        self.log("Start CIF")

        cmds = self.extensions["SrcGraph"].load_all_cmds()

        if not cmds:
            raise RuntimeError("There is no parsed CC commands")

        # TODO: remove later
        if os.environ.get("CLADE_DEBUG"):
            for cmd in cmds:
                self._run_cif(cmd)
        else:
            with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as p:
                for cmd in cmds:
                    p.submit(unwrap, self, cmd)

        self.log("CIF finished")

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        if not [file for file in self.files if os.path.exists(file)]:
            raise RuntimeError("Can't find CIF output - it means that CIF most likely failed on every CC command")

        self.__normalize_cif_output(cmds_file)
        if os.path.exists(self.unsupported_opts_file):
            self._normilize_file(self.unsupported_opts_file)
        self.log("Finish")

    def _run_cif(self, cmd):
        if self.__is_cmd_bad_for_cif(cmd):
            return

        for cmd_in in cmd["in"]:
            norm_cmd_in = self.extensions["Path"].get_rel_path(cmd_in, cmd["cwd"])
            cmd_in = self.extensions["Storage"].get_storage_path(norm_cmd_in)

            cif_out = os.path.join(self.temp_dir, str(os.getpid()), cmd_in.lstrip(os.sep) + ".o")
            os.makedirs(os.path.dirname(cif_out), exist_ok=True)
            os.makedirs(self.work_dir, exist_ok=True)

            os.environ["CIF_INFO_DIR"] = self.work_dir
            os.environ["C_FILE"] = norm_cmd_in
            os.environ["CIF_CMD_CWD"] = cmd['cwd']

            cif_args = ["cif",
                        "--debug", "ALL",
                        "--in", cmd_in,
                        "--aspect", self.aspect,
                        "--back-end", "src",
                        "--stage", "instrumentation",
                        "--out", cif_out]

            if not self.conf.get("Compiler.preprocess_cmds"):
                opts = self.extensions[cmd["type"]].load_opts_by_id(cmd["id"])
                opts = filter_opts(opts)

                if opts:
                    cif_args.append("--")
                    opts.extend(self.conf.get("Info.extra_CIF_opts", []))
                    opts = [re.sub(r'\"', r'\\"', opt) for opt in opts]
                    cif_args.extend(opts)

            cwd = self.extensions["Path"].get_abs_path(cmd["cwd"])
            cwd = self.extensions["Storage"].get_storage_path(cwd)
            os.makedirs(cwd, exist_ok=True)

            try:
                self.debug(cif_args)
                subprocess.check_output(cif_args, stderr=subprocess.STDOUT, cwd=cwd, universal_newlines=True)
            except subprocess.CalledProcessError as e:
                self.__save_log(cif_args, e.output)

    def __is_cmd_bad_for_cif(self, cmd):
        if cmd["in"] == []:
            return True

        for cif_in in cmd["in"]:
            if cif_in == "-" or cif_in == "/dev/null":
                return True
            elif re.search(r'\.(s|S)$', cif_in):
                # Assember files are not supported
                return True

        return False

    def __save_log(self, args, log):
        os.makedirs(self.work_dir, exist_ok=True)

        with open(self.err_log, "a") as log_fh:
            log_fh.write(' '.join(args) + "\n\n")
            log_fh.writelines(log)
            log_fh.write("\n\n")

    def _normilize_file(self, file):
        if not os.path.isfile(file):
            return

        regexp = re.compile(r'(\S*) (\S*) (.*)')
        storage = self.extensions["Storage"].get_storage_dir()

        seen = set()
        with codecs.open(file, "r", encoding='utf8', errors='ignore') as fh:
            with open(file + ".temp", "w") as temp_fh:
                for line in fh:
                    # Storing hash of string instead of string itself reduces memory usage by 30-40%
                    h = hashlib.md5(line.encode('utf-8')).hexdigest()
                    if h not in seen:
                        seen.add(h)
                        m = regexp.match(line)

                        if m:
                            cwd, path, rest = m.groups()
                            path = self.extensions["Path"].normalize_rel_path(path, cwd)
                            path = re.sub(storage, "", path)
                            temp_fh.write("{} {}\n".format(path, rest))
                        else:
                            temp_fh.write(line)

        seen.clear()

        os.remove(file)
        os.rename(file + ".temp", file)

        self.extensions["Path"].dump_paths()

    def __normalize_cif_output(self, cmds_file):
        self.log("Normalizing CIF output")

        with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as p:
            for file in [f for f in self.files if f != self.init_global]:
                p.submit(unwrap_normalize, self, file)

        self.log("Normalizing finished")

    def iter_definitions(self):
        return self.__iter_file(self.execution)

    def iter_declarations(self):
        return self.__iter_file(self.decl)

    def iter_exported(self):
        return self.__iter_file(self.exported)

    def iter_calls(self):
        return self.__iter_file(self.call)

    def iter_calls_by_pointers(self):
        return self.__iter_file(self.callp)

    def iter_functions_usages(self):
        return self.__iter_file(self.use_func)

    def iter_macros_definitions(self):
        return self.__iter_file(self.define)

    def iter_macros_expansions(self):
        return self.__iter_file(self.expand)

    def iter_typedefs(self):
        return self.__iter_file(self.typedefs)

    def __iter_file(self, file):
        if not os.path.isfile(file):
            return []

        with open(file, "r") as f:
            for line in f:
                yield line


def main(args=sys.argv[1:]):
    common_main(Info, args)
