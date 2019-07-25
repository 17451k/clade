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
import sys
import ujson


def merge_preset_to_conf(preset_name, conf):
    preset_file = os.path.join(
        os.path.dirname(__file__), "presets", "presets.json"
    )

    with open(preset_file, "r") as f:
        presets = ujson.load(f)

    if preset_name not in presets:
        raise RuntimeError("Preset {!r} is not found".format(preset_name))

    preset_conf = presets[preset_name]
    parent_preset = preset_conf.get("extends")

    if parent_preset:
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
