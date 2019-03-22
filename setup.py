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

from distutils.command.build import build
from setuptools.command.develop import develop


LIBINT_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "clade", "intercept")
)
LIB = os.path.join(LIBINT_SRC, "lib")
LIB64 = os.path.join(LIBINT_SRC, "lib64")


def build_target(target, build_dir, src_dir, options=None, quiet=False):
    if not options:
        options = []

    os.makedirs(build_dir, exist_ok=True)

    try:
        subprocess.check_output(
            ["cmake", src_dir] + options,
            stderr=subprocess.STDOUT,
            cwd=build_dir,
            universal_newlines=True,
        )
        subprocess.check_output(
            [
                "cmake",
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
            exit(
                "Your platform {!r} is not supported yet.".format(sys.platform)
            )
    finally:
        shutil.rmtree(build_dir)


def package_files(package_directory):
    paths = []

    for (path, _, filenames) in os.walk(package_directory):
        for filename in filenames:
            paths.append(
                os.path.relpath(
                    os.path.join(path, filename), start=package_directory
                )
            )

    # Add files created on the build step
    paths.extend(
        [
            os.path.join("intercept", "libinterceptor.so"),
            os.path.join("intercept", "lib", "libinterceptor.so"),
            os.path.join("intercept", "lib64", "libinterceptor.so"),
            os.path.join("intercept", "wrapper"),
            os.path.join("intercept", "debugger.exe"),
        ]
    )

    return paths


class CustomBuild(build):
    def run(self):
        build_libinterceptor()
        super().run()

    def finalize_options(self):
        super().finalize_options()


class CustomDevelop(develop):
    def run(self):
        build_libinterceptor()
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
    version="3.0",
    author="Ilya Shchepetkov",
    author_email="shchepetkov@ispras.ru",
    url="https://github.com/17451k/clade",
    license="LICENSE.txt",
    long_description=open("README.rst", encoding="utf8").read(),
    python_requires=">=3.4",
    packages=["clade"],
    package_data={"clade": package_files("clade")},
    entry_points={
        "console_scripts": [
            "clade-intercept=clade.intercept:intercept_main",
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
            "clade-cl=clade.extensions.cl:main",
            "clade-link=clade.extensions.link:main",
            "clade-all=clade:parse_all_main",
            "clade=clade.extensions.cdb:main",
            "clade-diff=clade.diff:main",
        ]
    },
    cmdclass={
        "build": CustomBuild,
        "develop": CustomDevelop,
        "bdist_wheel": bdist_wheel,
    },
    install_requires=["ujson", "cchardet", "graphviz", "ply"],
    extras_require={"dev": ["pytest", "pytest-profiling"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
)
