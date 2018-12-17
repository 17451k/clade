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
import re
import tempfile

from distutils.command.build import build
from setuptools.command.develop import develop


LIBINT_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "clade", "libinterceptor"))
LIB = os.path.join(LIBINT_SRC, "lib")
LIB64 = os.path.join(LIBINT_SRC, "lib64")


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


def package_files(package_directory):
    paths = []

    for (path, _, filenames) in os.walk(package_directory):
        for filename in filenames:
            paths.append(os.path.relpath(os.path.join(path, filename), start=package_directory))

    return paths


class CustomBuild(build):
    def run(self):
        if sys.platform == "linux" or sys.platform == "darwin":
            build_libinterceptor()
        else:
            raise NotImplementedError("clade is not yet supported on your platform ({})".format(sys.platform))
        super().run()

    def finalize_options(self):
        super().finalize_options()


class CustomDevelop(develop):
    def run(self):
        if sys.platform == "linux" or sys.platform == "darwin":
            build_libinterceptor()
        else:
            raise NotImplementedError("clade is not yet supported on your platform ({})".format(sys.platform))
        super().run()


try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

    class bdist_wheel(_bdist_wheel):
        def finalize_options(self):
            _bdist_wheel.finalize_options(self)
            # Mark us as not a pure python package
            self.root_is_pure = False
except ImportError:
    bdist_wheel = None

setuptools.setup(
    name="clade",
    version="2.1",
    author="Ilya Shchepetkov",
    author_email="ilya.shchepetkov@yandex.ru",
    url="https://github.com/17451k/clade",
    license="LICENSE.txt",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    python_requires=">=3.4",
    packages=["clade"],
    package_data={
        "clade": package_files("clade"),
    },
    entry_points={
        "console_scripts": [
            "clade-intercept=clade.intercept:main",
            "clade-cmds-stats=clade.cmds:print_cmds_stats",
            "clade-cc=clade.extensions.cc:main",
            "clade-ld=clade.extensions.ld:main",
            "clade-objcopy=clade.extensions.objcopy:main",
            "clade-mv=clade.extensions.mv:main",
            "clade-pid-graph=clade.extensions.pid_graph:main",
            "clade-cmd-graph=clade.extensions.cmd_graph:main",
            "clade-src-graph=clade.extensions.src_graph:main",
            "clade-info=clade.extensions.info:main",
            "clade-callgraph=clade.extensions.callgraph:main",
            "clade-functions=clade.extensions.functions:main",
            "clade-variables=clade.extensions.variables:main",
            "clade-macros=clade.extensions.macros:main",
            "clade-typedefs=clade.extensions.typedefs:main",
            "clade-ar=clade.extensions.ar:main",
            "clade-as=clade.extensions.assembler:main",
            "clade-execute=clade.extensions.execute:main",
            "clade-all=clade:main",
            "clade=clade.extensions.cdb:main"
        ],
    },
    cmdclass={"build": CustomBuild, "develop": CustomDevelop, 'bdist_wheel': bdist_wheel},
    install_requires=["ujson", "graphviz", "ply", "pytest"],
    classifiers=(
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Unix",
    )
)
