# Copyright (c) 2020 ISP RAS (http://www.ispras.ru)
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


class PathTree:
    KEY = "__val__"

    def __init__(self):
        self.data = dict()

    def __setitem__(self, key: str, value):
        data = self.data

        for new_key in key.split("/"):
            if not new_key:
                continue

            data = self.__get_or_create(data, new_key, dict())

        data[self.KEY] = value

    def __getitem__(self, key):
        return self.__get_or_create(self.__getitem_deep(key), self.KEY, None)

    def __getitem_deep(self, key):
        data = self.data

        for new_key in key.split("/"):
            if not new_key:
                continue

            data = data[new_key]

        return data

    def __get_or_create(self, data, key, value=None):
        if key not in data:
            data[key] = value

        return data[key]

    def __contains__(self, key):
        return self.get(key) is not None

    def __iter__(self):
        yield from self.__deep_iter()

    def __deep_iter(self, k=""):
        data = self.__getitem_deep(k)

        for key in data:
            if key == self.KEY:
                yield k
                continue

            if k:
                yield from self.__deep_iter(k + "/" + key)
            else:
                yield from self.__deep_iter("/" + key)

    def keys(self):
        return [x for x in self.__deep_iter()]

    def update(self, path_tree):
        raise NotImplementedError

        # if path_tree contains "/usr", and self contains "/usr/local" paths
        # then the following line of code will overwrite it:
        # self.data.update(path_tree.data)
        # TODO: fix it

    def get(self, key, default_value=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default_value
