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

from clade.extensions.abstract import Extension
from clade.extensions.utils import Location


class CommonInfo(Extension):
    """Parent class for extensions that parse output of Info extension"""

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.warn_log = os.path.join(self.work_dir, "warnings.log")
        self.warn_dir = os.path.join(self.work_dir, "warnings")

    def _warning(self, msg, file=None):
        """Print a warning message."""
        self.debug(msg)

        os.makedirs(self.work_dir, exist_ok=True)

        with open(self.warn_log, "a") as err_fh:
            err_fh.write("{}\n".format(msg))

        # If file specified, then also print the message to separate file log
        if file:
            self._warning_by_file(msg, file)

    def _warning_by_file(self, msg, file):
        """Print a warning message separately for each file."""
        path = os.path.join(self.work_dir, self.warn_dir + file + ".log")

        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "a") as err_fh:
            err_fh.write(f"{msg}\n")

    def _clean_warn_log(self):
        """Remove duplicate warning messages."""

        log_files = self.__find_log_files()

        if len(log_files) > 1:
            self.log(f"Cleaning {len(log_files)} log files")

        for log_file in log_files:
            if not os.path.isfile(log_file):
                return

            dup_lines = dict()

            with open(log_file, "r") as output_fh:
                for line in output_fh:
                    line = line.strip()
                    if line not in dup_lines:
                        dup_lines[line] = 1
                    else:
                        dup_lines[line] += 1

            # Print back clean and sorted log
            with open(log_file, "w") as output_fh:
                for line, times in sorted(
                    dup_lines.items(), key=lambda item: item[1], reverse=True
                ):
                    if times > 1:
                        output_fh.write(line + f" ({times} times)\n")
                    else:
                        output_fh.write(line + "\n")

    def __find_log_files(self):
        log_files = [self.warn_log]

        for root, _, filenames in os.walk(self.warn_dir):
            for filename in filenames:
                log_files.append(os.path.join(root, filename))

        return log_files

    def _in_the_same_file(self, definition, context_definition):
        return (
            definition["file"] == context_definition["file"]
            and context_definition["compiled_in"][0] in definition["compiled_in"]
        )

    def _in_the_same_tu(self, definition, context_definition):
        return context_definition["compiled_in"][0] in definition["compiled_in"]

    def _definition_is_exported(self, definition, context_definition):
        return (
            definition["type"] == "exported" and context_definition["type"] == "extern"
        )

    def _definition_is_linked(self, definition, context_definition):
        context_location = Location(
            context_definition["file"], context_definition["compiled_in"][0]
        )

        for cmd_id in definition["compiled_in"]:
            location = Location(definition["file"], cmd_id)

            if not self._files_are_linked(location, context_location):
                continue

            for declaration in definition["declarations"]:
                for decl_cmd_id in declaration["compiled_in"]:
                    # Declaration is included in the call file
                    if decl_cmd_id == context_location.cmd_id:
                        return True

        self.debug(
            f"{definition['file']!r} and {context_definition['file']!r} are not linked"
        )
        return False

    def _declaration_is_in_the_same_tu(self, definition, context_definition):
        context_location = Location(
            context_definition["file"], context_definition["compiled_in"][0]
        )

        for declaration in definition["declarations"]:
            for cmd_id in declaration["compiled_in"]:
                # Declaration is included in the call file
                if cmd_id == context_location.cmd_id:
                    return True

        self.debug(
            f"{definition['file']!r} and {context_definition['file']!r} are not in the same tu"
        )
        return False

    def _files_are_linked(self, loc1: Location, loc2: Location):
        if loc1 == Location("unknown", "0") or loc2 == Location("unknown", "0"):
            return False

        if not self.extensions["SrcGraph"].in_source_graph(loc1.file, loc1.cmd_id):
            self._warning(f"{loc1.file} was not compiled in {loc1.cmd_id}")

        if not self.extensions["SrcGraph"].in_source_graph(loc2.file, loc2.cmd_id):
            self._warning(f"{loc2.file} was not compiled in {loc2.cmd_id}")

        return (
            len(
                set(self.extensions["SrcGraph"].get_used_by(loc1.file, loc1.cmd_id))
                & set(self.extensions["SrcGraph"].get_used_by(loc2.file, loc2.cmd_id))
            )
            > 0
        )
