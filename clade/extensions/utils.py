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


def normalize_path(path, cwd, cache=dict()):
    # Cache variable considerably speeds up normalizing.
    # Cache size is quite small even for extra large files.

    if cwd not in cache:
        cache[cwd] = dict()

    if path in cache[cwd]:
        return cache[cwd][path]

    if os.path.commonprefix([path, cwd]) == cwd:
        cache[cwd][path] = os.path.relpath(path, start=cwd)
    else:
        cache[cwd][path] = os.path.normpath(path)

    return cache[cwd][path]


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument("-w", "--work_dir", help="a path to the DIR where processed commands will be saved", metavar='DIR', default="clade")
    parser.add_argument("-l", "--log_level", help="set logging level (ERROR, INFO, or DEBUG)", default="INFO")
    parser.add_argument("-c", "--config", help="a path to the JSON file with configuration", metavar='JSON', default=None)
    parser.add_argument(dest="cmds_file", help="a path to the file with intercepted commands")

    args = parser.parse_args(args)

    conf = dict()
    if args.config:
        try:
            with open(args.config, "r") as f:
                conf = ujson.load(f)
        except FileNotFoundError:
            print("Configuration file is not found")
            sys.exit(-1)

    conf["work_dir"] = conf.get("work_dir", args.work_dir)
    conf["log_level"] = conf.get("log_level", args.log_level)
    conf["cmds_file"] = conf.get("cmds_file", args.cmds_file)

    return conf
