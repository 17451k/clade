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
import psycopg2
import sys

from psycopg2 import sql

from clade import Clade
from clade.cmds import iter_cmds


class CladeDB:
    # TODO: change it
    USER = "clade"
    DB = "clade"
    PASSWORD = "clade"

    def __init__(self, work_dir):
        self.clade = Clade(work_dir)
        self.logger = self.clade.logger

        self.connection = psycopg2.connect(user=self.USER, password=self.PASSWORD, database=self.DB)
        self.cursor = self.connection.cursor()

    def get_project_id(self):
        return "clade-_" + self.clade.get_uuid().replace("-", "_")

    def __insert_path(self, path):
        path_sql = "INSERT INTO paths (path) VALUES (%s) ON CONFLICT DO NOTHING"

        self.cursor.execute(path_sql, [path])

    def __get_path_id(self, path):
        select_path_id_sql = "SELECT id FROM paths WHERE path = %s"

        self.cursor.execute(select_path_id_sql, [path])

        return self.cursor.fetchone()[0]

    def clear_tables(self):
        tables = [
            "cmd_opts",
            "cmd_in",
            "cmd_out",
            "cmd_graph",
            "src_compiled_in",
            "src_used_by",
            "parsed_cmds",
            "cmds",
            "paths"
        ]

        for table in tables:
            self.cursor.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))

        self.cursor.connection.commit()

    def import_cmds(self):
        cmd_sql = "INSERT INTO cmds (id, pid, cwd_id, which_id, command) VALUES (%s, %s, %s, %s, %s)"

        for cmd in iter_cmds(self.clade.cmds_file):
            self.__insert_path(cmd["cwd"])
            self.__insert_path(cmd["which"])

            cwd_id = self.__get_path_id(cmd["cwd"])
            which_id = self.__get_path_id(cmd["which"])

            self.cursor.execute(cmd_sql, [
                cmd["id"],
                cmd["pid"],
                cwd_id,
                which_id,
                cmd["command"]
            ])

        self.cursor.connection.commit()

    def import_cmd_graph(self):
        # parsed_cmd_sql = sql.SQL("INSERT INTO parsed_cmds (id, cwd_id, in_id, out_id, opts) VALUES (%s, %s, %s, %s, %s)")
        parsed_cmd_sql = "INSERT INTO parsed_cmds (id, type) VALUES (%s, %s)"
        cmd_opts_sql = "INSERT INTO cmd_opts (id, opts) VALUES (%s, %s)"
        cmd_in_sql = "INSERT INTO cmd_in (cmd_id, in_id) VALUES (%s, %s)"
        cmd_out_sql = "INSERT INTO cmd_out (cmd_id, out_id) VALUES (%s, %s)"
        cmd_graph_sql = "INSERT INTO cmd_graph (cmd_id, used_by) VALUES (%s, %s)"

        cmds = self.clade.get_cmds(with_opts=True)

        for cmd in cmds:
            self.cursor.execute(parsed_cmd_sql, [cmd["id"], cmd["type"]])
            self.cursor.execute(cmd_opts_sql, [cmd["id"], cmd["opts"]])

            for cmd_in in cmd["in"]:
                self.__insert_path(cmd_in)
                in_id = self.__get_path_id(cmd_in)

                self.cursor.execute(cmd_in_sql, [cmd["id"], in_id])

            for cmd_out in cmd["out"]:
                self.__insert_path(cmd_out)
                out_id = self.__get_path_id(cmd_out)

                self.cursor.execute(cmd_out_sql, [cmd["id"], out_id])

        for cmd_id in self.clade.cmd_graph:
            for used_by in self.clade.cmd_graph[cmd_id]["used_by"]:
                self.cursor.execute(cmd_graph_sql, [cmd_id, used_by])

        self.cursor.connection.commit()

    def import_src_graph(self):
        src_graph = self.clade.src_graph

        src_compiled_in_sql = "INSERT INTO src_compiled_in (path_id, cmd_id) VALUES (%s, %s)"
        src_used_by_sql = "INSERT INTO src_used_by (path_id, cmd_id) VALUES (%s, %s)"

        for path in src_graph:
            self.__insert_path(path)
            path_id = self.__get_path_id(path)

            for cmd_id in src_graph[path]["compiled_in"]:
                self.cursor.execute(src_compiled_in_sql, [path_id, cmd_id])

            for cmd_id in src_graph[path]["used_by"]:
                self.cursor.execute(src_used_by_sql, [path_id, cmd_id])

        self.cursor.connection.commit()


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        sys.exit("Please specify path to the Clade working directory")

    work_dir = sys.argv[1]

    if not os.path.isdir(work_dir):
        sys.exit("Specified working directory does not exist")

    c = CladeDB(work_dir)
    c.clear_tables()
    c.import_cmds()
    c.import_cmd_graph()
    c.import_src_graph()
