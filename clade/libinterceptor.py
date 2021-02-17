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
import sys

from clade.abstract import Intercept

LIB = os.path.join(os.path.dirname(__file__), "intercept", "lib")
LIB64 = os.path.join(os.path.dirname(__file__), "intercept", "lib64")


class Libinterceptor(Intercept):
    def _setup_env(self):
        env = super()._setup_env()

        libinterceptor = self.__find_libinterceptor()

        if sys.platform == "darwin":
            self.logger.debug("Set 'DYLD_INSERT_LIBRARIES' environment variable value")
            env["DYLD_INSERT_LIBRARIES"] = libinterceptor
            env["DYLD_FORCE_FLAT_NAMESPACE"] = "1"
        elif sys.platform == "linux":
            existing_preload = env.get("LD_PRELOAD")
            env["LD_PRELOAD"] = libinterceptor

            if existing_preload:
                env["LD_PRELOAD"] += " " + existing_preload

            existing_lpath = env.get("LD_LIBRARY_PATH")
            env["LD_LIBRARY_PATH"] = LIB64 + ":" + LIB

            if existing_lpath:
                env["LD_LIBRARY_PATH"] += ":" + existing_lpath

            self.logger.debug("Set 'LD_PRELOAD' environment variable value as {!r}".format(env["LD_PRELOAD"]))
            self.logger.debug("Set LD_LIBRARY_PATH environment variable value as {!r}".format(env["LD_LIBRARY_PATH"]))

        return env

    def __find_libinterceptor(self):
        if sys.platform == "linux":
            libinterceptor_name = "libinterceptor.so"
        elif sys.platform == "darwin":
            libinterceptor_name = "libinterceptor.dylib"
        else:
            raise NotImplementedError("Libinterceptor doesn't work on {!r}".format(sys.platform))

        libinterceptor = os.path.join(os.path.dirname(__file__), "intercept", libinterceptor_name)

        if not os.path.exists(libinterceptor):
            raise RuntimeError("libinterceptor is not found in {!r}".format(libinterceptor))

        # Multilib support, Linux only
        path = os.path.join(LIB, libinterceptor_name)
        path64 = os.path.join(LIB64, libinterceptor_name)

        if os.path.exists(path) and os.path.exists(path64):
            libinterceptor = libinterceptor_name
            self.logger.debug("Path to libinterceptor library locations: {!r}, {!r}".format(path, path64))
        else:
            self.logger.debug("Path to libinterceptor library location: {!r}".format(libinterceptor))

        return libinterceptor

    @Intercept.preprocess
    def execute(self):
        return super().execute()
