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

        self.aspect = os.path.join(
            os.path.dirname(__file__), "info", "info.aspect"
        )

        # Info about function definitions
        self.execution = os.path.join(self.work_dir, "execution.txt")
        # Info about function calls
        self.call = os.path.join(self.work_dir, "call.txt")
        # Info about function declarations
        self.decl = os.path.join(self.work_dir, "declare_func.txt")
        # Info about function calls via a function pointer
        self.callp = os.path.join(self.work_dir, "callp.txt")
        # Info about using function names in pointers (in function context only)
        self.use_func = os.path.join(self.work_dir, "use_func.txt")
        # Info about using global variables in function context
        self.use_var = os.path.join(self.work_dir, "use_var.txt")
        # Info about init values of global variables
        self.init_global = os.path.join(self.work_dir, "init_global.txt")
        # Info about macro functions
        self.define = os.path.join(self.work_dir, "define.txt")
        # Info about macros
        self.expand = os.path.join(self.work_dir, "expand.txt")
        # Info about exported functions (Linux kernel only)
        self.exported = os.path.join(self.work_dir, "exported.txt")
        # Info about typedefs
        self.typedefs = os.path.join(self.work_dir, "typedefs.txt")

        self.files = [
            self.execution,
            self.call,
            self.decl,
            self.callp,
            self.use_func,
            self.use_var,
            self.init_global,
            self.define,
            self.expand,
            self.exported,
            self.typedefs,
        ]

        # Path to files containing CIF log
        self.cif_log = os.path.join(self.work_dir, "cif.log")
        self.err_log = os.path.join(self.work_dir, "err.log")

    @Extension.prepare
    def parse(self, cmds_file):
        if not shutil.which(self.conf.get("Info.cif", "cif")):
            raise RuntimeError("Can't find CIF in PATH")

        self.log("Start CIF")

        cmds = self.extensions["SrcGraph"].load_all_cmds()

        if not cmds:
            raise RuntimeError("There are no parsed compiler commands")

        self.parse_cmds_in_parallel(cmds, Info._run_cif)

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        if not os.path.exists(self.cif_log):
            raise RuntimeError(
                "Something is wrong with every compilation command"
            )
        elif not [file for file in self.files if os.path.exists(file)]:
            raise RuntimeError(
                "CIF failed on every command. Log: {}".format(self.err_log)
            )

        if not os.path.exists(self.err_log):
            self.log("CIF finished without errors")
        else:
            self.log("CIF finished with errors. Log: {}".format(self.err_log))

        self.__normalize_cif_output(cmds_file)

    def _run_cif(self, cmd):
        if self.__is_cmd_bad_for_cif(cmd):
            return

        tmp_dir = os.path.join(self.temp_dir, str(os.getpid()))
        os.makedirs(tmp_dir, exist_ok=True)

        # If True then  CIF will be executed on preprocessed .i file
        use_pre = self.conf.get("Compiler.preprocess_cmds") and self.conf.get(
            "Info.use_preprocessed_files"
        )

        for cmd_in in cmd["in"]:
            norm_cmd_in = self.extensions["Path"].get_rel_path(
                cmd_in, cmd["cwd"]
            )

            cmd_in = self.extensions["Storage"].get_storage_path(norm_cmd_in)

            if use_pre:
                cif_in = self.extensions[cmd["type"]].get_pre_file_by_path(
                    norm_cmd_in, cmd["cwd"]
                )
            else:
                cif_in = cmd_in

            if not os.path.exists(cif_in):
                continue

            cif_out = os.path.join(
                tmp_dir, os.path.basename(cmd_in.lstrip(os.sep)) + ".o"
            )

            os.makedirs(self.work_dir, exist_ok=True)

            os.environ["CIF_INFO_DIR"] = self.work_dir
            os.environ["C_FILE"] = norm_cmd_in
            os.environ["CIF_CMD_CWD"] = cmd["cwd"]

            cif_args = [
                self.conf.get("Info.cif", "cif"),
                "--debug", "ALL",
                "--in", cif_in,
                "--aspect", self.aspect,
                "--back-end", "src",
                "--stage", "instrumentation",
                "--out", cif_out
            ]

            if self.conf.get("Info.aspectator"):
                cif_args.extend(
                    ["--aspectator", self.conf.get("Info.aspectator")]
                )

            if use_pre:
                opts = []
            else:
                opts = self.extensions[cmd["type"]].load_opts_by_id(cmd["id"])
                opts = filter_opts(
                    opts, self.extensions["Storage"].get_storage_path
                )

            opts.extend(self.conf.get("Info.extra_CIF_opts", []))
            opts = [re.sub(r"\"", r'\\"', opt) for opt in opts]

            if opts:
                cif_args.append("--")
                cif_args.extend(opts)

            cwd = self.extensions["Path"].get_abs_path(cmd["cwd"])
            cwd = self.extensions["Storage"].get_storage_path(cwd)
            os.makedirs(cwd, exist_ok=True)

            try:
                self.debug(cif_args)
                output = subprocess.check_output(
                    cif_args,
                    stderr=subprocess.STDOUT,
                    cwd=cwd,
                    universal_newlines=True,
                )
                self.__save_log(cif_args, output, self.cif_log)
            except subprocess.CalledProcessError as e:
                self.__save_log(cif_args, e.output, self.err_log)
                self.__save_log(cif_args, e.output, self.cif_log)
                return

    def __is_cmd_bad_for_cif(self, cmd):
        if cmd["in"] == []:
            return True

        for cif_in in cmd["in"]:
            if cif_in == "-" or cif_in == "/dev/null":
                return True
            elif re.search(r"\.(s|S)$", cif_in):
                # Assember files are not supported
                return True

        return False

    def __save_log(self, args, log, file):
        os.makedirs(self.work_dir, exist_ok=True)

        with open(file, "a") as log_fh:
            log_fh.write(" ".join(args) + "\n\n")
            log_fh.writelines(log)
            log_fh.write("\n\n")

    def _normilize_file(self, file):
        if not os.path.isfile(file):
            return

        regexp = re.compile(r"\"(.*?)\" \"(.*?)\" (.*)")
        storage = self.extensions["Storage"].get_storage_dir()

        seen = set()
        with codecs.open(file, "r", encoding="utf8", errors="ignore") as fh:
            with open(file + ".temp", "w") as temp_fh:
                for line in fh:
                    # Storing hash of string instead of string itself reduces memory usage by 30-40%
                    h = hashlib.md5(line.encode("utf-8")).hexdigest()
                    if h not in seen:
                        seen.add(h)
                        m = regexp.match(line)

                        if m:
                            cwd, path, rest = m.groups()

                            path = self.extensions["Path"].normalize_rel_path(
                                path, cwd
                            )

                            if "\\/" in path:
                                self.warning(
                                    "Normalized path looks weird: {!r}".format(
                                        path
                                    )
                                )

                            path = path.replace(storage, "")
                            temp_fh.write('"{}" {}\n'.format(path, rest))
                        else:
                            temp_fh.write(line)

        seen.clear()

        os.remove(file)
        os.rename(file + ".temp", file)

        self.extensions["Path"].dump_paths()

    def __normalize_cif_output(self, cmds_file):
        self.log("Normalizing CIF output")

        with concurrent.futures.ProcessPoolExecutor(
            max_workers=os.cpu_count()
        ) as p:
            for file in [f for f in self.files if f != self.init_global]:
                p.submit(Info._normilize_file, self, file)

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
