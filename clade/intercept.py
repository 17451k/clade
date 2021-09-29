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
import sys

from clade.debugger import Debugger
from clade.libinterceptor import Libinterceptor
from clade.wrapper import Wrapper


def intercept(command, cwd=os.getcwd(), output="cmds.txt", append=False, conf=None, use_wrappers=True, intercept_open=False, intercept_envs=False):
    if sys.platform in ["linux", "darwin"] and use_wrappers:
        cl = Wrapper
    elif sys.platform in ["linux", "darwin"] and not use_wrappers:
        cl = Libinterceptor
    elif sys.platform == "win32":
        cl = Debugger
    else:
        sys.exit("Your platform {!r} is not supported yet.".format(sys.platform))

    i = cl(command=command, cwd=cwd, output=output, append=append, intercept_open=intercept_open, intercept_envs=intercept_envs, conf=conf)
    return i.execute()
