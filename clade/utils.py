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
import subprocess
import sys
import re
import tempfile


def build_libinterceptor():
    try:
        build_dir = tempfile.mkdtemp()
        libint_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "libinterceptor"))

        os.makedirs(build_dir, exist_ok=True)

        try:
            ret = subprocess.call(["cmake", libint_src], cwd=build_dir)
            ret += subprocess.call(["make"], cwd=build_dir)
        except FileNotFoundError as e:
            # cmd is either cmake or make
            cmd = re.sub(r".*? '(.*)'", r"\1", e.args[1])
            raise OSError("{} is not installed on your system - please fix it".format(cmd), e.args[0])

        if ret:
            raise sys.exit("Can't build libinterceptor - something went wrong")
    finally:
        shutil.rmtree(build_dir)
