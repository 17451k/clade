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

import glob
import os
import shutil
import subprocess
import sys
import re
import tempfile

from clade.intercept import LIB, LIB64


LIBINT_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "libinterceptor"))


def build_target(target, build_dir, src_dir, options=None, quiet=False):
    if not options:
        options = []

    os.makedirs(build_dir, exist_ok=True)

    try:
        subprocess.check_output(["cmake", src_dir] + options, stderr=subprocess.STDOUT, cwd=build_dir, universal_newlines=True)
        subprocess.check_output(["make", target], stderr=subprocess.STDOUT, cwd=build_dir, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        if not quiet:
            print(e.output)
        raise RuntimeError("Can't build target {!r} - something went wrong".format(target))


def build_all(build_dir):
    build_target("all", build_dir, LIBINT_SRC)

    shutil.copy(os.path.join(build_dir, "wrapper"), LIBINT_SRC)

    for file in glob.glob(os.path.join(build_dir, "libinterceptor.*")):
        shutil.copy(file, LIBINT_SRC)


def build_multilib(build_dir):
    try:
        build_libinterceptor64(os.path.join(build_dir, "libinterceptor64"))
        build_libinterceptor32(os.path.join(build_dir, "libinterceptor32"))
    except RuntimeError:
        # Multilib build is not mandatory
        pass


def build_libinterceptor64(build_dir):
    build_target("interceptor", build_dir, LIBINT_SRC, ["-DCMAKE_C_COMPILER_ARG1=-m64"], quiet=True)

    os.makedirs(LIB64, exist_ok=True)
    for file in glob.glob(os.path.join(build_dir, "libinterceptor.*")):
        shutil.copy(file, LIB64)


def build_libinterceptor32(build_dir):
    build_target("interceptor", build_dir, LIBINT_SRC, ["-DCMAKE_C_COMPILER_ARG1=-m32"], quiet=True)

    os.makedirs(LIB, exist_ok=True)
    for file in glob.glob(os.path.join(build_dir, "libinterceptor.*")):
        shutil.copy(file, LIB)


def build_libinterceptor():
    try:
        build_dir = tempfile.mkdtemp()

        try:
            build_all(build_dir)
            if not sys.platform == "darwin":
                build_multilib(build_dir)
        except FileNotFoundError as e:
            # cmd is either cmake or make
            cmd = re.sub(r".*? '(.*)'", r"\1", e.args[1])
            raise OSError("{!r} is not installed on your system - please fix it".format(cmd), e.args[0])
    finally:
        shutil.rmtree(build_dir)
