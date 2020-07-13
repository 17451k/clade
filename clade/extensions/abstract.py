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
import datetime
import fnmatch
import glob
import hashlib
import importlib
import itertools
import logging
import platform
import pkg_resources
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import ujson
import uuid

from concurrent.futures import ProcessPoolExecutor

import clade.cmds


# Setup extensions logger
logger = logging.getLogger("Clade")
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(
    logging.Formatter("%(asctime)s clade %(message)s", "%H:%M:%S")
)
logger.addHandler(handler)


class Extension(metaclass=abc.ABCMeta):
    """Parent interface class for parsing intercepted build commands.

    Attributes:
        work_dir: A path to the working directory where all output files will be stored
        conf: A dictionary with optional arguments

    Raises:
        NotImplementedError: Required subclass is not found
        FileNotFoundError: Cant find file with the build commands
    """

    __version__ = "1"

    def __init__(self, work_dir, conf=None):
        self.name = self.__class__.__name__
        self.work_dir = os.path.join(os.path.abspath(str(work_dir)), self.name)
        self.conf = conf if conf else dict()
        self.temp_dir = None

        if not hasattr(self, "requires"):
            self.requires = []
        self.debug("Extension requirements: {!r}".format(self.requires))

        self.extensions = dict()

        logger.setLevel(self.conf.get("log_level", "INFO"))

        self.ext_meta = {"version": self.get_ext_version(), "corrupted": False}
        self.global_meta_file = os.path.abspath(
            os.path.join(str(work_dir), "meta.json")
        )

        if self.conf.get("force") and not self.conf.get("force_meta_deleted"):
            try:
                os.remove(self.global_meta_file)
            except FileNotFoundError:
                pass
            self.conf["force_meta_deleted"] = True

        self.debug("Extension version: {}".format(self.ext_meta["version"]))
        self.debug("Working directory: {}".format(self.work_dir))

    def is_parsed(self):
        """Returns True if build commands are already parsed."""
        return os.path.exists(self.work_dir)

    def preprocess(self, cmd):
        """Preprocess intercepted build command before its execution"""
        return

    @staticmethod
    def prepare(parse):
        """Decorator for parse() method

        It checks configuration consistency, collects meta
        information, checks that working directory is not corrupted
        """

        def parse_wrapper(self, *args, **kwargs):
            if self.is_parsed():
                self.log("Build commands are already parsed")
                return

            self.temp_dir = tempfile.mkdtemp()
            time_start = time.time()

            try:
                return parse(self, *args, **kwargs)
            except Exception:
                if os.path.exists(self.work_dir):
                    self.ext_meta["corrupted"] = True
                raise
            finally:
                if os.path.exists(self.temp_dir):
                    self.debug("Removing temp directory: {!r}".format(self.temp_dir))
                    shutil.rmtree(self.temp_dir)

                self.ext_meta["time"] = str(
                    datetime.timedelta(seconds=(time.time() - time_start))
                )

                if os.path.exists(os.path.dirname(self.work_dir)):
                    self.dump_global_meta(args[0])

        return parse_wrapper

    @abc.abstractmethod
    def parse(self, cmds_file):
        """Parse intercepted commands."""
        pass

    def get_build_dir(self, cmds_file):
        return clade.cmds.get_build_dir(cmds_file)

    def load_data(self, file_name, raise_exception=True):
        """Load json file by name."""

        if not os.path.isabs(file_name):
            file_name = os.path.join(self.work_dir, file_name)

        if not os.path.isfile(file_name):
            message = "{!r} file is not found".format(file_name)

            if raise_exception:
                self.error(message)
                raise FileNotFoundError
            else:
                self.debug(message)

            return dict()

        self.debug("Loading {}".format(file_name))
        with open(file_name, "r") as fh:
            return ujson.load(fh)

    def dump_data(self, data, file_name, indent=4):
        """Dump data to a json file in the object working directory."""

        if not os.path.isabs(file_name):
            file_name = os.path.join(self.work_dir, file_name)

        os.makedirs(os.path.dirname(file_name), exist_ok=True)

        self.debug("Dumping {}".format(file_name))

        try:
            with open(file_name, "w") as fh:
                ujson.dump(
                    data,
                    fh,
                    sort_keys=True,
                    indent=indent,
                    ensure_ascii=False,
                    escape_forward_slashes=False,
                )
        except RecursionError:
            # This is a workaround, but it is rarely required
            self.warning(
                "Do not print data to file due to recursion limit {}".format(
                    file_name
                )
            )

    def load_data_by_key(self, folder, files=None):
        """Load data stored in multiple json files using dump_data_by_key()."""
        if files and not isinstance(files, list) and not isinstance(files, set):
            raise TypeError(
                "Provide a list or set of files to retrieve data but not {!r}".format(
                    type(files).__name__
                )
            )

        data = dict()

        if files:
            self.debug("Loading data from {!r}: {!r}".format(folder, files))
            for key in files:
                file = os.path.join(
                    folder,
                    hashlib.md5(key.encode("utf-8")).hexdigest() + ".json",
                )
                data.update(self.load_data(file, raise_exception=False))
        else:
            self.debug("Loading all data from {!r}".format(folder))
            for file in self.__get_all_files_in_folder(folder):
                data.update(self.load_data(file, raise_exception=False))

        return data

    def yield_data_by_key(self, folder, files=None):
        """Yield data stored in multiple json files using dump_data_by_key()."""
        if files and not isinstance(files, list) and not isinstance(files, set):
            raise TypeError(
                "Provide a list or set of files to retrieve data but not {!r}".format(
                    type(files).__name__
                )
            )

        if files:
            self.debug("Yielding data from {!r}: {!r}".format(folder, files))
            for key in files:
                file = os.path.join(
                    folder,
                    hashlib.md5(key.encode("utf-8")).hexdigest() + ".json",
                )

                data = self.load_data(file, raise_exception=False)
                for key in data:
                    yield key, data
        else:
            self.debug("Yielding all data from {!r}".format(folder))
            for file in self.__get_all_files_in_folder(folder):
                data = self.load_data(file, raise_exception=False)
                for key in data:
                    yield key, data

    def __get_all_files_in_folder(self, folder):
        return glob.glob(os.path.join(self.work_dir, folder, "*"))

    def dump_data_by_key(self, data, folder):
        """Dump data to multiple json files in the object working directory."""
        self.debug("Dumping data to {!r}".format(folder))

        for key in data:
            to_dump = {key: data[key]}

            file_name = os.path.join(
                folder, hashlib.md5(key.encode("utf-8")).hexdigest() + ".json"
            )

            self.dump_data(to_dump, file_name, indent=0)

    def get_ext_version(self):
        version = self.__version__

        for parent in Extension.__get_all_parents(self.__class__):
            if hasattr(parent, "__version__"):
                version = parent.__version__ + "." + version

        return version

    def check_ext_version(self):
        """Check that working directory was creating with the extension of correct version."""
        stored_meta = self.load_global_meta().get(self.name)

        if stored_meta and self.ext_meta["version"] != stored_meta["version"]:
            self.error(
                "Working directory was created by incompatible version of Clade and can't be used."
            )
            raise RuntimeError

    def check_corrupted(self):
        """Check that working directory is not corrupted."""
        stored_meta = self.load_global_meta().get(self.name)

        if stored_meta and stored_meta["corrupted"]:
            self.error("Working directory is corrupted and can't be used.")
            raise RuntimeError

    def check_conf_consistency(self):
        """Check configuration consistency.

        Any configuration change between launches must not affect already
        collected part of the build base.
        """
        global_meta = self.load_global_meta()

        if global_meta:
            for key in [k for k in global_meta["conf"] if k in self.get_ext_opts()]:
                if global_meta["conf"][key] != self.conf[key]:
                    self.error("Configuration option {!r} was changed between launches".format(key))
                    raise RuntimeError

    def get_ext_opts(self):
        """Get all options that are related to the current extension."""
        names = [self.name]
        opts = []

        # Find names of all parent classes. For example,
        # for CC it would be Compiler and Abstract
        for parent in Extension.__get_all_parents(self.__class__):
            names.append(parent.__name__)

        for name in names:
            # Here we check that all options that are related to the
            # current extension were not changed between launches.
            # Options are related if their names start with the name of
            # the extension class.
            opts.extend([k for k in self.conf if k.startswith(name + ".")])

        return opts

    def load_global_meta(self):
        return self.load_data(self.global_meta_file, raise_exception=False)

    def dump_global_meta(self, cmds_file):
        stored_meta = self.load_global_meta()
        stored_meta[self.name] = self.ext_meta

        if "conf" not in stored_meta:
            stored_meta["conf"] = self.conf
        else:
            # Store updated values of extension options after it finishes its
            # execution
            for key in [k for k in stored_meta["conf"] if k in self.get_ext_opts()]:
                stored_meta["conf"][key] = self.conf[key]

        if "build_dir" not in stored_meta:
            stored_meta["build_dir"] = self.get_build_dir(cmds_file)
        elif self.name == "Path":
            stored_meta["build_dir"] = self.conf["build_dir"]

        if "versions" not in stored_meta:
            stored_meta["versions"] = dict()

        if "clade" not in stored_meta["versions"]:
            stored_meta["versions"]["clade"] = Extension.get_clade_version()

        if "python" not in stored_meta["versions"]:
            stored_meta["versions"]["python"] = platform.python_version()

        if "pip" not in stored_meta["versions"]:
            stored_meta["versions"]["pip"] = pkg_resources.get_distribution("pip").version

        if "gcc" not in stored_meta["versions"]:
            stored_meta["versions"]["gcc"] = self.get_program_version("gcc")

        if "cif" not in stored_meta["versions"]:
            stored_meta["versions"]["cif"] = self.get_program_version("cif")

        if "uuid" not in stored_meta:
            stored_meta["uuid"] = str(uuid.uuid4())

        if "platform" not in stored_meta:
            stored_meta["platform"] = platform.platform()

        if "requirements" not in stored_meta:
            stored_meta["requirements"] = [
                "{}=={}".format(d.project_name, d.version)
                for d in pkg_resources.working_set
                if d.project_name in sys.modules and d.project_name != "clade"
            ]

        if "date" not in stored_meta:
            stored_meta["date"] = datetime.datetime.today().strftime('%Y-%m-%d %H:%M')

        self.dump_data(stored_meta, self.global_meta_file)

    def add_data_to_global_meta(self, key, data):
        stored_meta = self.load_global_meta()
        stored_meta[key] = data
        self.dump_data(stored_meta, self.global_meta_file)

    @staticmethod
    def get_clade_version():
        version = pkg_resources.get_distribution("clade").version
        location = pkg_resources.get_distribution("clade").location

        if not os.path.exists(os.path.join(location, ".git")):
            return version

        try:
            desc = ["git", "describe", "--tags", "--dirty"]
            version = subprocess.check_output(
                desc, cwd=location, stderr=subprocess.DEVNULL, universal_newlines=True
            ).strip()
        finally:
            return version

    def get_program_version(self, program, version_arg="--version"):
        version = "unknown"
        try:
            version = subprocess.check_output(
                [program, version_arg], stderr=subprocess.DEVNULL, universal_newlines=True
            ).strip()
        finally:
            if version.startswith("gcc"):
                version = re.sub(r'\nCopyright[\s\S]*', '', version)
            return version

    def __get_cmd_chunk(self, cmds, chunk_size=1000):
        cmds_it = iter(cmds)

        while True:
            piece = list(itertools.islice(cmds_it, chunk_size))

            if piece:
                yield piece
            else:
                return

    def parse_cmds_in_parallel(self, cmds, unwrap, total_cmds=None):
        if os.environ.get("CLADE_DEBUG"):
            if total_cmds:
                self.log("Parsing {} commands".format(total_cmds))

            for cmd in cmds:
                unwrap(self, cmd)
            return

        if self.conf.get("cpu_count"):
            max_workers = self.conf.get("cpu_count")
        else:
            max_workers = os.cpu_count()

        # cmds is eather list, tuple or generator
        if type(cmds) is list or type(cmds) is tuple:
            total_cmds = len(cmds)

        # Print progress only of we know total number of commands
        if total_cmds:
            self.log("Parsing {} commands".format(total_cmds))

        with ProcessPoolExecutor(max_workers=max_workers) as p:
            chunk_size = 2000
            futures = []
            finished_cmds = 0

            # Submit commands to executor in chunks
            for cmd_chunk in self.__get_cmd_chunk(cmds, chunk_size=chunk_size):
                chunk_futures = []

                for cmd in cmd_chunk:
                    f = p.submit(unwrap, self, cmd)
                    chunk_futures.append(f)
                    futures.append(f)

                while True:
                    if not futures:
                        break

                    done_futures = [x for x in futures if x.done()]

                    # Remove all futures that are already completed
                    # to reduce memory usage
                    futures = [x for x in futures if not x.done()]

                    # Track progress (only if stdout is not redirected)
                    if total_cmds and sys.stdout.isatty() and self.conf["log_level"] in ["INFO", "DEBUG"]:
                        finished_cmds += len(done_futures)

                        msg = "\t [{:.0f}%] {} of {} commands are parsed".format(
                            finished_cmds / total_cmds * 100,
                            finished_cmds,
                            total_cmds,
                        )
                        print(msg, end="\r")

                    # Check return value of all finished futures
                    for f in done_futures:
                        try:
                            f.result()
                        except Exception as e:
                            raise RuntimeError(
                                "Something happened in the child process: {}".format(
                                    e
                                )
                            )

                    # Submit next chunk if the current one is almost processed
                    finished_chunk_cmds = len(
                        [x for x in chunk_futures if x.done()]
                    )
                    if finished_chunk_cmds > (chunk_size - chunk_size // 10):
                        break

                    # Save a little bit of CPU time
                    # skip sleep only for very small projects
                    time.sleep(0.1)

            if total_cmds and sys.stdout.isatty() and self.conf["log_level"] in ["INFO", "DEBUG"]:
                print(" " * 79, end="\r")

    @staticmethod
    def get_all_extensions():
        """Get all extension lasses."""

        Extension._import_extension_modules()
        return Extension.__get_all_subclasses(Extension)

    @staticmethod
    def __get_all_subclasses(cls):
        """Get all subclasses of a given class."""

        for subclass in cls.__subclasses__():
            yield subclass
            yield from Extension.__get_all_subclasses(subclass)

    @staticmethod
    def __get_all_parents(cls):
        """Get all subclasses of a given class."""

        for parent in cls.__bases__:
            yield parent
            yield from Extension.__get_all_parents(parent)

    @staticmethod
    def _import_extension_modules():
        clade_modules = [x for x in sys.modules if x.startswith("clade")]

        """Import all Python modules located in 'extensions' folder."""
        for _, _, filenames in os.walk(os.path.dirname(__file__)):
            for filename in fnmatch.filter(filenames, "*.py"):
                module_name = "." + os.path.splitext(os.path.basename(filename))[0]

                for module in clade_modules:
                    if module.endswith(module_name):
                        break
                else:
                    importlib.import_module(module_name, "clade.extensions")

    @staticmethod
    def find_subclass(ext_name):
        """Find a subclass of Interface class."""
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
