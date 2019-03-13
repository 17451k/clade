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

import argparse
import os
import sys

from clade.debugger import Debugger
from clade.libinterceptor import Libinterceptor
from clade.wrapper import Wrapper
from clade.extensions.utils import load_conf_file


def intercept(command, cwd=os.getcwd(), output="cmds.txt", append=False, conf=None, use_wrappers=True):
    if sys.platform in ["linux", "darwin"] and use_wrappers:
        cl = Wrapper
    elif sys.platform in ["linux", "darwin"] and not use_wrappers:
        cl = Libinterceptor
    elif sys.platform == "win32":
        cl = Debugger
    else:
        sys.exit("Your platform {!r} is not supported yet.".format(sys.platform))

    i = cl(command=command, cwd=cwd, output=output, append=append, conf=conf)
    return i.execute()


def intercept_main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", help="a path to the FILE where intercepted commands will be saved", metavar='FILE', default="cmds.txt")
    parser.add_argument("-w", "--wrappers", help="enable intercepting mode based on wrappers (not supported on Windows)", action="store_true")
    parser.add_argument("-a", "--append", help="append intercepted commands to existing cmds.txt file", action="store_true")
    parser.add_argument("-c", "--config", help="a path to the JSON file with configuration", metavar='JSON', default=None)
    parser.add_argument(dest="command", nargs=argparse.REMAINDER, help="build command to run and intercept")

    args = parser.parse_args(args)

    if not args.command:
        sys.exit("Build command is missing")

    sys.exit(intercept(command=args.command, output=args.output, append=args.append,
                       conf=load_conf_file(args.config), use_wrappers=args.wrappers))
