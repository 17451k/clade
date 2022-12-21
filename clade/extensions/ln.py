# Copyright (c) 2022 Ilya Shchepetkov
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
import pathlib
import re

from clade.extensions.common import Common


class LN(Common):
    __version__ = "1"

    def parse(self, cmds_file):
        super().parse(cmds_file, self.conf.get("LN.which_list", []))

    def parse_cmd(self, cmd):
        parsed_cmd = {
            "id": cmd["id"],
            "in": [],
            "out": [],
            "opts": [],
            "cwd": cmd["cwd"],
            "command": cmd["command"],
        }

        opts = iter(cmd["command"][1:])
        files = []
        out = None

        # First we parse only options, leaving all the files unparsed
        for opt in opts:
            if re.search(r"^-", opt):
                if opt == "-t" or opt == "--target-directory":
                    # Value is the next option.
                    out = os.path.normpath(next(opts))
                elif opt.startswith("--target-directory=") or opt.startswith("-t"):
                    out = opt.replace("--target-directory=", "")
                    out = opt.replace("-t", "")
                else:
                    parsed_cmd["opts"].append(opt)
            else:
                files.append(os.path.normpath(opt))

        # ln cases (ignoring options):
        # - FILE
        # - DIR
        # - FILE OUT_FILE
        # - FILE OUT_DIR
        # - DIR OUT_DIR
        # - FILE DIR FILE DIR OUT_DIR

        if len(files) == 1 or len(files) > 2 or out:
            # Output file will be current working directory, if not specified with -t
            if len(files) == 1 and not out:
                out = parsed_cmd["cwd"]
            # Or it can be specified in the command itself
            elif len(files) > 2 and not out:
                out = files[-1]
                files = files[:-1]

            for file in files:
                if os.path.isfile(file) or not os.path.isdir(file):
                    parsed_cmd["in"].append(file)
                    parsed_cmd["out"].append(os.path.join(out, os.path.basename(file)))
                else:
                    # If input file is a directory, we threat all the files inside it
                    # as input files
                    in_files = self.__get_files(file)
                    parsed_cmd["in"].extend(in_files)

                    for in_file in in_files:
                        in_file = in_file.replace(file + "/", "")
                        parsed_cmd["out"].append(os.path.join(out, in_file))
        # This case is special: name of the output file differs from the name of the input one
        elif len(files) == 2:
            if os.path.isfile(files[0]) or not os.path.isdir(files[0]):
                parsed_cmd["in"].append(files[0])

                if os.path.isdir(files[1]):
                    parsed_cmd["out"].append(os.path.join(files[1], os.path.basename(files[0])))
                else:
                    parsed_cmd["out"].append(files[1])
            else:
                parsed_cmd["in"] = self.__get_files(files[0])

                for in_file in parsed_cmd["in"]:
                    in_file = in_file.replace(files[0] + "/", "")
                    parsed_cmd["out"].append(os.path.join(files[1], in_file))
        else:
            self.error(f"No files in {parsed_cmd['id']} command")

        if not parsed_cmd["out"] and not parsed_cmd["in"]:
            self.error(f"Command {cmd} is incorrectly parsed: {parsed_cmd}")
            return

        if self.is_bad(parsed_cmd):
            self.dump_bad_cmd_id(cmd["id"])
            return

        self.dump_cmd_by_id(cmd["id"], parsed_cmd)

        return parsed_cmd

    def get_pairs(self):
        '''Returns iterator for all (file, its symlink) pairs'''
        cmds = self.load_all_cmds()

        for cmd in cmds:
            for i, file in enumerate(cmd["in"]):
                # ln commands always have paired input and output files:
                # in = ["test1.c", "test2.c"]
                # out = ["link/test1.c", "link/test2.c"]
                symlink = cmd["out"][i]

                yield (file, symlink)

    def __get_files(self, path):
        files = []

        if os.path.isfile(path):
            files.append(os.path.normpath(path))
        else:
            for p in pathlib.Path(path).rglob("*"):
                if p.is_file():
                    files.append(os.path.normpath(p))

        return files
