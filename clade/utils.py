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

import array
import importlib.metadata
import logging
import os
import re
import subprocess
import sys
from typing import Any

import orjson

Conf = dict[str, Any]


def get_logger(
    name: str, with_name: bool = True, conf: Conf | None = None
) -> logging.Logger:
    if not conf:
        conf = {}

    logger = logging.getLogger(name)

    # Remove all old handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    if with_name:
        formatter = logging.Formatter(
            f"%(asctime)s clade {name}: %(message)s", "%H:%M:%S"
        )
    else:
        formatter = logging.Formatter("%(asctime)s clade: %(message)s", "%H:%M:%S")

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if conf.get("work_dir") and os.access(conf.get("work_dir", "."), os.W_OK):
        try:
            log_file = os.path.join(conf["work_dir"], "clade.log")
            log_file = os.path.abspath(log_file)
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            file_handler = logging.FileHandler(log_file, delay=True)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (PermissionError, OSError):
            # Can't write to clade.log file if working directory is read only
            pass

    logger.setLevel(conf.get("log_level", "INFO"))

    return logger


def merge_preset_to_conf(preset_name: str, conf: Conf) -> Conf:
    preset_file = os.path.join(
        os.path.dirname(__file__), "extensions", "presets", "presets.json"
    )

    presets = load(preset_file)

    if preset_name not in presets:
        raise RuntimeError(f"Preset {preset_name!r} is not found")

    preset_conf = presets[preset_name]
    parent_preset = preset_conf.get("extends")

    if parent_preset:
        preset_conf = merge_preset_to_conf(parent_preset, preset_conf)

    preset_conf.update(conf)

    return preset_conf


def get_clade_version():
    version = importlib.metadata.version("clade")
    # For editable installs this is the source tree, so git describe works
    location = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if not os.path.exists(os.path.join(location, ".git")):
        return version

    try:
        desc = ["git", "describe", "--tags", "--dirty"]
        version = subprocess.check_output(
            desc, cwd=location, stderr=subprocess.DEVNULL, universal_newlines=True
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        pass

    return version


def get_program_version(program, version_arg="--version"):
    version = "unknown"
    try:
        version = subprocess.check_output(
            [program, version_arg], stderr=subprocess.DEVNULL, universal_newlines=True
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        pass

    if version.startswith("gcc"):
        version = re.sub(r"\nCopyright[\s\S]*", "", version)

    return version


def array_hook(obj):
    if isinstance(obj, array.array):
        return list(obj)
    raise TypeError


def dump(data: Any, path: str) -> None:
    with open(path, "wb") as fh:
        fh.write(orjson.dumps(data, default=array_hook))


def load(path: str) -> Any:
    with open(path, "rb") as f:
        return orjson.loads(f.read())
