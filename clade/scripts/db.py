# Copyright (c) 2026 Ilya Shchepetkov
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

from clade.db import Database


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        description="Compress or decompress the values stored in clade.db"
    )

    parser.add_argument(
        "action",
        choices=["compress", "decompress"],
        help="compress: store values as zlib blobs; decompress: store them as JSON text",
    )
    parser.add_argument(dest="work_dir", help="path to the Clade working directory")

    args = parser.parse_args(args)

    path = os.path.join(args.work_dir, "clade.db")

    if not os.path.isfile(path):
        sys.exit(f"{path!r} does not exist")

    before = os.path.getsize(path)
    Database(path).recode(args.action == "compress")
    after = os.path.getsize(path)

    print(f"{path}: {before / 2**20:.1f} MB -> {after / 2**20:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1:])
