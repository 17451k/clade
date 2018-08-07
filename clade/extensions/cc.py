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
import re
import subprocess
import sys

from clade.extensions.common import Common, parse_args


class CC(Common):
    """Class for parsing CC build commands."""
    def __init__(self, work_dir, conf=None):
        if not conf:
            conf = dict()

        if "CC.which_list" not in conf:
            self.which_list = [
                "/usr/bin/gcc",
                "/usr/local/bin/gcc",
                "/usr/bin/clang",
                "/usr/local/bin/clang"
            ]
        else:
            self.which_list = conf["CC.which_list"]

        if "CC.with_system_header_files" not in conf:
            conf["CC.with_system_header_files"] = True

        super().__init__(work_dir, conf)

    def parse(self, cmds_file):
        super().parse(cmds_file, self.which_list)

    def parse_cmd(self, cmd):
        cmd_id = cmd["id"]

        parsed_cmd = super().parse_cmd(cmd, self.name)
        self.debug("Parsed command: {}".format(parsed_cmd))

        deps = self.__get_deps(cmd_id, parsed_cmd)
        self.debug("Dependencies: {}".format(deps))
        self.dump_deps_by_id(cmd_id, deps)

        self.dump_opts_by_id(cmd_id, parsed_cmd["opts"])
        del parsed_cmd["opts"]

        self.dump_cmd_by_id(cmd_id, parsed_cmd)

    def __get_deps(self, cmd_id, cmd):
        """Get a list of CC command dependencies."""
        deps_file = self.__collect_deps(cmd_id, cmd)
        return self.__parse_deps(deps_file)

    def __collect_deps(self, cmd_id, cmd):
        deps_file = os.path.join(self.temp_dir, "{}-deps.txt".format(cmd_id))

        if self.conf["CC.with_system_header_files"]:
            additional_opts = ["-Wp,-MD,{}".format(deps_file), "-M"]
        else:
            additional_opts = ["-Wp,-MMD,{}".format(deps_file), "-MM"]

        opts = cmd["opts"] + additional_opts
        command = [cmd["command"]] + opts + cmd["in"]

        # Do not execute a command that does not contain any input files
        if "-" not in command and cmd["in"]:
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=cmd["cwd"])

        return deps_file

    def __parse_deps(self, deps_file):
        deps = []

        if os.path.isfile(deps_file):
            with open(deps_file, encoding='utf8') as fp:
                match = re.match(r'[^:]+:(.+)', fp.readline())
                if match:
                    first_dep_line = match.group(1)
                else:
                    raise RuntimeError('Dependencies file has unsupported format')

                for dep_line in [first_dep_line] + fp.readlines():
                    if ':' in dep_line:
                        break
                    dep_line = dep_line.lstrip(' ')
                    dep_line = dep_line.rstrip(' \\\n')
                    if not dep_line:
                        continue
                    deps.extend(dep_line.split(' '))

            os.remove(deps_file)

        return deps


def parse(args=sys.argv[1:]):
    args = parse_args(args)

    c = CC(args.work_dir, conf={"log_level": args.log_level})
    c.parse(args.cmds_file)
