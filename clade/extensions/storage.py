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
import shutil

from clade.extensions.abstract import Extension


class Storage(Extension):
    def add_file(self, filename, storage_filename=None, cache=set()):
        """Add file to the storage."""

        dst = self.work_dir + os.sep + (storage_filename if storage_filename else filename)

        if dst in cache:
            return
        else:
            cache.add(dst)

        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(filename, dst)
        except FileNotFoundError as e:
            self.warning(e)
        except shutil.SameFileError:
            pass

    def get_storage_dir(self):
        return self.work_dir

    def parse(self, cmd_file):
        super().parse(cmd_file)
