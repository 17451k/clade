# Copyright (c) 2019 ISP RAS (http://www.ispras.ru)
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

try:
    import cchardet as chardet
except ImportError:
    import chardet

import os
import re
import shlex
import subprocess

from clade.extensions.compiler import Compiler
from clade.extensions.opts import requires_value, cl_preprocessor_deps_opts

# TODO: Support /FA and /Fa options (output assembler code, .cod or .asm)
# TODO: Support /Fe option (Name of the output EXE file)
# /Fe[pathname] /Fe: pathname


class CL(Compiler):
    requires = Compiler.requires + ["Path"]

    __version__ = "1"

    def parse(self, cmds_file):
        super().parse(cmds_file, self.conf.get("CL.which_list", []))

    def parse_cmd(self, cmd):
        self.debug("Parse: {}".format(cmd))
        parsed_cmd = self.__parse_opts(cmd)

        if self.is_bad(parsed_cmd):
            self.dump_bad_cmd_id(cmd["id"])
            return

        deps = set(self.__get_deps(cmd["id"], parsed_cmd) + parsed_cmd["in"])
        self.dump_deps_by_id(cmd["id"], deps, parsed_cmd["cwd"])

        self.dump_cmd_by_id(cmd["id"], parsed_cmd)

        if self.conf.get(
            "Compiler.store_deps"
        ) and self.is_a_compilation_command(parsed_cmd):
            self.store_deps_files(deps, parsed_cmd["cwd"])

    def __parse_opts(self, cmd):
        parsed_cmd = self._get_cmd_dict(cmd)

        if self.name not in requires_value:
            raise RuntimeError(
                "Command type '{}' is not supported".format(self.name)
            )

        opts = iter(cmd["command"][1:])
        input_opts = ["/Tc", "-Tc", "/Tp", "-Tp"]

        for opt in opts:
            if opt in requires_value[self.name]:
                val = next(opts)
                parsed_cmd["opts"].extend([opt, val])

                if opt == "/link" or opt == "-link":
                    while True:
                        val = next(opts, None)
                        if not val:
                            break
                        parsed_cmd["opts"].append(val)

                if opt in input_opts:
                    parsed_cmd["in"].append(val)
            elif re.search(r"^[/-]", opt):
                parsed_cmd["opts"].append(opt)

                for prefix in input_opts:
                    if opt.startswith(prefix):
                        # All these options has length of 3
                        parsed_cmd["in"].append(opt[3:])
            else:
                parsed_cmd["in"].append(opt)

        if not parsed_cmd["out"] and (
            "/c" in parsed_cmd["opts"] or "-c" in parsed_cmd["opts"]
        ):
            for cmd_in in parsed_cmd["in"]:
                for opt in parsed_cmd["opts"]:
                    if re.search(r"[/-]Fo", opt):
                        obj_path = re.sub(r"[/-]Fo", "", opt)

                        if not os.path.isabs(obj_path):
                            obj_path = os.path.join(
                                parsed_cmd["cwd"], obj_path
                            )

                        if obj_path.endswith(".obj"):
                            parsed_cmd["out"].append(obj_path)
                        else:
                            obj_name = os.path.basename(
                                os.path.splitext(cmd_in)[0] + ".obj"
                            )
                            parsed_cmd["out"].append(
                                os.path.join(obj_path, obj_name)
                            )

                        break
                else:
                    obj_name = os.path.basename(
                        os.path.splitext(cmd_in)[0] + ".obj"
                    )
                    cmd_out = os.path.join(parsed_cmd["cwd"], obj_name)
                    parsed_cmd["out"].append(cmd_out)

        if not parsed_cmd["out"]:
            for cmd_in in parsed_cmd["in"]:
                exe_name = os.path.basename(
                    os.path.splitext(cmd_in)[0] + ".obj"
                )
                cmd_out = os.path.join(parsed_cmd["cwd"], exe_name)
                parsed_cmd["out"].append(cmd_out)

        for opt in parsed_cmd["opts"]:
            if re.search(r"[/-](E|EP)$", opt):
                parsed_cmd["out"] = list()

        if any(i for i in parsed_cmd["opts"] if i in ["/P", "-P"]):
            parsed_cmd["out"] = list()

            for opt in parsed_cmd["opts"]:
                if re.search(r"[/-]Fi", opt):
                    if len(parsed_cmd["in"] != 1):
                        raise RuntimeError(
                            "/Fi option could only be used with a single input file"
                        )

                    i_path = re.sub(r"[/-]Fi", "", opt)

                    if os.path.splitext(i_path)[1]:
                        parsed_cmd["out"].append(i_path)
                    else:
                        parsed_cmd["out"].append(i_path + ".i")
                    break
            else:
                for cmd_in in parsed_cmd["in"]:
                    i_name = os.path.basename(
                        os.path.splitext(cmd_in)[0] + ".i"
                    )
                    parsed_cmd["out"].append(os.path.join(cmd["cwd"], i_name))

        return parsed_cmd

    def __get_deps(self, cmd_id, cmd):
        """Get a list of CL command dependencies."""
        deps = []
        for cmd_in in cmd["in"]:
            deps_file = self.__collect_deps(cmd_id, cmd, cmd_in)
            deps.extend(self.__parse_deps(deps_file))

        return deps

    def __collect_deps(self, cmd_id, cmd, cmd_in):
        deps_file = os.path.join(self.temp_dir, "{}-deps.txt".format(cmd_id))

        opts = ["/showIncludes", "/P"] if self.conf.get("Compiler.preprocess_cmds") else ["/showIncludes"]

        deps_cmd = (
            [cmd["command"][0]]
            + cmd["opts"]
            + opts
            + [cmd_in]
            + self.conf.get("Compiler.extra_preprocessor_opts", [])
        )

        self.debug("CWD: {!r}".format(cmd["cwd"]))
        self.debug("Executing command: {!r}".format(
            " ".join([shlex.quote(x) for x in deps_cmd]))
        )

        if not os.path.exists(cmd["cwd"]):
            self.warning("CWD for command {!r} was deleted after build".format(cmd_id))
            return deps_file

        with open(deps_file, "wb") as deps_fh:
            proc = subprocess.Popen(
                # deps_cmd,
                ["dir"],
                stdout=deps_fh,
                stderr=deps_fh,
                cwd=cmd["cwd"],
                shell=True,
            )
            proc.communicate()

        if self.conf.get("Compiler.preprocess_cmds"):
            if not proc.returncode:
                self.__preprocess_cmd(cmd, cmd_in)
            else:
                self.warning(
                    "Can't preprocess command with ID={!r} and input file {!r}".format(
                        cmd_id, cmd_in
                    )
                )

        return deps_file

    def __parse_deps(self, deps_file):
        deps = list()
        output_bytes = None

        if not os.path.exists(deps_file):
            return deps

        with open(deps_file, "rb") as deps_fh:
            output_bytes = deps_fh.read()

        os.remove(deps_file)

        if self.conf.get("Compiler.deps_encoding"):
            encoding = self.conf.get("Compiler.deps_encoding")
        else:
            encoding = chardet.detect(output_bytes)["encoding"]

        if not encoding:
            return deps

        for line in output_bytes.decode(encoding).split(os.linesep):
            m = re.search(
                r"(Note: including file:|Примечание: включение файла:)\s*(.*)",
                line,
            )
            if m:
                dep = os.path.normpath(m.group(2)).strip()
                deps.append(dep)

        return deps

    def __preprocess_cmd(self, cmd, cmd_in):
        # pre_to - the path where we want to move the preprocessor output
        pre_to = os.path.splitext(cmd_in)[0] + ".i"
        pre_to = os.path.join(cmd["cwd"], pre_to)
        # pre_from - the path to the preprocessor output file
        i_name = os.path.basename(os.path.splitext(cmd_in)[0] + ".i")
        pre_from = os.path.join(cmd["cwd"], i_name)
        # Move .i file to be near source file
        if not os.path.exists(pre_to):
            os.rename(pre_from, pre_to)

        # Detect encoding of preprocessed file
        if self.conf.get("CL.pre_encoding"):
            encoding = self.conf.get("CL.pre_encoding")
        else:
            rawdata = open(pre_to, "rb").read()
            encoding = chardet.detect(rawdata)["encoding"]

        # Normalize paths in line directives
        self.__normalize_paths(pre_to, cmd["cwd"], encoding)

        if self.conf.get("Compiler.preprocess_cmds"):
            self.debug("Preprocessed file: {}".format(pre_to))
            self.store_pre_files([pre_to], cmd["cwd"], encoding)

        os.remove(pre_to)

    def __normalize_paths(self, c_file, cwd, encoding):
        with open(c_file, "r", encoding=encoding) as c_file_fh, open(
            c_file + ".new", "w", encoding="utf-8"
        ) as c_file_new_fh:
            for line in c_file_fh:
                m = re.match(r"\s*#line \d* \"(.*?)\"", line)

                if m:
                    inc_file = m.group(1)

                    norm_inc_file = self.extensions["Path"].normalize_rel_path(
                        inc_file.strip(), cwd
                    )

                    line = line.replace(inc_file, norm_inc_file)

                c_file_new_fh.write(line)

        try:
            os.replace(c_file + ".new", c_file)
        except OSError:
            os.remove(c_file + ".new")

    def is_a_compilation_command(self, cmd):
        if not super().is_a_compilation_command(cmd):
            return False

        if "opts" not in cmd:
            opts = self.load_opts_by_id(cmd["id"])
        else:
            opts = cmd["opts"]

        if set(opts).intersection(cl_preprocessor_deps_opts):
            return False

        return True
