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

import abc
import os
import shlex
import subprocess
import tempfile

from clade.cmds import get_last_id
from clade.utils import get_logger
from clade.server import PreprocessServer


class Intercept(metaclass=abc.ABCMeta):
    """Object for intercepting and parsing build commands.

    Attributes:
        command: A list of strings representing build command to run and intercept
        cwd: A path to the directory where build command should be executed
        output: A path to the file where intercepted commands will be saved
        append: A boolean allowing to append intercepted commands to already existing file with commands
        conf: dictionary with configuration

    Raises:
        NotImplementedError: Clade is launched on Windows
        RuntimeError: Clade installation is corrupted, or intercepting process failed
    """

    def __init__(self, command, cwd=os.getcwd(), output="cmds.txt", append=False, conf=None):
        self.command = command
        self.cwd = cwd
        self.output = os.path.abspath(output)
        self.append = append
        self.conf = conf if conf else dict()
        self.logger = get_logger("Intercept", self.conf)
        self.env = self._setup_env()

        if not self.append and os.path.exists(self.output):
            os.remove(self.output)

    def _setup_env(self):
        env = dict(os.environ)

        self.logger.debug("Set 'CLADE_INTERCEPT' environment variable value")
        env["CLADE_INTERCEPT"] = self.output

        # Prepare environment variables for PID graph
        if self.append:
            last_used_id = get_last_id(self.output)
        else:
            last_used_id = "0"

        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(last_used_id.encode())
        env["CLADE_ID_FILE"] = f.name
        env["CLADE_PARENT_ID"] = "0"

        return env

    @staticmethod
    def preprocess(execute):
        """Decorator for execute() method

        It runs build command under socket server allowing preprocessing of intercepted build commands
        before their execution by a suitable extension.
        """
        def execute_wrapper(self, *args, **kwargs):
            if not self.conf.get("Intercept.preprocess"):
                return execute(self, *args, **kwargs)

            server = PreprocessServer(self.conf, self.output)

            # self.env.update(server.env) would be wrong
            server_env = server.env.copy()
            server_env.update(self.env)
            self.env = server_env

            self.logger.debug("Start preprocess server")
            server.start()

            try:
                return execute(self, *args, **kwargs)
            finally:
                self.logger.debug("Terminate preprocess server")
                server.terminate()

        return execute_wrapper

    def execute(self):
        """Execute intercepting of build commands.

        Returns:
            0 if everything went successful and error code otherwise
        """

        shell_command = " ".join([shlex.quote(x) for x in self.command])
        self.logger.debug("Execute {!r} command".format(shell_command))
        return subprocess.call(shell_command, env=self.env, shell=True, cwd=self.cwd)
