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

import cchardet
import functools
import os
import shutil
import tempfile

from clade.extensions.abstract import Extension


class Storage(Extension):
    requires = ["Path"]

    __version__ = "1"

    def add_file(self, filename, storage_filename=None):
        """Add file to the storage."""

        storage_filename = (
            storage_filename
            if storage_filename
            else self.extensions["Path"].normalize_abs_path(filename)
        )

        dst = self.work_dir + os.sep + storage_filename

        if self.__path_exists(dst):
            return

        try:
            self.__copy_file(filename, dst)
        except FileNotFoundError as e:
            self.debug(e)
        except shutil.SameFileError:
            pass

    @functools.lru_cache(maxsize=30000)
    def __path_exists(self, path):
        return os.path.exists(path)

    def __copy_file(self, filename, dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        if not self.conf.get("Storage.convert_to_utf8"):
            shutil.copyfile(filename, dst)
        else:
            with open(filename, "rb") as fh:
                content_bytes = fh.read()

            detected = cchardet.detect(content_bytes)
            encoding = detected["encoding"]
            confidence = detected["confidence"]

            if not confidence:
                self.warning(
                    "Can't confidently detect encoding of {!r}.".format(
                        filename
                    )
                )
                shutil.copyfile(filename, dst)
                return

            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False
            ) as f:
                f.write(content_bytes.decode(encoding).encode("utf-8"))

            try:
                os.replace(f.name, dst)
            except OSError:
                os.remove(f.name)

    def get_storage_dir(self):
        return self.work_dir

    def get_storage_path(self, path):
        """Get path to the file or directory from the storage."""
        return os.path.join(self.work_dir, path.lstrip(os.path.sep))

    def parse(self, cmd_file):
        super().parse(cmd_file)
