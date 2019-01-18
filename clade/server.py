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
import os
import socket
import socketserver
import sys
import tempfile

from clade.utils import get_logger

if sys.platform == 'linux' or sys.platform == 'darwin':
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

            with open(self.output, "a") as clade_fh:
                clade_fh.write(data + "\n")

            # for ext in self.extensions:
            #     data = ext.preprocess(data)
            # self.wfile.write(data)

    def __init__(self, address, output, extensions):
        self.process = None
        # Variable to store file object of UNIX socket parent directory
        self.socket_fh = None

        rh = SocketServer.RequestHandler

        rh.output = output

        # Request handler must have access to extensions
        rh.extensions = extensions

        super().__init__(address, rh)

    def start(self):
        self.process = multiprocessing.Process(target=self.serve_forever)

        self.process.start()

    def terminate(self):
        # if UNIX socket was used, it's parent directory needs to be closed
        if self.socket_fh:
            self.socket_fh.close()

        self.process.terminate()


class PreprocessServer():
    def __init__(self, conf, output, extensions):
        self.conf = conf
        self.output = output
        self.extensions = extensions
        self.logger = get_logger("Server", self.conf)
        self.server = self.__prepare()

    def __prepare(self):
        if sys.platform == 'linux' or sys.platform == 'darwin':
            self.logger.debug("UNIX socket will be used")
            server = self.__prepare_unix()
        else:
            self.logger.debug("INET socket will be used")
            server = self.__prepare_inet()

        self.__setup_env()

        return server

    def __prepare_unix(self):
        # Create temporary directory with random name to store UNIX socket
        f = tempfile.TemporaryDirectory()
        name = os.path.join(f.name, "clade.sock")
        self.conf["Server.address"] = name

        server = SocketServer(name, self.output, self.extensions)

        # Without this file object will be closed automatically after exiting from this function
        server.sock_fh = f

        return server

    def __prepare_inet(self):
        self.conf["Server.host"] = self.conf.get("Server.host", "localhost")
        self.conf["Server.port"] = self.conf.get("Server.port", "0")

        server = SocketServer((self.conf["Server.host"], int(self.conf["Server.port"])), self.output, self.extensions)

        # If "Server.port" is 0, than dynamic port assignment is used and the value needs to be updated
        self.conf["Server.port"] = str(server.server_address[1])

        return server

    def __setup_env(self):
        # Windows doesn't support UNIX sockets
        if sys.platform == 'linux' or sys.platform == 'darwin':
            os.environ.update({'CLADE_UNIX_ADDRESS': self.conf["Server.address"]})
        else:
            os.environ.update({'CLADE_INET_HOST': self.conf["Server.host"]})
            os.environ.update({'CLADE_INET_PORT': self.conf["Server.port"]})

        os.environ.update({'CLADE_PREPROCESS': "true"})

    def start(self):
        # Create separate server process
        self.server.start()

    def terminate(self):
        self.server.terminate()

    def __send_message(self, message):
        if sys.platform == 'linux' or sys.platform == 'darwin':
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.conf["Server.address"])
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.conf["Server.host"], int(self.conf["Server.port"])))

        sock.sendall(bytes("{}\n".format(message), "utf-8"))

        # Wait until the server finishes all internal extensions
        sock.recv(1024)
