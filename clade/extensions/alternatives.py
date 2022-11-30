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

import hashlib
import itertools
import os

from typing import List
from clade.extensions.abstract import Extension


class Alternatives(Extension):
    """
    This extension is responsible for parsing build commands that create
    "identical" file copies: ln, cp, install, etc. It provides an API
    for the following things:

    * getting all known alternative paths for a given file: all its
      symlinks, copies and hard links.
    * getting a canonical representation for a given path, which will be
      the same for all identical files.

    Alternatives is a short from "alternative paths".
    """

    always_requires = ["Storage"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.requires = self.always_requires + self.conf.get("Alternatives.requires", [])

        self.alts = dict()
        self.alts_file = "alts.json"

    @Extension.prepare
    def parse(self, cmds_file):
        # Load all build commands that create "identical" file copies
        cmds = self.__load_cmds()

        if not cmds:
            return

        self.log(f"Parsing {len(cmds)} commands")

        for cmd in cmds:
            if not cmd["in"] or not cmd["out"] or len(cmd["in"]) != len(cmd["out"]):
                self.debug(
                    f"Command {cmd['id']} doesn't have symmetrical input and output files"
                )
                continue

            # For each input file, there should be a corresponding identical output file
            for i, cmd_in in enumerate(cmd["in"]):
                cmd_out = cmd["out"][i]

                # Sometimes there can be some false positives, for example,
                # because some ln commands overwrite files from the previous ones
                # Here we check that cmd_in is indeed the same file as cmd_out
                if (
                    not os.path.exists(cmd_in)
                    or not os.path.exists(cmd_out)
                    or self.__get_file_checksum(cmd_in)
                    != self.__get_file_checksum(cmd_out)
                ):
                    continue

                self.__add_pair(cmd_in, cmd_out)

                # Resolve possible symlinks
                real_cmd_in = os.path.realpath(cmd_in)
                if real_cmd_in != cmd_in:
                    self.__add_pair(real_cmd_in, cmd_in)

                real_cmd_out = os.path.realpath(cmd_out)
                if real_cmd_out != cmd_out:
                    self.__add_pair(real_cmd_out, cmd_out)

        # Convert sets to lists for json serialization
        for path in self.alts:
            self.alts[path] = list(self.alts[path])

        self.dump_data(self.alts, self.alts_file)

    def __add_pair(self, cmd_in, cmd_out):
        if cmd_in not in self.alts:
            self.alts[cmd_in] = set()

        if cmd_out not in self.alts:
            self.alts[cmd_out] = set()

        # Add output file as an identical for the input file
        # And vice versa
        self.alts[cmd_in].add(cmd_out)
        self.alts[cmd_out].add(cmd_in)

    def load_alternatives(self):
        return self.load_data(self.alts_file)

    def get_canonical_path(self, path):
        """Returns a canonical path for a given path

        For example. if "/lib/header.h" and "/lib/x86_64/header.h" files are the same,
        then:
            * get_canonical_path("/lib/header.h") == "/lib/header.h"
            * get_canonical_path("/lib/x86_64/header.h") == "/lib/header.h"
        """

        if not self.conf.get("Alternatives.use_canonical_paths"):
            return path

        paths = sorted(self.get_all_paths(path))

        # No alternatives
        if len(paths) == 1:
            return paths[0]

        # Try to return first path that exists
        for path in paths:
            if os.path.exists(self.extensions["Storage"].get_storage_path(path)):
                return path

        # Otherwise simply return the path itself
        return paths[0]

    def get_all_paths(self, paths):
        """Return list of all known paths for the ones provided as an input"""
        # Input parameter is a single path
        if isinstance(paths, str):
            return self.__get_all_paths(paths)

        # Otherwise it is a list of paths
        list_of_paths = [self.__get_all_paths(path) for path in paths]
        return list(itertools.chain.from_iterable(list_of_paths))

    def __get_all_paths(self, path: str) -> List[str]:
        if not self.alts and self.file_exists(self.alts_file):
            self.alts = self.load_alternatives()

        if path not in self.alts:
            return [path]

        return [path] + self.alts[path]

    def __load_cmds(self):
        cmds = list()

        for ext_name in self.extensions:
            if ext_name in self.always_requires:
                continue

            for cmd in self.extensions[ext_name].load_all_cmds():
                cmd["type"] = ext_name
                cmds.append(cmd)

        return cmds

    def __get_file_checksum(self, file):
        try:
            with open(file, "rb") as fh:
                return hashlib.md5(fh.read()).hexdigest()
        except FileNotFoundError:
            return None
