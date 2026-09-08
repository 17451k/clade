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
import setuptools
import shutil
import subprocess
import sys
import tempfile

from setuptools import dist
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py

LIBINT_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "clade", "intercept")
)
LIB = os.path.join(LIBINT_SRC, "lib")
LIB64 = os.path.join(LIBINT_SRC, "lib64")


def build_target(target, build_dir, src_dir, options=None, quiet=False):
    if not options:
        options = []

    # CentOS has 2 different cmake packages: cmake2 and cmake3
    # Executable named "cmake" can point to cmake2 package,
    # which is unsupported by Clade, so we need to try cmake3 first
    if shutil.which("cmake3"):
        cmake = "cmake3"
    else:
        cmake = "cmake"

    if not shutil.which(cmake):
        raise RuntimeError("Can't find cmake")

    os.makedirs(build_dir, exist_ok=True)

    try:
        subprocess.check_output(
            [cmake, src_dir] + options,
            stderr=subprocess.STDOUT,
            cwd=build_dir,
            universal_newlines=True,
        )
        subprocess.check_output(
            [
                cmake,
                "--build",
                ".",
                "--target",
                target,
                "--config",
                "Release",
            ],
            stderr=subprocess.STDOUT,
            cwd=build_dir,
            universal_newlines=True,
        )
    except subprocess.CalledProcessError as e:
        if not quiet:
            print(e.output)
        raise RuntimeError(
            "Can't build target {!r} - something went wrong".format(target)
        )


def build_wrapper(build_dir):
    build_target("wrapper", build_dir, LIBINT_SRC)

    shutil.copy(os.path.join(build_dir, "unix", "wrapper"), LIBINT_SRC)


def build_interceptor(build_dir):
    build_target("interceptor", build_dir, LIBINT_SRC)

    for file in glob.glob(os.path.join(build_dir, "unix", "libinterceptor.*")):
        shutil.copy(file, LIBINT_SRC)


def build_multilib(build_dir):
    try:
        build_interceptor64(os.path.join(build_dir, "libinterceptor64"))
        build_interceptor32(os.path.join(build_dir, "libinterceptor32"))
    except RuntimeError:
        # Multilib build is not mandatory
        pass


def build_interceptor64(build_dir):
    options = ["-DCMAKE_C_COMPILER_ARG1=-m64"]
    build_target("interceptor", build_dir, LIBINT_SRC, options, quiet=True)

    os.makedirs(LIB64, exist_ok=True)
    for file in glob.glob(os.path.join(build_dir, "unix", "libinterceptor.*")):
        shutil.copy(file, LIB64)


def build_interceptor32(build_dir):
    options = ["-DCMAKE_C_COMPILER_ARG1=-m32"]
    build_target("interceptor", build_dir, LIBINT_SRC, options, quiet=True)

    os.makedirs(LIB, exist_ok=True)
    for file in glob.glob(os.path.join(build_dir, "unix", "libinterceptor.*")):
        shutil.copy(file, LIB)


def build_debugger(build_dir):
    options = ["-DCMAKE_GENERATOR_PLATFORM=x64"]
    build_target("debugger", build_dir, LIBINT_SRC, options)

    copy_from = os.path.join(build_dir, "windows", "Release", "debugger.exe")
    shutil.copy(copy_from, LIBINT_SRC)


def build_libinterceptor():
    build_dir = tempfile.mkdtemp()

    try:
        if sys.platform == "linux":
            build_wrapper(build_dir)
            build_interceptor(build_dir)
            build_multilib(build_dir)
        elif sys.platform == "darwin":
            build_wrapper(build_dir)
            build_interceptor(build_dir)
        elif sys.platform == "win32":
            build_debugger(build_dir)
        else:
            exit("Your platform {!r} is not supported yet.".format(sys.platform))
    finally:
        shutil.rmtree(build_dir)


# build_py is the only build step that both wheel and PEP 660 editable
# installs are guaranteed to run, and it runs before package data is
# collected, so the artifacts it produces end up in the wheel
class CustomBuildPy(build_py):
    def run(self):
        build_libinterceptor()
        super().run()


class CustomBdistWheel(bdist_wheel):
    def get_tag(self):
        # The bundled binaries are loaded by the OS, not imported by CPython,
        # so the wheel is platform-specific but works with any Python 3
        _, _, plat = super().get_tag()
        return "py3", "none", plat


class CustomDist(dist.Distribution):
    def is_pure(self):
        return False

    def has_ext_modules(self):
        return True


setuptools.setup(
    cmdclass={"bdist_wheel": CustomBdistWheel, "build_py": CustomBuildPy},
    distclass=CustomDist,
)
