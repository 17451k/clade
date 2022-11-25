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
import pathlib
import pkg_resources
import platform
import os
import shutil
import sys
import tempfile
import time
import ujson
import uuid

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

    __version__ = "3"

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

    def file_exists(self, file_name):
        '''File exists in the working directory'''
        if not os.path.isabs(file_name):
            file_name = os.path.join(self.work_dir, file_name)

        return os.path.exists(file_name)

    def load_data(self, file_name, raise_exception=True):
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

        with open(file_name, "r") as fh:
            return ujson.load(fh)

    def dump_data(self, data, file_name, indent=None):
        """Dump data to a file in the object working directory."""

        if not os.path.isabs(file_name):
            file_name = os.path.join(self.work_dir, file_name)

        os.makedirs(os.path.dirname(file_name), exist_ok=True)

        self.debug("Dumping {!r}".format(file_name))

        if not indent:
            indent = self.conf.get("indent", 4)

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
        except FileNotFoundError:
            # Workaround for Python 3.5 and Windows
            self.error("Can't create file {!r}".format(file_name))

    def load_data_by_key(self, folder, keys=None):
        """Load data stored in multiple json files using dump_data_by_key()."""
        data = dict()

        for key, value in self.__yield_data_by_key(folder, keys=keys):
            data.update(value)

        return data

    def yield_data_by_key(self, folder, keys=None):
        """Yield data stored in multiple json files using dump_data_by_key()."""
        yield from self.__yield_data_by_key(folder, keys=keys)

    def __yield_data_by_key(self, folder, keys=None):
        if keys and not isinstance(keys, list) and not isinstance(keys, set):
            raise TypeError(
                "Provide a list or set of files to retrieve data but not {!r}".format(
                    type(keys).__name__
                )
            )

        if not os.path.isabs(folder):
            folder = os.path.join(self.work_dir, folder)

        if not os.path.exists(folder):
            self.debug("{!r} folder is not found".format(folder))
            return

        if keys:
            self.debug("Yielding data from {!r}: {!r}".format(folder, keys))
            for key in keys:
                file_name = self.__get_file_name_by_key(key, folder)

                data = self.load_data(file_name, raise_exception=False)
                for key in data:
                    yield key, data
        else:
            self.debug("Yielding all data from {!r}".format(folder))
            for file_name in self.__get_all_json_files_in_folder(folder):
                data = self.load_data(file_name, raise_exception=False)
                for key in data:
                    yield key, data

    def __get_all_json_files_in_folder(self, folder):
        files = []
        for p in pathlib.Path(folder).glob("**/*.json"):
            files.append(str(p))

        return files

    def dump_data_by_key(self, data, folder, indent=None):
        """Dump data to multiple json files in the object working directory."""
        self.debug("Dumping data to {!r}".format(folder))

        for key in data:
            file_name = self.__get_file_name_by_key(key, folder)
            self.dump_data({key: data[key]}, file_name, indent=indent)

    def __get_file_name_by_key(self, key, folder):
        file_name = folder + os.sep + key + ".json"
        file_name = os.path.normpath(file_name)

        return file_name

    def get_ext_version(self):
        version = self.__version__

        for parent in Extension.__get_all_parents(self.__class__):
            if hasattr(parent, "__version__"):
                version = parent.__version__ + "." + version

        return version

    def check_ext_version(self):
        """Check that working directory was creating with the extension of correct version."""
        stored_meta = self.load_global_meta().get(self.name)

        if os.path.exists(self.work_dir) and stored_meta and self.ext_meta["version"] != stored_meta["version"]:
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
                    self.error(
                        f"Configuration option {key} was changed between launches"
                    )
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
            stored_meta["versions"]["pip"] = pkg_resources.get_distribution(
                "pip"
            ).version

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
            stored_meta["date"] = datetime.datetime.today().strftime("%Y-%m-%d %H:%M")

        self.dump_data(stored_meta, self.global_meta_file, indent=4)

    def add_data_to_global_meta(self, key, data):
        stored_meta = self.load_global_meta()
        stored_meta[key] = data
        self.dump_data(stored_meta, self.global_meta_file, indent=4)

    def __get_empty_obj(self, obj):
        empty_self = obj.__class__(self.clade_work_dir, self.conf)
        empty_self.temp_dir = self.temp_dir

        for ext_name in obj.extensions:
            empty_self.extensions[ext_name] = self.__get_empty_obj(
                obj.extensions[ext_name]
            )

        return empty_self

    def execute_in_parallel(
        self, objs, process, args=(), total_objs=None, pass_self=True
    ):
        # objs is eather list, tuple or generator
        if not total_objs and (type(objs) is list or type(objs) is tuple):
            total_objs = len(objs)

        # Passing "self" object to p.submit() can be very, very time consuming
        # if self is rather big. So, here we create an empty object
        # of the current type, and use it instead
        if pass_self:
            empty_self = self.__get_empty_obj(self)

        if os.environ.get("CLADE_DEBUG"):
            for obj in objs:
                if pass_self:
                    process(empty_self, obj, *args)
                else:
                    process(obj, *args)
            return

        max_workers = self.conf.get("cpu_count", os.cpu_count())

        with ProcessPoolExecutor(max_workers=max_workers) as p:
            chunk_size = 2000
            futures = []
            finished_objs = 0

            # Submit objs to executor in chunks
            for obj_chunk in yield_chunk(objs, chunk_size=chunk_size):
                chunk_futures = []

                for obj in obj_chunk:
                    if pass_self:
                        f = p.submit(process, empty_self, obj, *args)
                    else:
                        f = p.submit(process, obj, *args)

                    chunk_futures.append(f)
                    futures.append(f)

                while True:
                    if not futures:
                        break

                    done_futures = [x for x in futures if x.done()]

                    # Remove all futures that are already completed
                    # to reduce memory usage
                    futures = [x for x in futures if not x.done()]

                    if total_objs:
                        finished_objs += len(done_futures)

                        msg = "Processed {} out of {} [{:.0f}%]".format(
                            finished_objs,
                            total_objs,
                            finished_objs / total_objs * 100,
                        )
                        self.progress(msg)

                    # Check return value of all finished futures
                    for f in done_futures:
                        try:
                            f.result()
                        except Exception as e:
                            raise e

                    # Submit next chunk if the current one is almost processed
                    finished_chunk_objs = len([x for x in chunk_futures if x.done()])
                    if finished_chunk_objs > (chunk_size - chunk_size // 10):
                        break

                    # Save a little bit of CPU time
                    # skip sleep only for very small projects
                    time.sleep(0.1)

        # Clean line
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

    def progress(self, message):
        # Track progress (only if stdout is not redirected)
        if sys.stdout.isatty() and self.conf["log_level"] in ["INFO", "DEBUG"]:
            print(" " * 79, end="\r")
            print("\t " + message, end="\r")

    def __get_logger(self):
        # Initializing logger this way serves two purposes:
        #   - as a workaround for multiprocessing not supporting passing logger
        #     objects in Python 3.5 and 3.6
        #   - and to setup logger in subprocesses

        if not self.logger:
            self.logger = get_logger("clade", with_name=False, conf=self.conf)
