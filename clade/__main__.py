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
import datetime
import os
import sys
import time
import ujson

from clade import Clade
from clade.utils import get_clade_version


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-w",
        "--work-dir",
        help="path to the directory where all Clade data will be saved",
        metavar="DIR",
        default="clade",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        help="set logging level (ERROR, INFO, or DEBUG)",
        metavar="LEVEL",
        default="INFO",
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
        "-e",
        "--extension",
        help="extension to launch",
        metavar="EXTENSION",
        default=[],
        action="append"
    )
    parser.add_argument(
        "-C",
        "--cmds",
        help="path to the FILE where intercepted commands will be saved (default is clade/cmds.txt)",
        metavar="FILE"
    )
    parser.add_argument(
        "-f",
        "--force",
        help="force Clade to clean its working directory before launch",
        action="store_true",
    )
    parser.add_argument(
        "-fe",
        "--force-exts",
        help="force Clade to clean working directories of specified list of extensions",
        action="store_true",
    )
    parser.add_argument(
        "-wr",
        "--wrappers",
        help="enable intercepting mode based on wrappers (not supported on Windows)",
        action="store_true",
    )
    parser.add_argument(
        "-i",
        "--intercept",
        help="only intercept build commands, without processing with extensions",
        action="store_true",
    )
    parser.add_argument(
        "-io",
        "--intercept-open",
        help="also intercept open() calls",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-a",
        "--append",
        help="append intercepted commands to existing cmds.txt file",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--version",
        help="print Clade version",
        action="store_true",
    )
    parser.add_argument(
        "--cif",
        help="name or path of the CIF to use",
    )
    parser.add_argument(
        dest="command",
        nargs=argparse.REMAINDER,
        help="build command to run and intercept",
    )

    args = parser.parse_args(args)

    if args.version:
        print("Clade", get_clade_version())
        sys.exit()

    if not args.cmds:
        args.cmds = os.path.join(args.work_dir, "cmds.txt")

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

    conf["work_dir"] = args.work_dir
    conf["log_level"] = args.log_level
    conf["cmds_file"] = args.cmds
    conf["force"] = args.force
    conf["use_wrappers"] = args.wrappers
    conf["preset"] = args.preset
    conf["command"] = args.command

    conf["Info.cif"] = args.cif if args.cif else conf.get("Info.cif", "cif")

    return conf


def main(sys_args=sys.argv[1:]):
    args = parse_args(sys_args)
    conf = prepare_conf(args)

    # Create Clade interface object
    try:
        c = Clade(work_dir=conf["work_dir"], cmds_file=conf["cmds_file"], conf=conf, preset=args.preset)
    except RuntimeError as e:
        raise SystemExit(e)

    if os.path.isfile(conf["cmds_file"]) and args.intercept and not args.append:
        c.logger.info("File with intercepted commands already exists: {!r}".format(conf["cmds_file"]))
        sys.exit(-1)
    elif os.path.isfile(conf["cmds_file"]) and not args.intercept and not args.append:
        c.logger.info("Skipping build and reusing {!r} file".format(conf["cmds_file"]))
    else:
        if not args.command:
            c.logger.error("Build command is missing")
            sys.exit(-1)

        c.logger.info("Starting build")
        build_time_start = time.time()
        r = c.intercept(conf["command"], use_wrappers=conf["use_wrappers"], append=args.append, intercept_open=args.intercept_open)

        build_delta = datetime.timedelta(seconds=(time.time() - build_time_start))
        build_delta_str = str(build_delta).split(".")[0]

        # Clade can still proceed further if exit code != 0
        c.logger.error("Build finished in {} with exit code {}".format(build_delta_str, r))

        if args.intercept and os.path.exists(conf["cmds_file"]):
            c.logger.info("Path to the file with intercepted commands: {!r}".format(conf["cmds_file"]))
            sys.exit(r)

    if not os.path.exists(conf["cmds_file"]):
        c.logger.error("Something is wrong: file with intercepted commands is empty")
        sys.exit(-1)

    try:
        extensions = args.extension if args.extension else c.conf["extensions"]

        c.logger.info("Executing extensions")
        ext_time_start = time.time()
        c.parse_list(extensions, args.force_exts)

        ext_delta = datetime.timedelta(seconds=(time.time() - ext_time_start))
        ext_delta_str = str(ext_delta).split(".")[0]
        c.logger.info("Extensions finished in {}".format(ext_delta_str))
    except RuntimeError as e:
        if e.args:
            raise SystemExit(e)
        else:
            raise SystemExit(-1)

    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
