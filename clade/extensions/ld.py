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

from clade.extensions.common import Common


class LD(Common):
    __version__ = "1"

    def parse(self, cmds_file):
        super().parse(cmds_file, self.conf.get("LD.which_list", []))

    def parse_cmd(self, cmd):
        parsed_cmd = super().parse_cmd(cmd, self.name)

        if self.is_bad(parsed_cmd):
            self.dump_bad_cmd_id(parsed_cmd["id"])
            return

        self.__parse_opts(parsed_cmd)

        self.dump_cmd_by_id(cmd["id"], parsed_cmd)

    def __parse_opts(self, parsed_cmd):
        archives = []

        searchdirs = self.__get_searchdirs(parsed_cmd)

        opts = iter(parsed_cmd["opts"])
        for opt in opts:
            if opt in ["-l", "--library"]:
                name = next(opts)

                self.__find_archive(name, searchdirs, parsed_cmd)
            elif opt.startswith("-l") or opt.startswith("--library="):
                name = re.sub(r"^-l", "", opt)
                name = re.sub(r"^--library=", "", name)

                self.__find_archive(name, searchdirs, parsed_cmd)

        return archives

    def __get_searchdirs(self, parsed_cmd):
        # sysroot paths are not supported (searchdir begins with "=")
        searchdirs = self.conf.get("LD.searchdirs", [])

        opts = iter(parsed_cmd["opts"])
        for opt in opts:
            if opt in ["-L", "--library-path"]:
                path = next(opts)

                path = os.path.normpath(os.path.join(parsed_cmd["cwd"], path))
                searchdirs.append(path)
            elif opt.startswith("-L") or opt.startswith("--library-path="):
                path = re.sub(r"^-L", "", opt)
                path = re.sub(r"^--library-path=", "", path)

                path = os.path.normpath(os.path.join(parsed_cmd["cwd"], path))
                searchdirs.append(os.path.normpath(path))

        return searchdirs

    def __find_archive(self, name, searchdirs, parsed_cmd):
        if not searchdirs:
            self.warning("Search directories are empty")
            return

        names = []

        if name.startswith(":"):
            names.append(name[1:])
        else:
            names.append("lib" + name + ".dylib")  # macOS
            names.append("lib" + name + ".so")
            names.append("lib" + name + ".a")
            names.append(name + ".a")

        for searchdir in searchdirs:
            for name in names:
                archive = os.path.normpath(os.path.join(searchdir, name))
                if os.path.exists(archive):
                    if archive not in parsed_cmd["in"]:
                        parsed_cmd["in"].append(archive)
                    break
            else:
                continue
            break
        else:
            self.warning("Couldn't find {!r} archive in {}".format(name, searchdirs))
