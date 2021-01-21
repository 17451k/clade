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
import subprocess

from clade.abstract import Intercept

LIB = os.path.join(os.path.dirname(__file__), "intercept", "lib")
LIB64 = os.path.join(os.path.dirname(__file__), "intercept", "lib64")


class Debugger(Intercept):
    def __init__(self, command, cwd=os.getcwd(), output="cmds.txt", append=False, intercept_open=False, conf=None):
        if intercept_open:
            raise RuntimeError("debugger can't be used to intercept open()")

        super().__init__(command, cwd=cwd, output=output, append=append, intercept_open=intercept_open, conf=conf)

        # self.conf["Intercept.preprocess"] = self.conf.get("Intercept.preprocess", True)
        self.debugger = self.__find_debugger()

    def __find_debugger(self):
        debugger = os.path.join(os.path.dirname(__file__), "intercept", "debugger.exe")

        if not os.path.exists(debugger):
            raise RuntimeError("debugger is not found in {!r}".format(debugger))

        self.logger.debug("Path to the debugger: {!r}".format(debugger))

        return debugger

    @Intercept.preprocess
    def execute(self):
        self.command.insert(0, self.debugger)
        self.logger.debug("Execute {!r} command".format(self.command))
        return subprocess.call(self.command, env=self.env, shell=False, cwd=self.cwd)
