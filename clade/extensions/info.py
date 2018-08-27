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
import jinja2
import os
import re
import shutil
import subprocess
import sys

from clade.extensions.abstract import Extension
from clade.extensions.utils import normalize_path, parse_args


def unwrap(*args, **kwargs):
    return Info._run_cif(*args, **kwargs)


class Info(Extension):
    requires = ["CC"]

    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        # Without this option it will be difficult to link data coming from Info and by CC extensions
        conf["CC.with_system_header_files"] = True

        if "Info.max_args" not in conf:
            conf["Info.max_args"] = 30

        super().__init__(work_dir, conf)

        self.aspect_template = os.path.join(os.path.dirname(__file__), "info.aspect.tmpl")
        self.aspect = os.path.join(self.work_dir, "info.aspect")

        self.execution = os.path.join(self.work_dir, "execution.txt")  # Info about function definitions
        self.call = os.path.join(self.work_dir, "call.txt")  # Info about function calls
        self.decl = os.path.join(self.work_dir, "declare_func.txt")  # Info about function declarations
        self.callp = os.path.join(self.work_dir, "callp.txt")  # Info about function calls via a function pointer
        self.use_func = os.path.join(self.work_dir, "use_func.txt")  # Info about using function names in pointers (in function context only)
        self.use_var = os.path.join(self.work_dir, "use_var.txt")  # Info about using global variables in function context
        self.init_global = os.path.join(self.work_dir, "init_global.txt")  # Info about init values of global variables
        # TODO: Add info: define to aspect file
        self.define = os.path.join(self.work_dir, "define.txt")  # Info about macro functions
        self.expand = os.path.join(self.work_dir, "expand.txt")  # Info about macros
        self.exported = os.path.join(self.work_dir, "exported.txt")  # Info about exported functions (Linux kernel only)
        self.typedefs = os.path.join(self.work_dir, "typedefs.txt")  # Info about typedefs

        self.files = [self.execution, self.call, self.decl,
                      self.callp, self.use_func, self.use_var,
                      self.init_global, self.define,
                      self.expand, self.exported,
                      self.typedefs]

        self.err_log = os.path.join(self.work_dir, "err.log")  # Path to file containing CIF error log

    def parse(self, cmds_file):
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.parse_prerequisites(cmds_file)

        if not shutil.which("cif"):
            sys.exit("Can't find CIF in PATH")

        self.log("Start CIF")
        self.__gen_info_requests()

        cmds = self.extensions["CC"].load_all_cmds()

        with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as p:
            for cmd in cmds:
                p.submit(unwrap, self, cmd)

        self.log("CIF finished")

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        self.__normalize_cif_output(cmds_file)
        self.log("Finish")

    def __gen_info_requests(self):
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(self.aspect_template)),
            line_statement_prefix='//',
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=jinja2.StrictUndefined
        )

        self.debug('Render template {}'.format(self.aspect_template))

        if os.path.isfile(self.aspect):
            return

        if not os.path.isdir(self.work_dir):
            os.makedirs(self.work_dir)

        with open(self.aspect, "w", encoding="utf8") as fh:
            fh.write(env.get_template(os.path.basename(self.aspect_template)).render({
                "max_args_num": self.conf["Info.max_args"],
                "arg_patterns": {i: ", ".join(["$"] * (i + 1)) for i in range(self.conf["Info.max_args"])},
                "arg_printf_patterns": {i: ' '.join(["arg{}='%s'".format(j + 1) for j in range(i + 1)])
                                        for i in range(self.conf["Info.max_args"])},
                "arg_types": {i: ",".join(["$arg_type_str{}".format(j + 1) for j in range(i + 1)])
                              for i in range(self.conf["Info.max_args"])},
                "arg_values": {i: ",".join(["$arg_value{}".format(j + 1) for j in range(i + 1)])
                               for i in range(self.conf["Info.max_args"])},
                "arg_vals": {i: ",".join(["$arg_val{}".format(j + 1) for j in range(i + 1)])
                             for i in range(self.conf["Info.max_args"])}
            }))
        self.debug('Rendered template was stored into file {}'.format(self.aspect))

    def _run_cif(self, cmd):
        if self.__is_cmd_bad_for_cif(cmd):
            return

        cif_out = os.path.join(self.temp_dir, cmd["out"])

        if not os.path.isdir(cif_out):
            try:
                os.makedirs(os.path.dirname(cif_out))
            except OSError as e:
                if e.errno != 17:
                    raise

        os.environ["CIF_INFO_DIR"] = self.work_dir
        os.environ["CC_IN_FILE"] = cmd['in'][0]
        os.environ["CIF_CMD_CWD"] = cmd['cwd']

        cif_args = ["cif",
                    "--debug", "ALL",
                    "--in", cmd["in"][0],
                    "--aspect", self.aspect,
                    "--back-end", "src",
                    "--stage", "instrumentation",
                    "--out", cif_out]

        cif_args.append("--")

        opts = self.extensions["CC"].load_opts_by_id(cmd["id"])
        opts.extend(self.conf.get("Info.extra CIF opts", []))
        cif_args.extend(self.__filter_opts_for_cif(opts))

        r = subprocess.run(cif_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cmd["cwd"], universal_newlines=True)

        if r.returncode:
            self.__save_log(cif_args, r.stdout)

    def __is_cmd_bad_for_cif(self, cmd):
        if cmd["in"] == []:
            return True

        if not cmd["out"]:
            # Add output file for CIF
            cmd["out"] = cmd["in"][0]

        cif_in = cmd["in"][0]

        if cif_in == "-" or cif_in == "/dev/null":
            return True
        elif re.search(r'\.(s|S)$', cif_in) or re.search(r'\.o$', cif_in):
            # Assember or object files are not supported
            return True

        return False

    def __filter_opts_for_cif(self, opts):
        filtered_opts = []

        # CIF is based on GCC 4.6 which doesn't support some options
        # TODO: Check this list for compatibility with new CIF based on GCC 7.3
        unsupported_opts = [
            "--param=allow-store-data-races",
            "-mpreferred-stack-boundary",
            "-Wno-unused-const-variable",
            "-fsanitize=kernel-address",
            "-Wno-maybe-uninitialized",
            "--param", "asan",  # --param asan-stack=1
            "-mno-abicalls",
            "-Werror",
            "-mthumb",
            "-mips32",
            "-fasan",
            "-mcpu",
            "-m16",
            "-G0",
            '-mindirect-branch-register',
            '-mindirect-branch=thunk-extern',
            '-mindirect-branch-register',
            "-DPAGER_ENV=\"LESS=FRX LV=-c\"",
            "-imultiarch",
            "-quiet",
            "-auxbase-strip",
            "-fstack-protector-strong"
        ]

        # Make a regex that matches if any of our regexes match.
        combined = "(" + ")|(".join(unsupported_opts) + ")"

        for opt in opts:
            if re.match(combined, opt):
                continue

            filtered_opts.append(opt)

        return filtered_opts

    def __save_log(self, args, log):
        with open(self.err_log, "a") as log_fh:
            log_fh.write(' '.join(args) + "\n\n")
            log_fh.writelines(log)
            log_fh.write("\n\n")

    def __normalize_cif_output(self, cmds_file):
        self.log("Normalizing CIF output")

        src = self.get_build_cwd(cmds_file)

        regexp = re.compile(r'(\S*) (\S*) (.*)')

        for file in self.files:
            if file == self.init_global:
                continue

            if not os.path.isfile(file):
                self.debug("Couldn't find '{}'".format(file))
                continue

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
                                if not os.path.isabs(path):
                                    path = os.path.join(cwd, path)
                                path = normalize_path(path, src)
                                temp_fh.write("{} {}\n".format(path, rest))

            os.remove(file)
            os.rename(file + ".temp", file)

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


def parse(args=sys.argv[1:]):
    conf = parse_args(args)

    c = Info(conf["work_dir"], conf=conf)
    c.parse(conf["cmds_file"])
