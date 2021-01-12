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

try:
    import cchardet as chardet
except ImportError:
    import chardet

import functools
import os
import shutil
import tempfile

from clade.extensions.abstract import Extension


class Storage(Extension):
    requires = ["Path"]

    __version__ = "1"

    @Extension.prepare
    def parse(self, cmds_file):
        files_to_add = self.conf.get("Storage.files_to_add", [])

        if files_to_add:
            self.log("Saving files")

        for file in files_to_add:
            file = os.path.abspath(file)
            self.debug("Saving {!r} to the Storage".format(file))

            if not os.path.exists(file):
                self.error(
                    "File does not exist: {!r}".format(file)
                )
                raise RuntimeError

            if os.path.isfile(file):
                self.add_file(file)
                continue

            for root, _, filenames in os.walk(file):
                for filename in filenames:
                    filename = os.path.join(root, filename)
                    if not filename.startswith(self.clade_work_dir):
                        self.add_file(filename)

    def add_file(self, filename, storage_filename=None, encoding=None):
        """Add file to the storage.

        Args:
            filename: Path to the file
            storage_filename: Name by which the file will be stored
            encoding: encoding of the file, which may be required if you want
                      to convert it to UTF-8 using 'Storage.convert_to_utf8'
                      option
        """

        storage_filename = (
            storage_filename
            if storage_filename
            else self.extensions["Path"].normalize_abs_path(filename)
        )

        dst = os.path.normpath(self.work_dir + os.sep + storage_filename)

        if self.__path_exists(dst):
            return

        try:
            self.__copy_file(filename, dst, encoding=encoding)
        except FileNotFoundError as e:
            self.debug(e)
        except (PermissionError, OSError) as e:
            self.log(e)
        except shutil.SameFileError:
            pass

        return dst

    @functools.lru_cache(maxsize=30000)
    def __path_exists(self, path):
        return os.path.exists(path)

    def __copy_file(self, filename, dst, encoding=None):
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        if not self.conf.get("Storage.convert_to_utf8"):
            self.debug("Storing {!r}".format(filename))
            shutil.copyfile(filename, dst)
        else:
            with open(filename, "rb") as fh:
                content_bytes = fh.read()

            if not encoding:
                detected = chardet.detect(content_bytes)
                encoding = detected["encoding"]
                confidence = detected["confidence"]
            else:
                # Encoding is specified by the user
                confidence = 1

            if not confidence:
                self.warning(
                    "Can't confidently detect encoding of {!r}.".format(
                        filename
                    )
                )
                shutil.copyfile(filename, dst)
                return

            self.debug("Trying to store {!r}. Detected encoding: {} (confidence = {})".format(
                filename, encoding, confidence
            ))

            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False
            ) as f:
                # Encode file content to utf-8
                try:
                    content_bytes = content_bytes.decode(
                        encoding,
                        self.conf.get("Storage.decoding_errors", "strict")
                    ).encode("utf-8")
                except UnicodeDecodeError:
                    # If user-specified encoding failed, try automatic detection
                    if confidence == 1:
                        self.__copy_file(filename, dst)
                    # else: raise original exception
                    else:
                        raise

                # Convert CRLF line endings to LF
                content_bytes = content_bytes.replace(b"\r\n", b"\n")
                f.write(content_bytes)

            try:
                shutil.copymode(filename, f.name)
            except Exception:
                self.warning("Couldn't set permissions for {!r}".format(filename))

            try:
                os.replace(f.name, dst)
            except OSError:
                os.remove(f.name)

    def get_storage_dir(self):
        return self.work_dir

    def get_storage_path(self, path) -> str:
        """Get path to the file or directory from the storage."""
        path = os.path.normpath(path)
        return os.path.join(self.work_dir, path.lstrip(os.path.sep))
