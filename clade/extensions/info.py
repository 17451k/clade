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
import fnmatch
import gc
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

from clade.extensions.abstract import Extension
from clade.extensions.opts import filter_opts


class Info(Extension):
    always_requires = ["SrcGraph", "Path", "Storage"]
    requires = always_requires + ["CC", "CL"]

    __version__ = "2"

    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        # Without this option it will be difficult to link data coming from Info and by CC extensions
        conf["CC.with_system_header_files"] = True

        if "SrcGraph.requires" in conf:
            self.requires = self.always_requires + conf["SrcGraph.requires"]

        super().__init__(work_dir, conf)

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

        # Path to cif output
        self.cif_output_dir = os.path.join(self.work_dir, "output")

        # Path to files containing CIF log
        self.cif_log = os.path.join(self.work_dir, "cif.log")
        self.err_log = os.path.join(self.work_dir, "err.log")

        self.expand_regex = re.compile(r'\"(.*?)\"(.*)')

    @Extension.prepare
    def parse(self, cmds_file):
        if not shutil.which(self.conf.get("Info.cif", "cif")):
            raise RuntimeError("Can't find CIF in PATH")

        # Check that CIF was not added in PATH via relative path
        current_dir = os.getcwd()
        os.chdir(self.temp_dir)
        if not shutil.which(self.conf.get("Info.cif", "cif")):
            raise RuntimeError("Path to CIF must be absolute")
        os.chdir(current_dir)

        cmds = list(self.extensions["SrcGraph"].load_all_cmds())

        if not cmds:
            raise RuntimeError("There are no parsed compiler commands")

        self.parse_cmds_in_parallel(cmds, Info._run_cif)

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        if not os.path.exists(self.cif_log):
            raise RuntimeError(
                "Something is wrong with every compilation command"
            )

        cif_output = self.__find_cif_output()

        if not cif_output and os.path.exists(self.err_log):
            raise RuntimeError(
                "CIF failed on every command. Log: {}".format(self.err_log)
            )

        if not os.path.exists(self.err_log):
            self.log("CIF finished without errors")
        else:
            self.log("CIF finished with errors. Log: {}".format(self.err_log))

        self.__normalize_cif_output(cif_output)

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

            cif_env = dict()
            cif_env["CIF_INFO_DIR"] = self.cif_output_dir
            cif_env["C_FILE"] = norm_cmd_in

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
                    env=os.environ.update(cif_env)
                )
                self.__save_log(cmd["id"], cwd, cif_args, cif_env, output, self.cif_log)
            except subprocess.CalledProcessError as e:
                self.__save_log(cmd["id"], cwd, cif_args, cif_env, e.output, self.err_log)
                self.__save_log(cmd["id"], cwd, cif_args, cif_env, e.output, self.cif_log)
                return

        # Force garbage collector to work
        gc.collect()

    def __is_cmd_bad_for_cif(self, cmd):
        if not cmd["in"]:
            return True

        for cif_in in cmd["in"]:
            if cif_in == "-" or cif_in == "/dev/null":
                return True
            elif re.search(r"\.[sS]$", cif_in):
                # Assembler files are not supported
                return True

        return False

    def __save_log(self, cmd_id, cwd, args, env, log, file):
        os.makedirs(self.work_dir, exist_ok=True)

        with open(file, "a") as log_fh:
            log_fh.write("COMMAND_ID: {}\n".format(cmd_id))
            log_fh.write("CWD: {}\n".format(cwd))

            log_fh.write("CIF ARGS:")
            for key in env:
                log_fh.write(" {}={}".format(key, shlex.quote(env[key])))

            for arg in args:
                log_fh.write(" {}".format(shlex.quote(arg)))
            log_fh.write("\n\n")

            log_fh.writelines(log)
            log_fh.write("\n\n")

    def __find_cif_output(self):
        cif_output = []

        for root, _, filenames in os.walk(self.work_dir):
            for filename in fnmatch.filter(filenames, "*.txt"):
                cif_output.append(os.path.join(root, filename))

        return cif_output

    def __normalize_cif_output(self, cif_output):
        self.log("Normalizing CIF output")

        if self.conf.get("cpu_count"):
            max_workers = self.conf.get("cpu_count", os.cpu_count())
        else:
            max_workers = os.cpu_count()

        # Normalize all small cif output files
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as p:
            futures = []
            finished_files = 0

            init_global = os.path.basename(self.init_global)
            files = [f for f in cif_output if not f.endswith(init_global)]
            total_files = len(files)

            storage = self.extensions["Storage"].get_storage_dir()
            expand = os.path.basename(self.expand)

            for file in files:
                f = p.submit(normalize_file, file, storage, self.cif_output_dir, expand)
                futures.append(f)

            while True:
                if not futures:
                    break

                done_futures = [x for x in futures if x.done()]

                # Remove all futures that are already completed
                # to reduce memory usage
                futures = [x for x in futures if not x.done()]

                # Track progress (only if stdout is not redirected)
                if total_files and sys.stdout.isatty() and self.conf["log_level"] in ["INFO", "DEBUG"]:
                    finished_files += len(done_futures)

                    msg = "\t [{:.0f}%] {} of {} files are normalized".format(
                        finished_files / total_files * 100,
                        finished_files,
                        total_files,
                    )
                    print(msg, end="\r")

                # Check return value of all finished futures
                for f in done_futures:
                    try:
                        f.result()
                    except Exception as e:
                        self.error(
                            "Something happened in the child process: {}".format(
                                e
                            )
                        )

                        raise RuntimeError

                # Save a little bit of CPU time
                time.sleep(0.1)

        if total_files and sys.stdout.isatty() and self.conf["log_level"] in ["INFO", "DEBUG"]:
            print(" " * 79, end="\r")

        # Join all cif output file into several big .txt files
        for file in self.files:
            output_type = os.path.basename(file)

            for output_file in [f for f in cif_output if f.endswith(output_type)]:
                with open(file, "a") as file_fh:
                    with open(output_file, "r") as output_fh:
                        # This files should be fairly small
                        file_fh.write(output_fh.read())

        # Remove cif output directory
        shutil.rmtree(self.cif_output_dir)

        self.log("Normalizing finished")

    def iter_definitions(self):
        """Yield src_file, func, def_line, func_type, signature"""

        regex = re.compile(r"\"(.*?)\" (\S*) (\S*) (\S*) ([^']*)\n")

        for content in self.__iter_file_regex(self.execution, regex):
            yield content

    def iter_declarations(self):
        """Yield decl_file, decl_name, decl_line, decl_type, decl_signature"""

        regex = re.compile(r"\"(.*?)\" (\S*) (\S*) (\S*) ([^']*)\n")

        for content in self.__iter_file_regex(self.decl, regex):
            yield content

    def iter_exported(self):
        """Yield src_file, func"""

        regex = re.compile(r"\"(.*?)\" (\S*)")

        for content in self.__iter_file_regex(self.exported, regex):
            yield content

    def iter_calls(self):
        """Yield context_file, context_func, func, call_line, call_type, args"""

        regex = re.compile(r'\"(.*?)\" (\S*) (\S*) (\S*) (\S*) (.*)')
        args_regex = re.compile(r"actual_arg_func_name(\d+)=\s*(\w+)\s*")

        for content in self.__iter_file_regex(self.call, regex):
            content = list(content)

            # Last element should be args
            content[-1] = args_regex.findall(content[-1])

            yield content

    def iter_calls_by_pointers(self):
        """Yield context_file, context_func, func_ptr, call_line"""

        regex = re.compile(r'\"(.*?)\" (\S*) (\S*) (\S*)')

        for content in self.__iter_file_regex(self.callp, regex):
            yield content

    def iter_functions_usages(self):
        """Yield context_file, context_func, func, line"""

        regex = re.compile(r'\"(.*?)\" (\S*) (\S*) (\S*)')

        for content in self.__iter_file_regex(self.use_func, regex):
            yield content

    def iter_macros_definitions(self):
        """Yield file, macro, line"""

        regex = re.compile(r"\"(.*?)\" (\S*) (\S*)")

        for content in self.__iter_file_regex(self.define, regex):
            yield content

    def iter_macros_expansions(self):
        """Yield exp_file, def_file, macro, exp_line, def_line, args_str"""

        regex = re.compile(r'\"(.*?)\" \"(.*?)\" (\S*) (\S*) (\S*)(.*)')
        arg_regex = re.compile(r' actual_arg\d+=(.*)')

        for content in self.__iter_file_regex(self.expand, regex):
            content = list(content)

            args = list()

            # Last element should be args
            if content[-1]:
                for arg in content[-1].split(','):
                    m_arg = arg_regex.match(arg)
                    if m_arg:
                        args.append(m_arg.group(1))

            content[-1] = args

            yield content

    def iter_typedefs(self):
        """Yeild scope_file, declaration"""

        regex = re.compile(r'\"(.*?)\" typedef (.*)')

        for content in self.__iter_file_regex(self.typedefs, regex):
            yield content

    def __iter_file_regex(self, file, regex):
        for line in self.__iter_file(file):
            m = regex.match(line)

            if not m:
                self.error("CIF output has unexpected format: {!r}".format(line))
                raise SyntaxError

            yield m.groups()

    def __iter_file(self, file):
        if not os.path.isfile(file):
            return []

        with open(file, "r") as f:
            for line in f:
                yield line


# Moving this function outside output_file class increases performance
def normalize_file(file, storage, cif_output_dir, expand):
    if not os.path.isfile(file):
        return

    # Path to the source file is encoded in the path to the CIF output file
    path = os.path.dirname(file)

    path = path.replace(storage, "")
    path = path.replace(cif_output_dir, "")

    if "\\/" in path:
        raise "Normalized path looks weird: {!r}".format(path)

    expand_file = True if file.endswith(expand) else False

    if expand_file:
        path, def_path = path.split("/CLADE-EXPAND")

    seen = set()
    new_file = file + ".tmp"

    # Read large files (>= 100mb) line by line
    if os.path.getsize(file) >= 104857600:
        with codecs.open(file, "r", encoding="utf8", errors="ignore") as fh:
            with open(new_file, "w") as new_fh:
                for line in fh:
                    if not line:
                        continue

                    # Storing hash of string instead of string itself reduces memory usage by 30-40%
                    h = hashlib.md5(line.encode("utf-8")).hexdigest()
                    if h in seen:
                        continue

                    seen.add(h)

                    if expand_file:
                        new_fh.write('"{}" "{}" {}'.format(path, def_path, line))
                    else:
                        new_fh.write('"{}" {}'.format(path, line))
    else:
        lines = []
        with codecs.open(file, "r", encoding="utf8", errors="ignore") as fh:
            lines = fh.readlines()

            new_lines = []
            for line in lines:
                h = hashlib.md5(line.encode("utf-8")).hexdigest()
                if h in seen:
                    continue

                seen.add(h)

                if expand_file:
                    new_lines.append('"{}" "{}" {}'.format(path, def_path, line))
                else:
                    new_lines.append('"{}" {}'.format(path, line))

            with open(new_file, "w") as new_fh:
                new_fh.writelines(new_lines)

    os.replace(new_file, file)
