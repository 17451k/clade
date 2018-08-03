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

import jinja2
import multiprocessing
import os
import re
import subprocess
import sys

from clade.extensions.abstract import Extension
from clade.extensions.common import parse_args
from clade.extensions.utils import normalize_path
from clade.cmds import load_cmds, get_build_cwd


def unwrap(arg, **kwarg):
    return Info._run_cif(*arg, **kwarg)


class Info(Extension):
    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        self.requires = ["CC"]

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
        self.define = os.path.join(self.work_dir, "define.txt")  # Info about macro functions
        self.expand = os.path.join(self.work_dir, "expand.txt")  # Info about macros
        self.exported = os.path.join(self.work_dir, "exported.txt")  # Info about exported functions (Linux kernel only)
        self.typedefs = os.path.join(self.work_dir, "typedefs.txt")  # Info about typedefs

        self.files = [self.execution, self.call, self.decl,
                      self.callp, self.use_func, self.use_var,
                      self.init_global, self.define,
                      self.expand, self.exported,
                      self.exported]

        self.cif_err_log = os.path.join(self.work_dir, "cif_err.log")  # Path to file containing CIF error log

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

    def parse(self, cmds):
        if self.is_parsed():
            self.log("Skip parsing")
            return

        self.parse_prerequisites(cmds)

        self.log("Start CIF")

        self.__gen_info_requests()

        cmds = self.extensions["CC"].load_all_cmds()

        with multiprocessing.Pool(os.cpu_count()) as p:
            p.map(unwrap, zip([self] * len(cmds), cmds))

        self.log("CIF finished")

        self.__normalize_cif_output(cmds)

    def _run_cif(self, cmd):
        if self.__is_cmd_bad_for_cif(cmd):
            return

        cif_work_dir = os.path.join(self.work_dir, "cif")
        cif_out = os.path.normpath(os.path.join(cif_work_dir, cmd["out"]))

        if not os.path.isdir(cif_out):
            try:
                os.makedirs(os.path.dirname(cif_out))
            except OSError as e:
                if e.errno != 17:
                    raise

        os.environ["CWD"] = self.work_dir
        os.environ["CC_IN_FILE"] = cmd['in'][0]

        cif_args = ["cif",
                    "--debug", "ALL",
                    "--in", cmd["in"][0],
                    "--aspect", self.aspect,
                    "--back-end", "src",
                    "--stage", "instrumentation",
                    "--out", cif_out]

        cif_args.append("--")

        opts = self.extensions["CC"].load_opts_by_id(cmd["id"])
        cif_args.extend(self.__filter_opts_for_cif(opts))

        cif_log = os.path.join(cif_out + ".log")
        with open(cif_log, "w") as log_fh:
            if subprocess.call(cif_args, stdout=log_fh, stderr=log_fh, cwd=cmd["cwd"]):
                self.__store_error_information(cif_args, cif_log)

    def __is_cmd_bad_for_cif(self, cmd):
        if cmd["in"] == []:
            return True

        if not cmd["out"]:
            # TODO: investigate this case
            return True

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
            "-DPAGER_ENV=\"LESS=FRX LV=-c\""
        ]

        # Make a regex that matches if any of our regexes match.
        combined = "(" + ")|(".join(unsupported_opts) + ")"

        for opt in opts:
            if re.match(combined, opt):
                continue

            filtered_opts.append(opt)

        return filtered_opts

    def __store_error_information(self, args, log):
        with open(log, "r") as log_fh:
            log_str = log_fh.readlines()

        with open(self.cif_err_log, "a") as log_fh:
            log_fh.write("CIF ARGUMENTS: " + ' '.join(args) + "\n\n")
            log_fh.write("CIF LOG: ")
            log_fh.writelines(log_str)
            log_fh.write("\n\n")

    def __normalize_cif_output(self, cmds):
        self.log("Normalizing CIF output")

        src = get_build_cwd(cmds)

        for file in self.files:
            if file == self.init_global:
                continue

            if not os.path.isfile(file):
                self.debug("Couldn't find '{}'".format(file))
                continue

            seen = set()
            try:
                with open(file, "r", encoding='utf8') as fh:
                    with open(file + ".temp", "w") as temp_fh:
                        for line in fh:
                            if line not in seen:
                                seen.add(line)
                                m = re.match(r'(\S*) (.*)', line)

                                if m:
                                    path, rest = m.groups()
                                    if 'ext-modules' not in path:
                                        path = normalize_path(path, src)
                                    temp_fh.write("{} {}\n".format(path, rest))
            except UnicodeDecodeError as err:
                self.warning("Cannot open file {0} or {0}.temp: {1}".format(file, err))

            os.remove(file)
            os.rename(file + ".temp", file)

        self.log("Normalizing finished")


def parse(args=sys.argv[1:]):
    args = parse_args(args)

    c = Info(args.work_dir, conf={"log_level": args.log_level})
    if not c.is_parsed():
        c.parse(load_cmds(args.cmds_json))
