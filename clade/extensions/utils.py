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
import ujson


def merge_preset_to_conf(preset_name, conf):
    preset_file = os.path.join(
        os.path.dirname(__file__), "presets", "presets.json"
    )

    with open(preset_file, "r") as f:
        presets = ujson.load(f)

        if preset_name not in presets:
            print("Preset {!r} is not found".format(preset_name))
            sys.exit(-1)

        preset_conf = presets[preset_name]

        for parent_preset in preset_conf.get("extends", []):
            preset_conf = merge_preset_to_conf(parent_preset, preset_conf)

    preset_conf.update(conf)
    return preset_conf


def load_conf_file(file_name):
    conf = dict()

    if file_name:
        try:
            with open(file_name, "r") as f:
                conf = ujson.load(f)
        except FileNotFoundError:
            print("Configuration file is not found")
            sys.exit(-1)

    return conf


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-w",
        "--work-dir",
        help="a path to the DIR where processed commands will be saved",
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
        help="a path to the JSON file with configuration",
        metavar="JSON",
        default=None,
    )
    parser.add_argument(
        "-p",
        "--preset",
        help="a name of the preset configuration",
        metavar="NAME",
        default="base",
    )
    parser.add_argument(
        "-f",
        "--force",
        help="force all Clade extensions to run even if their working directories are not empty",
        action="store_true"
    )
    parser.add_argument(
        "-fc",
        "--force-current",
        help="force the current Clade extension to run even if its working directory is not empty",
        action="store_true"
    )
    parser.add_argument(
        dest="cmds_file", help="a path to the file with intercepted commands"
    )

    args = parser.parse_args(args)

    conf = load_conf_file(args.config)
    conf["work_dir"] = conf.get("work_dir", args.work_dir)
    conf["log_level"] = conf.get("log_level", args.log_level)
    conf["cmds_file"] = conf.get("cmds_file", args.cmds_file)
    conf["force"] = conf.get("force", args.force)
    conf["force_current"] = conf.get("force_current", args.force_current)
    conf["preset"] = args.preset

    return merge_preset_to_conf(args.preset, conf)


def common_main(cl, args):
    conf = parse_args(args)

    try:
        c = cl(conf["work_dir"], conf=conf)
        c.parse(conf["cmds_file"])
    except RuntimeError as e:
        if e.args:
            raise SystemExit(e)
        else:
            raise SystemExit
