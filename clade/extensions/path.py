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

import functools
import glob
import os
import sys

from typing import List

from clade.cmds import get_build_dir
from clade.extensions.abstract import Extension


class Path(Extension):
    __version__ = "4"

    @Extension.prepare
    def parse(self, cmds_file):
        build_cwd = get_build_dir(cmds_file)
        self.conf["build_dir"] = self.normalize_abs_path(build_cwd)

    def normalize_rel_paths(self, paths: List[str], cwd: str) -> List[str]:
        return [self.normalize_rel_path(path, cwd) for path in paths]

    @functools.lru_cache()
    def normalize_rel_path(self, path: str, cwd: str) -> str:
        cwd = cwd.strip()
        path = path.strip()

        key = self.__get_key(path, cwd)
        if sys.platform == "win32":
            key = key.lower()

        if not os.path.isabs(path):
            abs_path = os.path.join(cwd, path)
        else:
            abs_path = path

        return self.normalize_abs_path(abs_path)

    @functools.lru_cache()
    def normalize_abs_path(self, path: str) -> str:
        path = path.strip()

        key = path
        if sys.platform == "win32":
            key = key.lower()

        npath = os.path.normpath(path)

        if sys.platform == "win32":
            npath = self.__get_actual_filename(npath)
            npath = npath.replace("\\", "/")
            drive, tail = os.path.splitdrive(npath)
            if drive:
                npath = "/" + drive[:-1] + tail

        return npath

    def __get_key(self, path, cwd):
        return cwd + "/" + path

    def __get_actual_filename(self, path):
        if path[-1] in "\\":
            path = path[:-1]
        dirs = path.split("\\")
        # disk letter
        test_path = [dirs[0].upper()]
        for d in dirs[1:]:
            test_path += ["%s[%s]" % (d[:-1], d[-1])]
        res = glob.glob("\\".join(test_path))
        if not res:
            # File not found
            return path
        return res[0]
