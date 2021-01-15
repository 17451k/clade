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

import multiprocessing
import threading
import os
import socketserver
import sys
import tempfile

from clade.utils import get_logger
from clade.extensions.abstract import Extension
from clade.cmds import split_cmd, join_cmd

if sys.platform == "linux" or sys.platform == "darwin":
    parent = socketserver.UnixStreamServer
else:
    parent = socketserver.TCPServer


# Forking and threading versions can be created using
# the ForkingMixIn and ThreadingMixIn mix-in classes.
# For instance, a forking CladeSocketServer class is created as follows:
# class SocketServer(ForkingMixIn, parent):
class SocketServer(parent):
    class RequestHandler(socketserver.StreamRequestHandler):
        def handle(self):
            data = self.rfile.readline().strip().decode("utf-8")
            cmd = split_cmd(data)

            for ext in self.extensions:
                ext.preprocess(cmd)

            data = join_cmd(cmd)

            with open(self.output, "a") as clade_fh:
                clade_fh.write(data + "\n")

    def __init__(self, address, output, conf):
        self.process = None
        # Variable to store file object of UNIX socket parent directory
        self.socket_fh = None

        rh = SocketServer.RequestHandler

        rh.output = output

        # Request handler must have access to extensions
        extensions = []
        for cls in Extension.get_all_extensions():
            extensions.append(cls(conf.get("work_dir", "Clade"), conf))
        rh.extensions = extensions

        super().__init__(address, rh)

    def start(self):
        if sys.platform == "win32" or (sys.platform == "darwin" and sys.version_info[1] >= 8):
            self.process = threading.Thread(target=self.serve_forever)
        else:
            self.process = multiprocessing.Process(target=self.serve_forever)
        self.process.daemon = True
        self.process.start()

    def terminate(self):
        # if UNIX socket was used, it's parent directory needs to be closed
        if self.socket_fh:
            self.socket_fh.close()


class PreprocessServer:
    def __init__(self, conf, output):
        self.conf = conf
        self.output = output
        self.logger = get_logger("Server", conf=self.conf)
        self.server = self.__prepare()
        self.env = self.__setup_env()

    def __prepare(self):
        if sys.platform == "linux" or sys.platform == "darwin":
            self.logger.debug("UNIX socket will be used")
            server = self.__prepare_unix()
        else:
            self.logger.debug("INET socket will be used")
            server = self.__prepare_inet()

        return server

    def __prepare_unix(self):
        # Create temporary directory with random name to store UNIX socket
        f = tempfile.TemporaryDirectory()
        name = os.path.join(f.name, "clade.sock")
        self.conf["Server.address"] = name

        server = SocketServer(name, self.output, self.conf)

        # Without this file object will be closed automatically after exiting from this function
        server.sock_fh = f

        return server

    def __prepare_inet(self):
        self.conf["Server.host"] = self.conf.get("Server.host", "localhost")
        self.conf["Server.port"] = self.conf.get("Server.port", "0")

        server = SocketServer(
            (self.conf["Server.host"], int(self.conf["Server.port"])),
            self.output,
            self.conf,
        )

        # If "Server.port" is 0, than dynamic port assignment is used and the value needs to be updated
        self.conf["Server.port"] = str(server.server_address[1])

        return server

    def __setup_env(self):
        env = os.environ.copy()
        # Windows doesn't support UNIX sockets
        if sys.platform == "linux" or sys.platform == "darwin":
            env.update({"CLADE_UNIX_ADDRESS": self.conf["Server.address"]})
        else:
            env.update({"CLADE_INET_HOST": self.conf["Server.host"]})
            env.update({"CLADE_INET_PORT": self.conf["Server.port"]})

        env.update({"CLADE_PREPROCESS": "true"})

        return env

    def start(self):
        # Create separate server process
        self.server.start()

    def terminate(self):
        self.server.terminate()
