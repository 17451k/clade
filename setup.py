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

import setuptools
import sys

from distutils.command.build import build
from setuptools.command.develop import develop

from clade.utils import build_libinterceptor


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
    version="2.0",
    author="Ilya Shchepetkov",
    author_email="ilya.shchepetkov@yandex.ru",
    url="https://github.com/17451k/clade",
    license="LICENSE.txt",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    python_requires=">=3.4",
    packages=["clade"],
    package_data={
        "clade": [
            "libinterceptor/*",
            "libinterceptor/lib/*",
            "libinterceptor/lib64/*",
            "extensions/*",
            "extensions/info/*",
            "extensions/presets/*"
        ],
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
            "clade-all=clade.interface:main",
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
