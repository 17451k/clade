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
import setuptools
import shutil
import subprocess
import sys
import re
import tempfile

from distutils.command.build import build
from setuptools.command.develop import develop


def build_libinterceptor():
    try:
        build_dir = os.path.join(tempfile.gettempdir(), "clade-build")
        libint_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "clade", "libinterceptor"))

        if not os.path.exists(build_dir):
            os.makedirs(build_dir)

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
    version="1.0",
    author="Ilya Shchepetkov",
    author_email="ilya.shchepetkov@yandex.ru",
    url="https://github.com/17451k/clade",
    license="LICENSE.txt",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    packages=["clade"],
    package_data={
        "clade": ["libinterceptor/*"],
    },
    entry_points={
        "console_scripts": [
            "clade-intercept=clade.intercept:main",
            "clade-cmds-stats=clade.cmds:print_cmds_stats",
        ],
    },
    cmdclass={"build": CustomBuild, "develop": CustomDevelop, 'bdist_wheel': bdist_wheel},
    install_requires=["ujson"],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Unix",
    )
)
