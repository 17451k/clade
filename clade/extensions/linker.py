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

import abc
import os
import re

from clade.extensions.compiler import Compiler
from clade.extensions.opts import requires_value


class Linker(Compiler):
    """Parent class for all C compilers, who are also linkers"""

    __version__ = "1"

    def _parse_linker_opts(self, which, parsed_cmd):
        archives = []

        searchdirs = self.__get_searchdirs(which, parsed_cmd)

        opts = iter(parsed_cmd["opts"])
        for opt in opts:
            if opt in ["-l", "--library"]:
                name = next(opts)

                self.__find_archive(name, searchdirs, parsed_cmd)
            elif opt in requires_value[self.name]:
                continue
            elif opt.startswith("-l") or opt.startswith("--library="):
                name = re.sub(r"^-l", "", opt)
                name = re.sub(r"^--library=", "", name)

                self.__find_archive(name, searchdirs, parsed_cmd)

        return archives

    @abc.abstractmethod
    def _get_default_searchdirs(self, which, parse_cmd):
        '''Returns default search dir, where linker searches for libraries'''
        pass

    def __get_searchdirs(self, which, parsed_cmd):
        # sysroot paths are not supported (searchdir begins with "=")
        default_searchdirs = self._get_default_searchdirs(which)
        self.debug(f"Default search dirs for {which} are: {default_searchdirs}")

        searchdirs = default_searchdirs + self.conf.get("Linker.searchdirs", [])

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

        syslibroot = self.__get_syslibroot(parsed_cmd)

        return [syslibroot + s for s in searchdirs]

    def __get_syslibroot(self, parsed_cmd):
        syslibroot = ""

        opts = iter(parsed_cmd["opts"])

        for opt in opts:
            if opt == "-syslibroot":
                syslibroot = next(opts)
                break

        return syslibroot

    def __find_archive(self, name, searchdirs, parsed_cmd):
        if not searchdirs:
            return

        names = []

        if name.startswith(":"):
            names.append(name[1:])
        else:
            names.append("lib" + name + ".dylib")  # macOS
            names.append("lib" + name + ".tbd")  # macOS, "text-based stub libraries"
            names.append("lib" + name + ".so")
            names.append("lib" + name + ".a")
            names.append(name + ".a")

        for searchdir in searchdirs:
            for basename in names:
                archive = os.path.normpath(os.path.join(searchdir, basename))
                if os.path.exists(archive):
                    if archive not in parsed_cmd["in"]:
                        parsed_cmd["in"].append(archive)
                    break
            else:
                continue
            break
        else:
            self.warning("Couldn't find {!r} archive in {}".format(name, searchdirs))
