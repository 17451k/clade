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

import chardet
import os
import re
import subprocess
import sys

from clade.extensions.compiler import Compiler
from clade.extensions.opts import requires_value
from clade.extensions.utils import common_main

# TODO: Suppport /E and /EP options (Preprocess to stdout)
# TODO: Suppport /FA and /Fa options (output assembler code, .cod or .asm)
# TODO: Support /Fe option (Name of the output EXE file)
# /Fe[pathname] /Fe: pathname
# TODO: Suppport /Fi option (Name of the output preprocessed code, .i)
# Option is used together with /P


class CL(Compiler):
    def parse(self, cmds_file):
        super().parse(cmds_file, self.conf.get("CL.which_list", []))

    def parse_cmd(self, cmd):
        self.debug("Parse: {}".format(cmd))
        parsed_cmd = self._get_cmd_dict(cmd)

        if self.name not in requires_value:
            raise RuntimeError(
                "Command type '{}' is not supported".format(self.name)
            )

        opts = iter(cmd["command"][1:])

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
            elif re.search(r"^(/|-)", opt):
                parsed_cmd["opts"].append(opt)
            else:
                parsed_cmd["in"].append(opt)

        if not parsed_cmd["out"] and (
            "/c" in parsed_cmd["opts"] or "-c" in parsed_cmd["opts"]
        ):
            for cmd_in in parsed_cmd["in"]:
                for opt in parsed_cmd["opts"]:
                    if re.search(r"/Fo|-Fo", opt):
                        obj_path = re.sub(r"/Fo|-Fo", "", opt)

                        if not os.path.isabs(obj_path):
                            obj_path = os.path.join(
                                parsed_cmd["cwd"], obj_path
                            )

                        if os.path.isfile(obj_path):
                            parsed_cmd["out"].append(obj_path)
                        elif os.path.exists(obj_path):
                            obj_name = os.path.basename(
                                os.path.splitext(cmd_in)[0] + ".obj"
                            )
                            parsed_cmd["out"].append(
                                os.path.join(obj_path, obj_name)
                            )
                        else:
                            raise RuntimeError(
                                "Can't determine output file of CL command"
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

        if self.is_bad(parsed_cmd):
            return

        deps = set(self.__get_deps(cmd["id"], parsed_cmd) + parsed_cmd["in"])
        self.debug("Dependencies: {}".format(deps))
        self.dump_deps_by_id(cmd["id"], deps)

        self.debug("Parsed command: {}".format(parsed_cmd))
        self.dump_cmd_by_id(cmd["id"], parsed_cmd)

        if self.conf.get("Compiler.store_deps"):
            self.store_src_files(deps, parsed_cmd["cwd"])

    def __get_deps(self, cmd_id, cmd):
        """Get a list of CL command dependencies."""
        unparsed_deps = self.__collect_deps(cmd_id, cmd)
        return self.__parse_deps(unparsed_deps)

    def __collect_deps(self, cmd_id, cmd):
        try:
            deps_cmd = (
                cmd["command"]
                + ["/showIncludes", "/P"]
                + self.conf.get("Compiler.extra_preprocessor_opts", [])
            )
            output_bytes = subprocess.check_output(
                deps_cmd,
                stderr=subprocess.STDOUT,
                cwd=cmd["cwd"],
                shell=True,
                universal_newlines=False,
            )
        except subprocess.CalledProcessError:
            self.warning("Couldn't get dependencies")
            self.warning("CWD: {!r}".format(cmd["cwd"]))
            self.warning("Command: {!r}".format(" ".join(deps_cmd)))
            return ""

        self.__preprocess_cmd(cmd)

        encoding = chardet.detect(output_bytes)["encoding"]
        if not encoding:
            return ""
        return output_bytes.decode(encoding)

    def __parse_deps(self, unparsed_deps):
        deps = list()

        for line in unparsed_deps.split("\r\n"):
            m = re.search(
                r"(Note: including file:|Примечание: включение файла:)\s*(.*)",
                line,
            )
            if m:
                dep = os.path.normpath(m.group(2)).strip()
                deps.append(dep)

        return deps

    def __preprocess_cmd(self, cmd):
        pre = []

        for cmd_in in cmd["in"]:
            # pre_to - the path where we want to move the preprocessor output
            pre_to = os.path.splitext(cmd_in)[0] + ".i"
            pre_to = os.path.join(cmd["cwd"], pre_to)
            # pre_from - the path to the preprocessor output file
            i_name = os.path.basename(os.path.splitext(cmd_in)[0] + ".i")
            pre_from = os.path.join(cmd["cwd"], i_name)
            # Move .i file to be near source file
            if not os.path.exists(pre_to):
                os.rename(pre_from, pre_to)

            # Normalize paths in line directives
            self.__normalize_paths(pre_to, cmd["cwd"])
            pre.append(pre_to)

        if self.conf.get("Compiler.preprocess_cmds"):
            self.debug("Preprocessed files: {}".format(pre))
            self.store_src_files(pre, cmd["cwd"])

        for pre_file in pre:
            os.remove(pre_file)

    def __normalize_paths(self, c_file, cwd):
        rawdata = open(c_file, 'rb').read()
        encoding = chardet.detect(rawdata)["encoding"]

        with open(c_file, "r", encoding=encoding) as c_file_fh, open(
            c_file + ".new", "w", encoding="utf-8"
        ) as c_file_new_fh:
            for line in c_file_fh:
                m = re.match(r"#line \d* \"(.*?)\"", line)

                if m:
                    inc_file = m.group(1)

                    norm_inc_file = os.path.normpath(inc_file)
                    norm_inc_file = norm_inc_file.strip()
                    norm_inc_file = norm_inc_file.replace("\\", "\\\\")

                    line = line.replace(inc_file, norm_inc_file)

                c_file_new_fh.write(line)

        os.remove(c_file)
        os.rename(c_file + ".new", c_file)


def main(args=sys.argv[1:]):
    common_main(CL, args)
