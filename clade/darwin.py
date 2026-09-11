# Copyright (c) 2026 ISP RAS (http://www.ispras.ru)
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


def setup_env(env):
    # /usr/bin tools are xcode-select shims: Apple platform binaries that ignore
    # DYLD_INSERT_LIBRARIES and strip it from the environment of their children.
    # Real tools live in the developer directory and need SDKROOT, which the
    # shims would have set.
    dev_dir = subprocess.check_output(["xcode-select", "-p"], text=True).strip()
    bin_dirs = [
        os.path.join(dev_dir, "usr", "bin"),
        os.path.join(dev_dir, "Toolchains", "XcodeDefault.xctoolchain", "usr", "bin"),
    ]
    env["CLADE_XCODE_PATH"] = os.pathsep.join(d for d in bin_dirs if os.path.isdir(d))

    if "SDKROOT" not in env:
        env["SDKROOT"] = subprocess.check_output(
            ["xcrun", "--show-sdk-path"], text=True
        ).strip()


def resolve_shim(name, env):
    which = shutil.which(name, path=env["PATH"])

    if which and which.startswith("/usr/bin/"):
        return (
            shutil.which(os.path.basename(which), path=env["CLADE_XCODE_PATH"]) or which
        )

    return which or name
