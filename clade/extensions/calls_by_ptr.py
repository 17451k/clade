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

from clade.extensions.abstract import Extension
from clade.types.nested_dict import nested_dict


class CallsByPtr(Extension):
    requires = ["Info"]

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        super().__init__(work_dir, conf)

        self.calls_by_ptr = nested_dict()
        self.calls_by_ptr_file = "calls_by_ptr.json"

    @Extension.prepare
    def parse(self, cmds_file):
        self.log("Parsing calls by pointers")

        for context_file, context_func, func_ptr, call_line in self.extensions[
            "Info"
        ].iter_calls_by_pointers():
            self.debug(
                "Processing calls by pointers: "
                + " ".join([context_file, context_func, func_ptr, call_line])
            )

            if func_ptr not in self.calls_by_ptr[context_file][context_func]:
                self.calls_by_ptr[context_file][context_func][func_ptr] = [call_line]
            else:
                self.calls_by_ptr[context_file][context_func][func_ptr].append(
                    call_line
                )

        self.dump_data(self.calls_by_ptr, self.calls_by_ptr_file)

    def load_calls_by_ptr(self):
        return self.load_data(self.calls_by_ptr_file)
