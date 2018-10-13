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

import abc
import fnmatch
import glob
import hashlib
import logging
import os
import sys
import tempfile
import ujson

import clade.cmds
from clade.extensions.utils import merge_preset_to_conf


# Setup extensions logger
logger = logging.getLogger("Clade")
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s clade %(message)s", "%H:%M:%S"))
logger.addHandler(handler)


class Extension(metaclass=abc.ABCMeta):
    """Parent interface class for parsing intercepted build commands.

    Attributes:
        work_dir: A path to the working directory where all output files will be stored
        cmds: A list with intercepted build commands
        conf: A dictionary with optional arguments

    Raises:
        NotImplementedError: Required subclass is not found
        FileNotFoundError: Cant find file with parsed build command
    """

    def __init__(self, work_dir, conf=None, preset="base"):
        self.name = self.__class__.__name__
        self.work_dir = os.path.join(os.path.abspath(str(work_dir)), self.name)
        self.conf = conf if conf else dict()
        self.conf = merge_preset_to_conf(preset, self.conf)
        self.temp_dir = tempfile.mkdtemp()

        if not hasattr(self, "requires"):
            self.requires = []

        self.extensions = dict()

        logger.setLevel(self.conf.get("log_level", "INFO"))

        self.already_initialised = dict()
        self.already_initialised[self.name] = self
        self.init_extensions(work_dir)

        self.debug("Working directory: {}".format(self.work_dir))

    def init_extensions(self, work_dir):
        """Initialise all extensions required by this object."""

        if not self.requires:
            return

        self.debug("Prerequisites to initialise: {}".format(
            [x for x in self.requires if x not in self.already_initialised]
        ))

        for ext_name in self.requires:
            if ext_name in self.already_initialised:
                self.extensions[ext_name] = self.already_initialised[ext_name]
                continue

            ext_class = Extension.find_subclass(ext_name)
            self.extensions[ext_name] = ext_class(work_dir, self.conf)

    def parse_prerequisites(self, cmds_file):
        """Run parse() method on all extensions required by this object."""
        for ext_name in self.extensions:
            if not self.extensions[ext_name].is_parsed():
                self.extensions[ext_name].parse(cmds_file)

    def is_parsed(self):
        """Returns True if build commands are already parsed."""
        return os.path.exists(self.work_dir)

    @staticmethod
    def prepare(parse):
        """Decorator for parse() method

        It checks that commands were not already parsed
        and run parse() for required extensions.
        """
        def parse_wrapper(self, *args, **kwargs):
            if self.is_parsed():
                self.log("Build commands are already parsed")
                return

            self.parse_prerequisites(args[0])
            return parse(self, *args, **kwargs)

        return parse_wrapper

    @abc.abstractmethod
    def parse(self, cmds_file):
        """Parse intercepted commands."""
        pass

    def get_build_cwd(self, cmds_file):
        return self.conf.get("build_cwd", clade.cmds.get_build_cwd(cmds_file))

    def load_data(self, file_name, raise_exception=True):
        """Load json file by name."""

        if not os.path.isabs(file_name):
            file_name = os.path.join(self.work_dir, file_name)

        if not os.path.isfile(file_name):
            message = "{!r} file is not found".format(file_name)

            if raise_exception:
                raise FileNotFoundError(message)

            self.warning(message)
            return dict()

        self.debug("Load {}".format(file_name))
        with open(file_name, "r") as fh:
            return ujson.load(fh)

    def dump_data(self, data, file_name, indent=4):
        """Dump data to a json file in the object working directory."""

        if not os.path.isabs(file_name):
            file_name = os.path.join(self.work_dir, file_name)

        os.makedirs(os.path.dirname(file_name), exist_ok=True)

        self.debug("Dump {}".format(file_name))

        try:
            with open(file_name, "w") as fh:
                ujson.dump(data, fh, sort_keys=True, indent=indent, ensure_ascii=False, escape_forward_slashes=False)
        except RecursionError:
            # todo: This is a workaround but it is required rarely
            self.warning("Do not print data to file due to recursion limit {}".format(file_name))

    def load_data_by_key(self, folder, files=None):
        """Load data stored in multiple json files using dump_data_by_key()."""
        data = dict()
        if files is None:
            for file in glob.glob(os.path.join(self.work_dir, folder, "*")):
                data.update(self.load_data(file, raise_exception=False))
        elif isinstance(files, list) or isinstance(files, set):
            for key in files:
                file_name = os.path.join(folder, hashlib.md5(key.encode('utf-8')).hexdigest() + ".json")
                data.update(self.load_data(file_name, raise_exception=False))
        else:
            raise TypeError("Provide a list or set of files to retrieve data but not {!r}".format(type(files).__name__))

        return data

    def dump_data_by_key(self, data, folder):
        """Dump data to multiple json files in the object working directory."""
        for key in data:
            to_dump = {key: data[key]}

            file_name = os.path.join(folder, hashlib.md5(key.encode('utf-8')).hexdigest() + ".json")

            self.dump_data(to_dump, file_name, indent=0)

    @staticmethod
    def __get_all_subclasses(cls):
        """Get all sublclasses of a given class."""

        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(Extension.__get_all_subclasses(subclass))

        return all_subclasses

    @staticmethod
    def __import_extension_modules():
        """Import all Python modules located in 'extensions' folder."""
        for root, _, filenames in os.walk(os.path.dirname(__file__)):
            for filename in fnmatch.filter(filenames, '*.py'):
                file = os.path.join(root, filename)

                if file != __file__:
                    sys.path.insert(0, os.path.dirname(file))
                    __import__(os.path.splitext(os.path.basename(file))[0])
                    sys.path.pop(0)

    @staticmethod
    def find_subclass(ext_name):
        """Find a sublclass of Interface class."""

        Extension.__import_extension_modules()

        for ext_class in Extension.__get_all_subclasses(Extension):
            if ext_name == ext_class.__name__:
                return ext_class
        else:
            raise NotImplementedError("Can't find '{}' class".format(ext_name))

    def log(self, message):
        """Print debug message.

        self.conf["log_level"] must be set to INFO or DEBUG in order to see the message.
        """
        logger.info("{}: {}".format(self.name, message))

    def debug(self, message):
        """Print debug message.

        self.conf["log_level"] must be set to DEBUG in order to see the message.

        WARNING: debug messages can have a great impact on the performance.
        """
        logger.debug("{}: {}".format(self.name, message))

    def warning(self, message):
        """Print warning message.

        self.conf["log_level"] must be set to WARNING, INFO or DEBUG in order to see the message.
        """
        logger.warning("{}: {}".format(self.name, message))

    def error(self, message):
        """Print error message.

        self.conf["log_level"] must be set to ERROR, WARNING, INFO or DEBUG in order to see the message.
        """
        logger.error("{}: {}".format(self.name, message))
