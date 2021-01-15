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
import importlib
import pkg_resources
import platform
import os
import pickle
import shutil
import sys
import tempfile
import time
import ujson
import uuid
import zipfile

from concurrent.futures import ProcessPoolExecutor

from clade.cmds import get_build_dir
from clade.extensions.utils import yield_chunk
from clade.utils import get_clade_version, get_program_version, get_logger


class Extension(metaclass=abc.ABCMeta):
    """Parent interface class for parsing intercepted build commands.

    Attributes:
        work_dir: A path to the working directory where all output files will be stored
        conf: A dictionary with optional arguments

    Raises:
        NotImplementedError: Required subclass is not found
        FileNotFoundError: Cant find file with the build commands
    """

    __version__ = "2"

    def __init__(self, work_dir, conf=None):
        self.name = self.__class__.__name__
        self.clade_work_dir = os.path.abspath(str(work_dir))
        self.work_dir = os.path.join(self.clade_work_dir, self.name)
        self.temp_dir = ""

        self.conf = conf if conf else dict()

        self.logger = None

        if not hasattr(self, "requires"):
            self.requires = []

        self.extensions = dict()

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

                delta = datetime.timedelta(seconds=(time.time() - time_start))
                delta_str = str(delta).split(".")[0]

                self.ext_meta["time"] = delta_str

                # 5 is an arbitrary threshold to supress printing unnessesary
                # log messages for extensions that finished quickly
                if delta.seconds > 5:
                    self.log("Finished in {}".format(delta_str))

                if os.path.exists(os.path.dirname(self.work_dir)):
                    self.dump_global_meta(args[0])

        return parse_wrapper

    @abc.abstractmethod
    def parse(self, cmds_file):
        """Parse intercepted commands."""
        pass

    def load_data(self, file_name, raise_exception=True, format="json"):
        """Load file by name."""

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

        self.debug("Loading {!r}".format(file_name))

        if format == "json":
            return self.__load_data_json(file_name)
        elif format == "pickle":
            return self.__load_data_pickle(file_name)
        else:
            self.error("Unreckognised data format: {!r}".format(format))
            raise ValueError

    def __load_data_json(self, file_name, raise_exception=True):
        with open(file_name, "r") as fh:
            return ujson.load(fh)

    def __load_data_pickle(self, file_name, raise_exception=True):
        with open(file_name, "rb") as fh:
            return pickle.load(fh)

    def dump_data(self, data, file_name, indent=4, format="json"):
        """Dump data to a file in the object working directory."""

        if not os.path.isabs(file_name):
            file_name = os.path.join(self.work_dir, file_name)

        os.makedirs(os.path.dirname(file_name), exist_ok=True)

        self.debug("Dumping {!r}".format(file_name))

        if format == "json":
            self.__dump_data_json(data, file_name, indent=indent)
        elif format == "pickle":
            self.__dump_data_pickle(data, file_name)
        else:
            self.error("Unreckognised data format: {!r}".format(format))
            raise ValueError

    def __dump_data_pickle(self, data, file_name):
        with open(file_name, "wb") as fh:
            pickle.dump(data, fh, protocol=4)

    def __dump_data_json(self, data, file_name, indent=0):
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
                "Do not print data to file due to recursion limit {!r}".format(
                    file_name
                )
            )

    def load_data_by_key(self, archive, keys=None):
        """Load data stored in multiple json files inside zip archive using dump_data_by_key()."""
        data = dict()

        for key, value in self.__yield_data_by_key(archive=archive, keys=keys):
            data.update(value)

        return data

    def yield_data_by_key(self, archive, keys=None):
        """Yield data stored in multiple json files inside zip archive using dump_data_by_key()."""
        yield from self.__yield_data_by_key(archive, keys=keys)

    def __yield_data_by_key(self, archive, keys=None):
        """Yield data stored in multiple json files inside zip archive using dump_data_by_key()."""
        if keys and not isinstance(keys, list) and not isinstance(keys, set):
            raise TypeError(
                "Provide a list or set of files to retrieve data but not {!r}".format(
                    type(keys).__name__
                )
            )

        if not os.path.isabs(archive):
            archive = os.path.join(self.work_dir, archive)

        if not os.path.exists(archive):
            self.debug("{!r} file is not found".format(archive))
            return

        with zipfile.ZipFile(archive, "r") as zip_fh:
            if keys:
                self.debug("Yielding data from {!r}: {!r}".format(archive, keys))
                for key in keys:
                    data = self.__load_data_from_zip(key, zip_fh, raise_exception=False)
                    yield key, {key: data}
            else:
                self.debug("Yielding all data from {!r}".format(archive))
                for file in self.__get_all_files_in_archive(zip_fh):
                    data = self.__load_data_from_zip(file, zip_fh, raise_exception=False)
                    yield file, {file: data}

    def __get_all_files_in_archive(self, zip_fh):
        return zip_fh.namelist()

    def dump_data_by_key(self, data, archive):
        """Dump data to multiple json files inside zip archive in the object working directory."""
        if not os.path.isabs(archive):
            archive = os.path.join(self.work_dir, archive)

        os.makedirs(os.path.dirname(archive), exist_ok=True)

        self.debug("Dumping data to {!r}".format(archive))

        with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_STORED) as zip_fh:
            for key in data:
                self.__dump_data_to_zip_fh(data[key], key, zip_fh)

    def load_data_from_zip(self, file_name, archive, raise_exception=True):
        if not os.path.isabs(archive):
            archive = os.path.join(self.work_dir, archive)

        self.debug("Loading {!r} from {!r}".format(file_name, archive))

        with zipfile.ZipFile(archive, "r") as zip_fh:
            return self.__load_data_from_zip(file_name, zip_fh, raise_exception=raise_exception)

    def __load_data_from_zip(self, file_name, zip_fh, raise_exception=True):
        try:
            with zip_fh.open(file_name, "r") as fh:
                return ujson.loads(fh.read().decode("utf-8"))
        except (FileNotFoundError, KeyError) as e:
            if raise_exception:
                self.error(e)
                raise RuntimeError

            return dict()

    def dump_data_to_zip(self, data, file_name, archive):
        if not os.path.isabs(archive):
            archive = os.path.join(self.work_dir, archive)

        self.debug("Dumping {!r} to {!r}".format(file_name, archive))

        os.makedirs(os.path.dirname(archive), exist_ok=True)

        with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_STORED) as zip_fh:
            self.__dump_data_to_zip_fh(data, file_name, zip_fh)

    def __dump_data_to_zip_fh(self, data, file_name, zip_fh):
        zip_fh.writestr(file_name, ujson.dumps(data).encode("utf-8"))

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
        if not os.path.exists(self.work_dir):
            return

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
        return self.load_data(self.global_meta_file, raise_exception=False, format="json")

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
            stored_meta["build_dir"] = get_build_dir(cmds_file)
        elif self.name == "Path":
            stored_meta["build_dir"] = self.conf["build_dir"]

        if "versions" not in stored_meta:
            stored_meta["versions"] = dict()

        if "clade" not in stored_meta["versions"]:
            stored_meta["versions"]["clade"] = get_clade_version()

        if "python" not in stored_meta["versions"]:
            stored_meta["versions"]["python"] = platform.python_version()

        if "pip" not in stored_meta["versions"]:
            stored_meta["versions"]["pip"] = pkg_resources.get_distribution("pip").version

        if "gcc" not in stored_meta["versions"]:
            stored_meta["versions"]["gcc"] = get_program_version("gcc")

        if "cif" not in stored_meta["versions"]:
            stored_meta["versions"]["cif"] = get_program_version("cif")

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

        self.dump_data(stored_meta, self.global_meta_file, indent=4, format="json")

    def add_data_to_global_meta(self, key, data):
        stored_meta = self.load_global_meta()
        stored_meta[key] = data
        self.dump_data(stored_meta, self.global_meta_file, indent=4, format="json")

    def __get_empty_obj(self, obj):
        empty_self = obj.__class__(self.clade_work_dir, self.conf)
        empty_self.temp_dir = self.temp_dir

        for ext_name in obj.extensions:
            empty_self.extensions[ext_name] = self.__get_empty_obj(obj.extensions[ext_name])

        return empty_self

    def parse_cmds_in_parallel(self, cmds, unwrap, total_cmds=None):
        if os.environ.get("CLADE_DEBUG"):
            if total_cmds:
                self.log("Parsing {} commands".format(total_cmds))

            for cmd in cmds:
                unwrap(self, cmd)
            return

        max_workers = self.conf.get("cpu_count", os.cpu_count())

        # cmds is eather list, tuple or generator
        if type(cmds) is list or type(cmds) is tuple:
            total_cmds = len(cmds)

        # Print progress only of we know total number of commands
        if total_cmds:
            self.log("Parsing {} commands".format(total_cmds))

        # Passing "self" object to p.submit() can be very, very time consuming
        # if self is rather big. So, here we create an empty object
        # of the current type, and use it instead
        empty_self = self.__get_empty_obj(self)

        with ProcessPoolExecutor(max_workers=max_workers) as p:
            chunk_size = 2000
            futures = []
            finished_cmds = 0

            # Submit commands to executor in chunks
            for cmd_chunk in yield_chunk(cmds, chunk_size=chunk_size):
                chunk_futures = []

                for cmd in cmd_chunk:
                    f = p.submit(unwrap, empty_self, cmd)
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
                            raise e

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
        """Get all extension classes."""

        Extension._import_extension_modules()
        return Extension.__get_all_subclasses(Extension)

    @staticmethod
    def __get_all_subclasses(parent_cls):
        """Get all subclasses of a given class."""

        for subclass in parent_cls.__subclasses__():
            yield subclass
            yield from Extension.__get_all_subclasses(subclass)

    @staticmethod
    def __get_all_parents(child_cls):
        """Get all parents of a given class."""

        for parent in child_cls.__bases__:
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
            raise NotImplementedError("Can't find {!r} class".format(ext_name))

    def log(self, message):
        """Print debug message.

        self.conf["log_level"] must be set to INFO or DEBUG in order to see the message.
        """
        self.__get_logger()
        self.logger.info("{}: {}".format(self.name, message))

    def debug(self, message):
        """Print debug message.

        self.conf["log_level"] must be set to DEBUG in order to see the message.

        WARNING: debug messages can have a great impact on the performance.
        """
        self.__get_logger()
        self.logger.debug("{}: [DEBUG] {}".format(self.name, message))

    def warning(self, message):
        """Print warning message.

        self.conf["log_level"] must be set to WARNING, INFO or DEBUG in order to see the message.
        """
        self.__get_logger()
        self.logger.warning("{}: [WARNING] {}".format(self.name, message))

    def error(self, message):
        """Print error message.

        self.conf["log_level"] must be set to ERROR, WARNING, INFO or DEBUG in order to see the message.
        """
        self.__get_logger()
        self.logger.error("{}: [ERROR] {}".format(self.name, message))

    def __get_logger(self):
        # Initializing logger this way serves two purposes:
        #   - as a workaround for multiprocessing not supporting passing logger
        #     objects in Python 3.5 and 3.6
        #   - and to setup logger in subprocesses

        if not self.logger:
            self.logger = get_logger("clade", with_name=False, conf=self.conf)
