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

    def __init__(self, command, cwd=os.getcwd(), output: str = "cmds.txt", append=False, intercept_open=False, conf=None):
        self.command = command
        self.cwd = cwd
        self.output = os.path.abspath(output)
        self.output_open = os.path.join(os.path.dirname(self.output), "open.txt")
        self.append = append
        self.intercept_open = intercept_open
        self.conf = conf if conf else dict()

        self.clade_if_file = None
        self.logger = get_logger("Intercept", conf=self.conf)
        self.env = self._setup_env()

        if not self.append:
            if os.path.exists(self.output):
                os.remove(self.output)
            if os.path.exists(self.output_open):
                os.remove(self.output_open)

    def _setup_env(self):
        env = dict(os.environ)

        self.logger.debug("Set 'CLADE_INTERCEPT' environment variable value")
        env["CLADE_INTERCEPT"] = str(self.output)

        if self.intercept_open:
            self.logger.debug("Set 'CLADE_INTERCEPT_OPEN' environment variable value")
            env["CLADE_INTERCEPT_OPEN"] = self.output_open

        # Prepare environment variables for PID graph
        if self.append:
            last_used_id = get_last_id(self.output)
        else:
            last_used_id = "0"

        f = tempfile.NamedTemporaryFile(mode="w", delete=False)
        f.write(last_used_id)
        f.flush()

        self.clade_if_file = f.name
        env["CLADE_ID_FILE"] = self.clade_if_file
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
        r = subprocess.call(shell_command, env=self.env, shell=True, cwd=self.cwd)

        if self.clade_if_file and os.path.exists(self.clade_if_file):
            os.remove(self.clade_if_file)

        return r
