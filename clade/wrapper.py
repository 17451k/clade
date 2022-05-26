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

import os
import tempfile
import shutil
import sys

from clade.abstract import Intercept


class Wrapper(Intercept):
    def __init__(self, command, cwd=os.getcwd(), output="cmds.txt", append=False, intercept_open=False, intercept_envs=False, conf=None):
        if intercept_open:
            raise RuntimeError("wrappers can't be used to intercept open()")

        self.wrappers_dir = tempfile.mkdtemp()

        super().__init__(command, cwd=cwd, output=output, append=append, intercept_open=intercept_open, intercept_envs=intercept_envs, conf=conf)

        self.wrapper = self.__find_wrapper()
        self.wrapper_postfix = ".clade"

    def _setup_env(self):
        env = super()._setup_env()

        env["PATH"] = self.wrappers_dir + os.pathsep + os.environ.get("PATH", "")
        self.logger.debug("Add directory with wrappers to PATH: {!r}".format(self.wrappers_dir))

        return env

    def __find_wrapper(self):
        wrapper = os.path.join(os.path.dirname(__file__), "intercept", "wrapper")

        if not os.path.exists(wrapper):
            raise RuntimeError("wrapper is not found in {!r}".format(wrapper))

        self.logger.debug("Path to the wrapper: {!r}".format(wrapper))

        return wrapper

    def __create_wrappers(self):
        self.__create_path_wrappers()
        self.__create_exe_wrappers()

    def __create_path_wrappers(self):
        self.logger.debug("Create temporary directory for wrappers: {!r}".format(self.wrappers_dir))

        if os.path.exists(self.wrappers_dir):
            shutil.rmtree(self.wrappers_dir)

        os.makedirs(self.wrappers_dir)

        paths = os.environ.get("PATH", "").split(os.pathsep)

        counter = 0
        self.logger.debug("Walk through every directory in PATH to create wrappers: {!r}".format(paths))
        for path in paths:
            try:
                for file in os.listdir(path):
                    if os.access(os.path.join(path, file), os.X_OK):
                        try:
                            os.symlink(self.wrapper, os.path.join(self.wrappers_dir, file))
                            counter += 1
                        except FileExistsError:
                            continue
            except (FileNotFoundError, PermissionError):
                continue

        self.logger.debug("{} path wrappers were created".format(counter))

    def __create_exe_wrappers(self):
        wrap_list = self.conf.get("Wrapper.wrap_list", [])
        self.logger.debug("Wrap list: {!r}".format(wrap_list))

        for path in wrap_list:
            if os.path.isfile(path):
                self.__create_exe_wrapper(path)
            elif os.path.isdir(path):
                if self.conf.get("Wrapper.recursive_wrap"):
                    for root, _, filenames in os.walk(path):
                        for filename in filenames:
                            self.__create_exe_wrapper(os.path.join(root, filename))
                else:
                    for file in os.listdir(path):
                        self.__create_exe_wrapper(os.path.join(path, file))
            else:
                self.logger.error("{!r} file or directory from 'Wrapper.wrap_list' option does not exist".format(path))
                sys.exit(-1)

    def __create_exe_wrapper(self, path):
        if not(os.path.isfile(path) and os.access(path, os.X_OK) and not os.path.basename(path) == "wrapper"):
            return

        self.logger.debug("Create exe wrapper: {!r}".format(path))

        try:
            os.rename(path, path + self.wrapper_postfix)
            os.symlink(self.wrapper, path)
        except PermissionError:
            self.logger.warning("You do not have permissions to modify {!r}".format(path))
        except Exception as e:
            self.logger.warning(e)

    def __delete_wrappers(self):
        self.logger.debug("Delete temporary directory with wrappers: {!r}".format(self.wrappers_dir))

        if os.path.exists(self.wrappers_dir):
            shutil.rmtree(self.wrappers_dir)

        self.logger.debug("Delete all other wrapper files")
        wrap_list = self.conf.get("Wrapper.wrap_list", [])

        for path in wrap_list:
            if os.path.isfile(path):
                self.__delete_exe_wrapper(path)
            elif os.path.isdir(path):
                if self.conf.get("Wrapper.recursive_wrap"):
                    for root, _, filenames in os.walk(path):
                        for filename in filenames:
                            self.__delete_exe_wrapper(os.path.join(root, filename))
                else:
                    for file in os.listdir(path):
                        self.__delete_exe_wrapper(os.path.join(path, file))

    def __delete_exe_wrapper(self, path):
        if not(os.path.isfile(path) and os.access(path, os.X_OK) and not path.endswith(self.wrapper_postfix)):
            return

        try:
            if os.path.isfile(path + self.wrapper_postfix):
                self.logger.debug("Delete exe wrapper: {!r}".format(path))
                os.remove(path)
                os.rename(path + self.wrapper_postfix, path)
        except PermissionError:
            return
        except Exception as e:
            self.logger.warning(e)

    @Intercept.preprocess
    def execute(self):
        try:
            self.__create_wrappers()

            return super().execute()
        finally:
            self.__delete_wrappers()
