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

import glob
import os
import sys

from clade.extensions.abstract import Extension


class Path(Extension):
    __version__ = "3"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.paths = dict()
        self.paths_folder = self.work_dir

    @Extension.prepare
    def parse(self, cmds_file):
        build_cwd = self.get_build_dir(cmds_file)
        self.conf["build_dir"] = self.normalize_abs_path(build_cwd)

    def get_rel_paths(self, paths, cwd):
        # TODO: check that paths is a list, not a string
        npaths = []

        for path in paths:
            npaths.append(self.get_rel_path(path, cwd))

        return npaths

    def get_rel_path(self, path, cwd):
        key = cwd + " " + path

        return self.__get_path_by_key(key, path)

    def get_abs_path(self, path):
        return self.__get_path_by_key(path, path)

    def __get_path_by_key(self, key, orig_path):
        if key not in self.paths or key.lower() not in self.paths:
            self.paths.update(self.load_paths_by_key(key))

        # get data either by key, or by key.lower()
        npath = self.paths.get(key, self.paths.get(key.lower()))

        if not npath:
            npath = orig_path

        if npath[0] != "/":
            self.error("{!r} path is not normalized".format(npath))
            raise RuntimeError

        return npath

    def load_paths_by_key(self, key):
        """Load information about paths grouped by key."""
        return self.load_data_by_key(self.paths_folder, [key, key.lower()])

    def normalize_rel_paths(self, paths, cwd):
        # TODO: check that paths is a list, not a string
        npaths = []

        for path in paths:
            npaths.append(self.normalize_rel_path(path, cwd))

        return npaths

    def normalize_rel_path(self, path, cwd):
        cwd = cwd.strip()
        path = path.strip()

        key = cwd + " " + path
        if sys.platform == "win32":
            key = key.lower()

        if key in self.paths:
            return self.paths[key]

        if not os.path.isabs(path):
            abs_path = os.path.join(cwd, path)
        else:
            abs_path = path

        npath = self.normalize_abs_path(abs_path)

        if path != npath:
            self.paths[key] = npath
            self.dump_data_by_key({key: npath}, self.paths_folder)

        return npath

    def normalize_abs_path(self, path):
        path = path.strip()

        key = path
        if sys.platform == "win32":
            key = key.lower()

        if key in self.paths:
            return self.paths[key]

        npath = os.path.normpath(path)

        if sys.platform == "win32":
            npath = self.__get_actual_filename(npath)
            npath = npath.replace("\\", "/")
            drive, tail = os.path.splitdrive(npath)
            if drive:
                npath = "/" + drive[:-1] + tail

        if path != npath:
            self.paths[key] = npath
            self.dump_data_by_key({key: npath}, self.paths_folder)

        return npath

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
