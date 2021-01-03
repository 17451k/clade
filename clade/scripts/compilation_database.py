# Copyright (c) 2019 ISP RAS (http://www.ispras.ru)
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
import shutil
import sys
import tempfile
import ujson

from clade import Clade


def parse_args(args, work_dir):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-o",
        "--output",
        help="path to the FILE where compilation database will be saved",
        metavar="FILE",
        default="compile_commands.json",
    )
    parser.add_argument(
        "-w",
        "--wrappers",
        help="enable intercepting mode based on wrappers (not available on Windows)",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="path to the JSON file with configuration",
        metavar="JSON",
        default=None,
    )
    parser.add_argument(
        "-p",
        "--preset",
        help="name of the preset configuration",
        metavar="NAME",
        default="base",
    )
    parser.add_argument(
        "--cmds",
        help="path to the file with intercepted commands",
    )
    parser.add_argument(
        dest="command", nargs=argparse.REMAINDER, help="build command to run"
    )

    args = parser.parse_args(args)

    if not args.command and not args.cmds:
        sys.exit("Build command is missing")

    if not args.cmds:
        args.cmds = os.path.join(work_dir, "cmds.txt")

    return args


def prepare_conf(args):
    conf = dict()

    if args.config:
        try:
            with open(args.config, "r") as f:
                conf = ujson.load(f)
        except FileNotFoundError:
            print("Configuration file is not found")
            sys.exit(-1)

    conf["log_level"] = "ERROR"
    conf["preset"] = args.preset
    conf["CDB.output"] = os.path.abspath(args.output)

    return conf


def main(args=sys.argv[1:]):
    work_dir = tempfile.mkdtemp()
    args = parse_args(args, work_dir)
    conf = prepare_conf(args)

    conf["SrcGraph.requires"] = ["CC", "CL", "CXX"]

    try:
        c = Clade(work_dir, args.cmds, conf, args.preset)
    except RuntimeError as e:
        raise SystemExit(e)

    if args.command and not os.path.isfile(args.cmds):
        c.intercept(args.command, use_wrappers=args.wrappers)

    if not os.path.exists(args.cmds):
        print("Something is wrong: file with intercepted commands is empty")
        sys.exit(-1)

    c.parse("CDB")

    shutil.rmtree(work_dir)


if __name__ == "__main__":
    main(sys.argv[1:])
