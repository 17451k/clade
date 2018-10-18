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
from clade.extensions.opts import cif_unsupported_opts, filter_opts
from clade.extensions.utils import common_main, normalize_path


def unwrap(*args, **kwargs):
    return Info._run_cif(*args, **kwargs)


def unwrap_normalize(*args, **kwargs):
    return Info._normilize_file(*args, **kwargs)


class Info(Extension):
    requires = ["CC"]

    def __init__(self, work_dir, conf=None, preset="base"):
        if not conf:
            conf = dict()

        # Without this option it will be difficult to link data coming from Info and by CC extensions
        conf["CC.with_system_header_files"] = True

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

        cmds = self.extensions["CC"].load_all_cmds(compile_only=True)

        if not cmds:
            raise RuntimeError("There is no parsed CC commands")

        with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as p:
            for cmd in cmds:
                p.submit(unwrap, self, cmd, cmds_file)

        self.log("CIF finished")

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        if not [file for file in self.files if os.path.exists(file)]:
            shutil.rmtree(self.work_dir)
            raise RuntimeError("Can't find CIF output - it means that CIF most likely failed on every CC command")

        self.__normalize_cif_output(cmds_file)
        if os.path.exists(self.unsupported_opts_file):
            self._normilize_file(self.unsupported_opts_file)
        self.log("Finish")

    def _run_cif(self, cmd, cmds_file, opts_to_filter=None):
        if self.__is_cmd_bad_for_cif(cmd):
            return

        if not opts_to_filter:
            opts_to_filter = []

        src = self.get_build_cwd(cmds_file)

        for cmd_in in cmd["in"]:
            cif_out = os.path.join(self.temp_dir, str(os.getpid()), cmd_in.lstrip(os.sep) + ".o")
            os.makedirs(os.path.dirname(cif_out), exist_ok=True)
            os.makedirs(self.work_dir, exist_ok=True)

            var_c_file = cmd_in
            var_c_file = normalize_path(var_c_file, cmd["cwd"], src)

            os.environ["CIF_INFO_DIR"] = self.work_dir
            os.environ["VAR_C_FILE"] = var_c_file
            os.environ["C_FILE"] = cmd_in
            os.environ["CIF_CMD_CWD"] = cmd['cwd']

            cif_args = ["cif",
                        "--debug", "ALL",
                        "--in", cmd_in,
                        "--aspect", self.aspect,
                        "--back-end", "src",
                        "--stage", "instrumentation",
                        "--out", cif_out]

            cif_args.append("--")

            opts = self.extensions["CC"].load_opts_by_id(cmd["id"])
            opts.extend(self.conf.get("Info.extra CIF opts", []))
            opts = [re.sub(r'\"', r'\\"', opt) for opt in opts]
            cif_args.extend(filter_opts(opts, cif_unsupported_opts[:] + opts_to_filter[:]))

            try:
                subprocess.check_output(cif_args, stderr=subprocess.STDOUT, cwd=cmd["cwd"], universal_newlines=True)
            except subprocess.CalledProcessError as e:
                # CIF may fail if it does not support some options
                # We can try to parse stdout to identify unsupported options and relaunch CIF without it
                m = self.unsupported_opts_regex.findall(e.output)
                if m and not opts_to_filter:
                    self.__save_unsupported_opts(m)
                    self._run_cif(cmd, cmds_file, m)
                else:
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

    def __save_unsupported_opts(self, opts):
        with open(self.unsupported_opts_file, "a") as f:
            for opt in opts:
                f.write("{}\n".format(opt))

    def __save_log(self, args, log):
        with open(self.err_log, "a") as log_fh:
            log_fh.write(' '.join(args) + "\n\n")
            log_fh.writelines(log)
            log_fh.write("\n\n")

    def _normilize_file(self, file, src=""):
        if not os.path.isfile(file):
            return

        regexp = re.compile(r'(\S*) (\S*) (.*)')

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
                            path = normalize_path(path, cwd, src)
                            temp_fh.write("{} {}\n".format(path, rest))
                        else:
                            temp_fh.write(line)

        os.remove(file)
        os.rename(file + ".temp", file)

    def __normalize_cif_output(self, cmds_file):
        self.log("Normalizing CIF output")

        src = self.get_build_cwd(cmds_file)

        with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as p:
            for file in [f for f in self.files if f != self.init_global]:
                p.submit(unwrap_normalize, self, file, src)

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
