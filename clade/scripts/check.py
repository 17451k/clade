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
import sys

from clade import Clade


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        description="Check that Clade working directory exists and not corrupted."
    )

    parser.add_argument(
        dest="work_dir", help="path to the Clade working directory"
    )

    args = parser.parse_args(args)

    c = Clade(args.work_dir)
    sys.exit(not c.work_dir_ok(log=True))


if __name__ == "__main__":
    main(sys.argv[1:])
