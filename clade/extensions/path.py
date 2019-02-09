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

import os
import glob
import sys
import re

from clade.extensions.abstract import Extension


class Path(Extension):
    def __init__(self, work_dir, conf=None, preset="base"):
        super().__init__(work_dir, conf=conf, preset=preset)

        self.paths = dict()
        self.paths_file = os.path.join(self.work_dir, "paths.txt")

    def parse(self, cmds_file):
        build_cwd = self.get_build_cwd(cmds_file)
        self.normalize_abs_path(build_cwd)

    def get_rel_paths(self, paths, cwd):
        # TODO: check that paths is a list, not a string
        npaths = []

        for path in paths:
            npaths.append(self.get_rel_path(path, cwd))

        return npaths

    def get_rel_path(self, path, cwd):
        key = cwd.lower() + " " + path.lower()
        npath = self.paths.get(key)

        if npath:
            return npath
        else:
            self.paths = self.load_paths()
            return self.paths[key]

    def get_abs_path(self, path):
        key = path.lower()
        npath = self.paths.get(key)

        if npath:
            return npath
        else:
            self.paths = self.load_paths()
            return self.paths[key]

    def dump_paths(self):
        os.makedirs(os.path.dirname(self.paths_file), exist_ok=True)

        paths = self.load_paths()
        paths.update(self.paths)

        with open(self.paths_file, "a") as paths_fh:
            for path in paths:
                paths_fh.write("{}: {}\n".format(path, paths[path]))

    def load_paths(self):
        paths = dict()

        if os.path.exists(self.paths_file):
            with open(self.paths_file, "r") as paths_fh:
                for line in paths_fh:
                    m = re.search(r"(.*): (.*)", line)
                    if m:
                        paths[m.group(1)] = m.group(2)

        return paths

    def normalize_rel_paths(self, paths, cwd):
        # TODO: check that paths is a list, not a string
        npaths = []

        for path in paths:
            npaths.append(self.normalize_rel_path(path, cwd))

        return npaths

    def normalize_rel_path(self, path, cwd, cache=dict()):
        # cache variable considerably speeds up normalizing.
        # cache size is quite small even for extra large files.

        key = cwd.lower() + " " + path.lower()

        if key in cache:
            # I am not shure why it is necessary
            # But sometimes cache variable is preserved through different launches
            self.paths[key] = cache[key]
            return cache[key]

        if not os.path.isabs(path):
            abs_path = os.path.join(cwd, path)
        else:
            abs_path = path

        npath = self.normalize_abs_path(abs_path)
        cache[key] = npath
        self.paths[key] = npath
        return npath

    def normalize_abs_path(self, path, cache=dict()):
        if path in cache:
            return cache[path]

        npath = os.path.normpath(path)

        if sys.platform == "win32":
            npath = self.__get_actual_filename(npath)
            npath = npath.replace("\\", "/")
            drive, tail = os.path.splitdrive(npath)
            if drive:
                npath = "/" + drive[:-1] + tail

        cache[path] = npath
        self.paths[path.lower()] = npath
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
