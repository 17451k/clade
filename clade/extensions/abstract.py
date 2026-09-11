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
import importlib.metadata
import json
import logging
import os
import platform
import shutil
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Generator, Iterable
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from clade.cmds import Cmd, get_build_dir
from clade.db import Database, buffered
from clade.extensions.utils import yield_chunk
from clade.utils import (
    Conf,
    dump,
    get_clade_version,
    get_logger,
    get_program_version,
    load,
)


def _run_buffered(process, self, obj, *args):
    with buffered() as rows:
        process(self, obj, *args)

    return rows


class Extension(metaclass=abc.ABCMeta):
    """Parent interface class for parsing intercepted build commands.

    Attributes:
        work_dir: A path to the working directory where all output files will be stored
        conf: A dictionary with optional arguments

    Raises:
        NotImplementedError: Required subclass is not found
        FileNotFoundError: Cant find file with the build commands
    """

    __version__ = "4"

    requires: list[str]

    def __init__(self, work_dir: str, conf: Conf | None = None):
        self.name = self.__class__.__name__
        self.clade_work_dir = os.path.abspath(str(work_dir))
        self.work_dir = os.path.join(self.clade_work_dir, self.name)
        self.temp_dir = ""

        self.conf: Conf = conf if conf else {}

        self.db = Database(
            os.path.join(self.clade_work_dir, "clade.db"),
            compress=self.conf.get("compress_db", False),
        )

        self.logger: logging.Logger | None = None

        if not hasattr(self, "requires"):
            self.requires = []

        self.extensions: dict[str, Any] = {}

        self.ext_meta: dict[str, Any] = {
            "version": self.get_ext_version(),
            "corrupted": False,
        }
        self.global_meta_file = os.path.abspath(
            os.path.join(str(work_dir), "meta.json")
        )

        if self.conf.get("force") and not self.conf.get("force_meta_deleted"):
            try:
                os.remove(self.global_meta_file)
            except FileNotFoundError:
                pass
            self.conf["force_meta_deleted"] = True

    def is_parsed(self) -> bool:
        """Returns True if build commands are already parsed."""
        return self.name in self.load_global_meta()

    def clean(self) -> None:
        """Remove everything the extension has stored."""
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

        self.db.delete(self.name)

        stored_meta = self.load_global_meta()
        if stored_meta.pop(self.name, None) is not None:
            self.__save_global_meta(stored_meta)

    def preprocess(self, cmd: Cmd) -> None:
        """Preprocess intercepted build command before its execution"""
        return

    @staticmethod
    def prepare(parse: Callable[..., None]) -> Callable[..., None]:
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
                self.ext_meta["corrupted"] = True
                raise
            finally:
                if os.path.exists(self.temp_dir):
                    self.debug(f"Removing temp directory: {self.temp_dir!r}")
                    shutil.rmtree(self.temp_dir)

                delta = datetime.timedelta(seconds=(time.time() - time_start))
                delta_str = str(delta).split(".")[0]

                self.ext_meta["time"] = delta_str

                # 5 is an arbitrary threshold to supress printing unnessesary
                # log messages for extensions that finished quickly
                if delta.seconds > 5:
                    self.log(f"Finished in {delta_str}")

                if os.path.exists(os.path.dirname(self.work_dir)):
                    self.dump_global_meta(args[0])

        return parse_wrapper

    @abc.abstractmethod
    def parse(self, cmds_file: str) -> None:
        """Parse intercepted commands."""

    def __db_name(self, file_name: str) -> str | None:
        """Name under which the file is stored in the database.

        Absolute paths outside the working directory are kept as real files.
        """
        if not os.path.isabs(file_name):
            return os.path.normpath(file_name)

        name = os.path.relpath(file_name, self.work_dir)
        return None if name.startswith("..") else name

    def file_exists(self, file_name: str) -> bool:
        """File exists in the working directory"""
        name = self.__db_name(file_name)

        if name is None:
            return os.path.exists(file_name)

        return self.db.has(self.name, name)

    def load_data(self, file_name: str, raise_exception: bool = True) -> Any:
        """Load file by name."""
        name = self.__db_name(file_name)

        if name is None:
            data = load(file_name) if os.path.isfile(file_name) else None
        else:
            data = self.db.get(self.name, name)

        if data is None:
            message = f"{file_name!r} file is not found"

            if raise_exception:
                self.error(message)
                raise FileNotFoundError
            else:
                self.debug(message)

            return {}

        return data

    def load_dict_with_int_keys(self, file_name: str) -> dict[int, Any]:
        """Load dictionary and replace back string keys with int ones."""
        data = self.load_data(file_name)
        return {int(key): data[key] for key in data}

    def dump_dict_with_int_keys(self, data: dict[int, Any], file_name: str) -> None:
        """Dump dictionary with int keys by replacing them with string ones."""
        self.dump_data({str(key): data[key] for key in data}, file_name)

    def dump_data(self, data: Any, file_name: str) -> None:
        """Dump data to the database under a file name in the object working directory."""
        name = self.__db_name(file_name)
        self.debug(f"Dumping {file_name!r}")

        if name is None:
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
            dump(data, file_name)
        else:
            self.db.put(self.name, name, "", data)

    def load_data_by_key(
        self, folder: str, keys: list[str] | set[str] | None = None
    ) -> dict[str, Any]:
        """Load data stored in the database using dump_data_by_key()."""
        self.__check_keys(keys)
        return dict(self.db.iter(self.name, folder, keys))

    def yield_data_by_key(
        self, folder: str, keys: list[str] | set[str] | None = None
    ) -> Generator[tuple[str, Any], None, None]:
        """Yield data stored in the database using dump_data_by_key()."""
        self.__check_keys(keys)

        for key, value in self.db.iter(self.name, folder, keys):
            yield key, {key: value}

    @staticmethod
    def __check_keys(keys) -> None:
        if keys and not isinstance(keys, (list, set)):
            raise TypeError(
                f"Provide a list or set of files to retrieve data but not {type(keys).__name__!r}"
            )

    def dump_data_by_key(self, data: dict[str, Any], folder: str) -> None:
        """Dump data to the database, one record per key."""
        self.debug(f"Dumping data to {folder!r}")
        self.db.put_many(self.name, folder, data)

    def file_exists_by_key(self, key: str, folder: str) -> bool:
        return self.db.has(self.name, folder, key)

    def get_ext_version(self) -> str:
        version = self.__version__

        for parent in Extension.__get_all_parents(self.__class__):
            if hasattr(parent, "__version__"):
                version = parent.__version__ + "." + version

        return version

    def check_ext_version(self) -> None:
        """Check that working directory was creating with the extension of correct version."""
        stored_meta = self.load_global_meta().get(self.name)

        if stored_meta and self.ext_meta["version"] != stored_meta["version"]:
            self.error(
                "Working directory was created by incompatible version of Clade and can't be used."
            )
            raise RuntimeError

    def check_corrupted(self) -> None:
        """Check that working directory is not corrupted."""
        stored_meta = self.load_global_meta().get(self.name)

        if stored_meta and stored_meta["corrupted"]:
            self.error("Working directory is corrupted and can't be used.")
            raise RuntimeError

    def check_conf_consistency(self) -> None:
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

    def get_ext_opts(self) -> list[str]:
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

    def load_global_meta(self) -> dict[str, Any]:
        return self.load_data(self.global_meta_file, raise_exception=False)

    def dump_global_meta(self, cmds_file: str) -> None:
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
            stored_meta["versions"] = {}

        if "clade" not in stored_meta["versions"]:
            stored_meta["versions"]["clade"] = get_clade_version()

        if "python" not in stored_meta["versions"]:
            stored_meta["versions"]["python"] = platform.python_version()

        if "pip" not in stored_meta["versions"]:
            try:
                stored_meta["versions"]["pip"] = importlib.metadata.version("pip")
            except importlib.metadata.PackageNotFoundError:
                stored_meta["versions"]["pip"] = None

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
                "{}=={}".format(d.metadata["Name"], d.version)
                for d in importlib.metadata.distributions()
                if d.metadata["Name"] in sys.modules and d.metadata["Name"] != "clade"
            ]

        if "date" not in stored_meta:
            stored_meta["date"] = (
                datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
            )

        self.__save_global_meta(stored_meta)

    def add_data_to_global_meta(self, key: str, data: Any) -> None:
        stored_meta = self.load_global_meta()
        stored_meta[key] = data
        self.__save_global_meta(stored_meta)

    def __save_global_meta(self, stored_meta: dict[str, Any]) -> None:
        with open(self.global_meta_file, "w") as fh:
            fh.write(json.dumps(stored_meta, indent=4))

    def __get_empty_obj(self, obj):
        empty_self = obj.__class__(self.clade_work_dir, self.conf)
        empty_self.temp_dir = self.temp_dir

        for ext_name in obj.extensions:
            empty_self.extensions[ext_name] = self.__get_empty_obj(
                obj.extensions[ext_name]
            )

        return empty_self

    def execute_in_parallel(
        self,
        objs: Iterable[Any],
        process: Callable[..., Any],
        args: tuple[Any, ...] = (),
        total_objs: int | None = None,
        pass_self: bool = True,
    ) -> None:
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

        # Only this process writes to the database: workers return
        # what they would have written and it is stored here
        with ProcessPoolExecutor(max_workers=max_workers) as p, self.db.transaction():
            chunk_size = 2000
            futures = []
            finished_objs = 0

            # Submit objs to executor in chunks
            for obj_chunk in yield_chunk(objs, chunk_size=chunk_size):
                chunk_futures = []

                for obj in obj_chunk:
                    if pass_self:
                        f = p.submit(_run_buffered, process, empty_self, obj, *args)
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

                        msg = f"Processed {finished_objs} out of {total_objs} [{finished_objs / total_objs * 100:.0f}%]"
                        self.progress(msg)

                    # Check return value of all finished futures.
                    # result() re-raises whatever the worker raised
                    for f in done_futures:
                        rows = f.result()
                        if rows:
                            self.db.put_rows(rows)

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
    def get_all_extensions() -> Generator[type["Extension"], None, None]:
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
    def find_subclass(ext_name: str) -> type["Extension"]:
        """Find a subclass of Interface class."""
        for ext_class in Extension.__get_all_subclasses(Extension):
            if ext_name == ext_class.__name__:
                return ext_class
        raise NotImplementedError(f"Can't find {ext_name!r} class")

    def log(self, message: str) -> None:
        """Print debug message.

        self.conf["log_level"] must be set to INFO or DEBUG in order to see the message.
        """
        self.__get_logger().info(f"{self.name}: {message}")

    def debug(self, message: str) -> None:
        """Print debug message.

        self.conf["log_level"] must be set to DEBUG in order to see the message.

        WARNING: debug messages can have a great impact on the performance.
        """
        self.__get_logger().debug(f"{self.name}: [DEBUG] {message}")

    def warning(self, message: str) -> None:
        """Print warning message.

        self.conf["log_level"] must be set to WARNING, INFO or DEBUG in order to see the message.
        """
        self.__get_logger().warning(f"{self.name}: [WARNING] {message}")

    def error(self, message: str) -> None:
        """Print error message.

        self.conf["log_level"] must be set to ERROR, WARNING, INFO or DEBUG in order to see the message.
        """
        self.__get_logger().error(f"{self.name}: [ERROR] {message}")

    def progress(self, message: str) -> None:
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

        return self.logger
