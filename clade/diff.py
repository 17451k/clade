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

import argparse
import logging
import os
import sys

from clade import Clade


# Setup extensions logger
logger = logging.getLogger("Diff")
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s clade %(levelname)s: %(message)s", "%H:%M:%S"
    )
)
logger.addHandler(handler)


class Diff:
    def __init__(self, work_dir1, work_dir2, log_level="INFO"):
        self.work_dir1 = work_dir1
        self.work_dir2 = work_dir2

        self.cl1 = Clade(work_dir1)
        self.cl2 = Clade(work_dir2)

        logger.setLevel(log_level)

    def compare(self):
        self.compare_extension_lists()
        self.compare_pid_graphs()
        self.compare_cmds()
        self.compare_storages()
        self.compare_cmd_graphs()
        self.compare_src_graphs()
        self.compare_functions()
        self.compare_macros()
        self.compare_callgraphs()
        pass

    def compare_extension_lists(self):
        a = self.__get_extension_list(self.work_dir1)
        b = self.__get_extension_list(self.work_dir2)

        if a == b:
            logger.info(
                "Sets of extensions are the same: {!r}".format(", ".join(a))
            )
        else:
            logger.error("Sets of extensions are different")
            logger.error("First  set: {!r}".format(", ".join(a)))
            logger.error("Second set: {!r}".format(", ".join(b)))

    def compare_pid_graphs(self):
        if not self.__ext_work_dirs_exist("PidGraph"):
            return

        keys_are_same = True
        direct_parents_are_same = True
        indirect_parents_are_same = True

        pid_by_id1 = self.cl1.pid_by_id
        pid_by_id2 = self.cl2.pid_by_id

        keys1 = pid_by_id1.keys()
        keys2 = pid_by_id2.keys()

        if keys1 == keys2:
            logger.debug("IDs of intercepted commands are the same")
            common_ids = keys1
        else:
            common_ids = set(keys1) & set(keys2)
            keys_are_same = False

            removed = [x for x in keys1 if x not in common_ids]
            added = [x for x in keys2 if x not in common_ids]

            if removed:
                logger.error(
                    "{!r} ids were removed from the pid graph".format(removed)
                )

            if added:
                logger.error(
                    "{!r}  ids were added to the pid graph".format(added)
                )

        for key in common_ids:
            if pid_by_id1[key] != pid_by_id2[key]:
                logger.error(
                    "ID {!r} has different direct parents: {!r} vs {!r}".format(
                        key, pid_by_id1[key], pid_by_id2[key]
                    )
                )
                direct_parents_are_same = False

        if direct_parents_are_same and keys_are_same:
            logger.debug("All ids have the same direct parents")
        elif direct_parents_are_same and not keys_are_same:
            logger.debug("All common ids have the same direct parents")

        pid_graph1 = self.cl1.pid_graph
        pid_graph2 = self.cl2.pid_graph

        for key in common_ids:
            if pid_graph1[key] != pid_graph2[key]:
                logger.error(
                    "ID {!r} has different indirect parents: {!r} vs {!r}".format(
                        key, pid_graph1[key], pid_graph2[key]
                    )
                )
                indirect_parents_are_same = False

        if indirect_parents_are_same and keys_are_same:
            logger.debug("All ids have the same indirect parents")
        elif indirect_parents_are_same and not keys_are_same:
            logger.debug("All common ids have the same indirect parents")

        if (
            keys_are_same
            and direct_parents_are_same
            and indirect_parents_are_same
        ):
            logger.info("Pid graphs are the same")
        else:
            logger.info("Pid graphs are different")

    def compare_cmds(self):
        if not self.__ext_work_dirs_exist("CmdGraph"):
            return

        keys_are_same = True
        inputs_are_same = True
        outputs_are_same = True
        deps_are_same = True

        cmds1 = self.cl1.cmds
        cmds2 = self.cl2.cmds

        cmd_ids1 = [x["id"] for x in cmds1]
        cmd_ids2 = [x["id"] for x in cmds2]

        if cmd_ids1 == cmd_ids2:
            logger.debug("Sets of parsed commands are the same")
            common_ids = cmd_ids1
        else:
            common_ids = set(cmd_ids1) & set(cmd_ids2)
            keys_are_same = False

            removed = [x for x in cmd_ids1 if x not in common_ids]
            added = [x for x in cmd_ids2 if x not in common_ids]

            for cmd_id in removed:
                logger.error(
                    "{!r} command with ID={!r} was removed".format(
                        self.cl1.get_cmd_type(cmd_id), cmd_id
                    )
                )

            for cmd_id in added:
                logger.error(
                    "{!r} command with ID={!r} was added".format(
                        self.cl2.get_cmd_type(cmd_id), cmd_id
                    )
                )

        for cmd_id in common_ids:
            cmd1 = self.cl1.get_cmd(cmd_id)
            cmd2 = self.cl2.get_cmd(cmd_id)

            if cmd1["in"] != cmd2["in"]:
                logger.error(
                    "{!r} command with ID={!r} changed its input files: {!r} vs {!r}".format(
                        self.cl1.get_cmd_type(cmd_id),
                        cmd_id,
                        cmd1["in"],
                        cmd2["in"],
                    )
                )
                inputs_are_same = False

            if cmd1["out"] != cmd2["out"]:
                logger.error(
                    "{!r} command with ID={!r} changed its output files: {!r} vs {!r}".format(
                        self.cl1.get_cmd_type(cmd_id),
                        cmd_id,
                        cmd1["out"],
                        cmd2["out"],
                    )
                )
                outputs_are_same = False

        common_compilation_cmds_ids = [
            x["id"] for x in self.cl2.compilation_cmds if x["id"] in common_ids
        ]

        for cmd_id in common_compilation_cmds_ids:
            cmd_deps1 = set(
                self.cl1.get_cmd(cmd_id, with_deps=True)["deps"]
            )
            cmd_deps2 = set(
                self.cl2.get_cmd(cmd_id, with_deps=True)["deps"]
            )

            if cmd_deps1 != cmd_deps2:
                removed = cmd_deps1 - cmd_deps2
                added = cmd_deps2 - cmd_deps1

                for dep in removed:
                    logger.error(
                        "{!r} command with ID={!r} no longer has dependency: {!r}".format(
                            self.cl1.get_cmd_type(cmd_id), cmd_id, dep
                        )
                    )

                for dep in added:
                    logger.error(
                        "{!r} command with ID={!r} has new dependency: {!r}".format(
                            self.cl1.get_cmd_type(cmd_id), cmd_id, dep
                        )
                    )

                deps_are_same = False

        if (
            keys_are_same
            and inputs_are_same
            and outputs_are_same
            and deps_are_same
        ):
            logger.info("Parsed commands are the same")
        else:
            logger.info("Parsed commands are different")

    def compare_storages(self):
        if not self.__ext_work_dirs_exist("Storage"):
            return

        storage_files1 = set()
        storage_files2 = set()

        for root, _, filenames in os.walk(self.cl1.storage_dir):
            for filename in filenames:
                storage_files1.add(
                    os.path.relpath(
                        os.path.join(root, filename),
                        start=self.cl1.storage_dir,
                    )
                )

        for root, _, filenames in os.walk(self.cl2.storage_dir):
            for filename in filenames:
                storage_files2.add(
                    os.path.relpath(
                        os.path.join(root, filename),
                        start=self.cl2.storage_dir,
                    )
                )

        if storage_files1 == storage_files2:
            logger.info("Files in the Storage are the same")
        else:
            removed = storage_files1 - storage_files2
            added = storage_files2 - storage_files1

            for file in removed:
                logger.error(
                    "{!r} file was removed from the Storage".format(file)
                )

            for file in added:
                logger.error("{!r} file was added to the Storage".format(file))

    def compare_cmd_graphs(self):
        if not self.__ext_work_dirs_exist("CmdGraph"):
            return

        cmd_graph1 = self.cl1.cmd_graph
        cmd_graph2 = self.cl2.cmd_graph

        used_by_are_same = True
        using_are_same = True

        cmds_ids1 = set(cmd_graph1.keys())
        cmds_ids2 = set(cmd_graph2.keys())

        if cmds_ids1 == cmds_ids2:
            common_ids = cmds_ids1
        else:
            common_ids = cmds_ids1 & cmds_ids2

        for cmd_id in common_ids:
            used_by1 = set(cmd_graph1[cmd_id]["used_by"])
            used_by2 = set(cmd_graph2[cmd_id]["used_by"])

            if used_by1 != used_by2:
                removed = used_by1 - used_by2
                added = used_by2 - used_by1

                if removed:
                    logger.error(
                        "{!r} command with ID={!r} is no longer used by: {!r}".format(
                            cmd_graph1[cmd_id]["type"],
                            cmd_id,
                            ", ".join(removed),
                        )
                    )

                if added:
                    logger.error(
                        "{!r} command with ID={!r} is now used by: {!r}".format(
                            cmd_graph1[cmd_id]["type"],
                            cmd_id,
                            ", ".join(added),
                        )
                    )

                used_by_are_same = False

            using1 = set(cmd_graph1[cmd_id]["using"])
            using2 = set(cmd_graph2[cmd_id]["using"])

            if using1 != using2:
                removed = using1 - using2
                added = using2 - using1

                if removed:
                    logger.error(
                        "{!r} command with ID={!r} is no longer using: {!r}".format(
                            cmd_graph1[cmd_id]["type"],
                            cmd_id,
                            ", ".join(removed),
                        )
                    )

                if added:
                    logger.error(
                        "{!r} command with ID={!r} is now using: {!r}".format(
                            cmd_graph1[cmd_id]["type"],
                            cmd_id,
                            ", ".join(added),
                        )
                    )

                using_are_same = False

        if used_by_are_same and using_are_same:
            logger.info("Cmd graphs are the same")
        else:
            logger.info("Cmd graphs are different")

    def compare_src_graphs(self):
        if not self.__ext_work_dirs_exist("SrcGraph"):
            return

        src_graph1 = self.cl1.src_graph
        src_graph2 = self.cl2.src_graph

        keys_are_same = True
        used_by_are_same = True
        compiled_in_are_same = True

        files1 = set(src_graph1.keys())
        files2 = set(src_graph2.keys())

        if files1 == files2:
            logger.info("Files in the source graph are the same")
            common_files = files1
        else:
            common_files = files1 & files2

            removed = files1 - files2
            added = files2 - files1

            for file in removed:
                logger.error(
                    "{!r} file was removed from the source graph".format(file)
                )

            for file in added:
                logger.error(
                    "{!r} file was added to the source graph".format(file)
                )

            keys_are_same = False

        for file in common_files:
            used_by1 = set(src_graph1[file]["used_by"])
            used_by2 = set(src_graph2[file]["used_by"])

            if used_by1 != used_by2:
                removed = used_by1 - used_by2
                added = used_by2 - used_by1

                if removed:
                    logger.error(
                        "{!r} file is no longer used by {!r} commands".format(
                            file, ", ".join(removed)
                        )
                    )

                if added:
                    logger.error(
                        "{!r} file is now used by {!r} commands".format(
                            file, ", ".join(added)
                        )
                    )

                used_by_are_same = False

            compiled_in1 = set(src_graph1[file]["compiled_in"])
            compiled_in2 = set(src_graph1[file]["compiled_in"])

            if compiled_in1 != compiled_in2:
                removed = compiled_in1 - compiled_in2
                added = compiled_in2 - compiled_in1

                if removed:
                    logger.error(
                        "{!r} file is no longer compiled in {!r} commands".format(
                            file, ", ".join(removed)
                        )
                    )

                if added:
                    logger.error(
                        "{!r} file is now compiled in {!r} commands".format(
                            file, ", ".join(added)
                        )
                    )

                compiled_in_are_same = False

        if keys_are_same and used_by_are_same and compiled_in_are_same:
            logger.info("Source graphs are the same")
        else:
            logger.info("Source graphs are different")

    def compare_functions(self):
        if not self.__ext_work_dirs_exist("Functions"):
            return

        keys_are_same = True
        types_are_same = True
        lines_are_same = True
        signatures_are_same = True
        decls_are_same = True

        f1 = self.cl1.functions_by_file
        f2 = self.cl2.functions_by_file

        keys1 = set()
        keys2 = set()

        for file in f1:
            for func in f1[file]:
                keys1.add((file, func))

        for file in f2:
            for func in f2[file]:
                keys2.add((file, func))

        if keys1 == keys2:
            common_keys = keys2
        else:
            common_keys = keys1 & keys2

            removed = keys1 - keys2
            added = keys2 - keys1

            for file, func in removed:
                logger.error(
                    "{!r} function from {!r} file was removed".format(
                        func, file
                    )
                )

            for file, func in added:
                logger.error(
                    "{!r} function from {!r} file was added".format(func, file)
                )

            keys_are_same = False

        for file, func in common_keys:
            type1 = f1[file][func]["type"]
            type2 = f2[file][func]["type"]

            if type1 != type2:
                logger.error(
                    "{!r} function from {!r} file changed its type from {!r} to {!r}".format(
                        func, file, type1, type2
                    )
                )

                types_are_same = False

            line1 = f1[file][func]["line"]
            line2 = f2[file][func]["line"]

            if line1 != line2:
                logger.error(
                    "{!r} function from {!r} file changed its definition line from {!r} to {!r}".format(
                        func, file, line1, line2
                    )
                )

                lines_are_same = False

            signature1 = f1[file][func]["signature"]
            signature2 = f2[file][func]["signature"]

            if signature1 != signature2:
                logger.error(
                    "{!r} function from {!r} file changed its signature from {!r} to {!r}".format(
                        func, file, signature1, signature2
                    )
                )

                signatures_are_same = False

            if f1[file][func]["declarations"]:
                decl_files1 = set(f1[file][func]["declarations"].keys())
            else:
                decl_files1 = set()
            if f2[file][func]["declarations"]:
                decl_files2 = set(f2[file][func]["declarations"].keys())
            else:
                decl_files2 = set()

            if decl_files1 == decl_files2:
                common_decl_files = decl_files2
            else:
                common_decl_files = decl_files1 & decl_files2

                removed = decl_files1 - decl_files2
                added = decl_files2 - decl_files1

                for decl_file in removed:
                    logger.error(
                        "{!r} function from {!r} file no longer has declaration in {!r}".format(
                            func, file, decl_file
                        )
                    )

                for decl_file in added:
                    logger.error(
                        "{!r} function from {!r} file has new declaration in {!r}".format(
                            func, file, decl_file
                        )
                    )

                decls_are_same = False

            for decl_file in common_decl_files:
                decl1 = f1[file][func]["declarations"][decl_file]
                decl2 = f2[file][func]["declarations"][decl_file]

                line1 = decl1["line"]
                line2 = decl2["line"]

                if line1 != line2:
                    logger.error(
                        "{!r} function from {!r} file changed its declaration line from {!r} to {!r}".format(
                            func, file, line1, line2
                        )
                    )
                    decls_are_same = False

                signature1 = decl1["signature"]
                signature2 = decl2["signature"]

                if signature1 != signature2:
                    logger.error(
                        "{!r} function from {!r} file changed its declaration signature from {!r} to {!r}".format(
                            func, file, signature1, signature2
                        )
                    )

                    decls_are_same = False

                type1 = decl1["type"]
                type2 = decl2["type"]

                if type1 != type2:
                    logger.error(
                        "{!r} function from {!r} file changed its declaration type from {!r} to {!r}".format(
                            func, file, type1, type2
                        )
                    )

                    decls_are_same = False

        if (
            keys_are_same
            and types_are_same
            and lines_are_same
            and signatures_are_same
            and decls_are_same
        ):
            logger.info("Functions are the same")
        else:
            logger.info("Functions are different")

    def compare_macros(self):
        if not self.__ext_work_dirs_exist("Macros"):
            return

        exp_files_are_same = True
        exp_names_are_same = True
        exp_args_are_same = True

        exp1 = self.cl1.get_macros_expansions()
        exp2 = self.cl2.get_macros_expansions()

        exp_files1 = set(exp1)
        exp_files2 = set(exp2)

        if exp_files1 == exp_files2:
            common_exp_files = exp_files2
        else:
            common_exp_files = exp_files1 & exp_files2

            removed = exp_files1 - exp_files2
            added = exp_files2 - exp_files1

            for exp_file in removed:
                logger.error(
                    "{!r} file was removed from macros expansions".format(
                        exp_file
                    )
                )

            for exp_file in added:
                logger.error(
                    "{!r} file was added to macros expansions".format(exp_file)
                )

            exp_files_are_same = False

        for exp_file in common_exp_files:
            exp_names1 = set(exp1[exp_file])
            exp_names2 = set(exp2[exp_file])

            if exp_names1 == exp_names2:
                common_exp_names = exp_names2
            else:
                common_exp_names = exp_names1 & exp_names2

                removed = exp_names1 - exp_names2
                added = exp_names2 - exp_names1

                for exp_name in removed:
                    logger.error(
                        "Expansion of macro {!r} from {!r} file was removed".format(
                            exp_name, exp_file
                        )
                    )

                for exp_name in added:
                    logger.error(
                        "Expansion of macro {!r} from {!r} file was added".format(
                            exp_name, exp_file
                        )
                    )

                exp_names_are_same = False

            for exp_name in common_exp_names:
                args1 = set([x for sublist in exp1[exp_file][exp_name]["args"] for x in sublist])
                args2 = set([x for sublist in exp2[exp_file][exp_name]["args"] for x in sublist])

                if args1 != args2:
                    removed = args1 - args2
                    added = args2 - args1

                    for args in removed:
                        logger.error(
                            "Macro {!r} from {!r} file no longer has these expansion args: {!r}".format(
                                exp_name, exp_file, args
                            )
                        )

                    for args in added:
                        logger.error(
                            "Macro {!r} from {!r} file now has new expansion args: {!r}".format(
                                exp_name, exp_file, args
                            )
                        )

                    exp_args_are_same = False

        if exp_files_are_same and exp_names_are_same and exp_args_are_same:
            logger.info("Macros expansions are the same")
        else:
            logger.info("Macros expansions are different")

        def1 = self.cl1.get_macros_definitions()
        def2 = self.cl2.get_macros_definitions()

        def_files_are_same = True
        def_names_are_same = True
        def_lines_are_same = True

        def_files1 = set(def1)
        def_files2 = set(def2)

        if def_files1 == def_files2:
            common_def_files = def_files2
        else:
            common_def_files = def_files1 & def_files2

            removed = def_files1 - def_files2
            added = def_files2 - def_files1

            for def_file in removed:
                logger.error(
                    "{!r} file was removed from macros definitions".format(
                        def_file
                    )
                )

            for def_file in added:
                logger.error(
                    "{!r} file was added to macros definitions".format(
                        def_file
                    )
                )

            def_files_are_same = False

        for def_file in common_def_files:
            def_names1 = set(def1[def_file])
            def_names2 = set(def1[def_file])

            if def_names1 == def_names2:
                common_def_names = def_names2
            else:
                common_def_names = def_names1 & def_names2

                removed = def_names1 - def_names2
                added = def_names2 - def_names1

                for def_name in removed:
                    logger.error(
                        "Definition of macro {!r} from {!r} file was removed".format(
                            def_name, def_file
                        )
                    )

                for def_name in added:
                    logger.error(
                        "Definition of macro {!r} from {!r} file was added".format(
                            def_name, def_file
                        )
                    )

                def_names_are_same = False

            for def_name in common_def_names:
                lines1 = def1[def_file][def_name]
                lines2 = def1[def_file][def_name]

                if lines1 != lines2:
                    removed = lines1 - lines2
                    added = lines2 - lines1

                    for line in removed:
                        logger.error(
                            "Macro {!r} from {!r} file no longer has definition on line {!r}".format(
                                def_name, def_file, line
                            )
                        )

                    for line in added:
                        logger.error(
                            "Macro {!r} from {!r} file now has definition on line {!r}".format(
                                def_name, def_file, line
                            )
                        )

                    def_lines_are_same = False

        if def_files_are_same and def_names_are_same and def_lines_are_same:
            logger.info("Macros definitions are the same")
        else:
            logger.info("Macros definitions are different")

    def compare_callgraphs(self):
        if not self.__ext_work_dirs_exist("Callgraph"):
            return

        files_are_same = True
        funcs_are_same = True
        called_in_files_are_same = True
        called_in_funcs_are_same = True
        call_lines_are_same = True
        match_types_are_same = True

        c1 = self.cl1.callgraph
        c2 = self.cl2.callgraph

        files1 = set(c1)
        files2 = set(c2)

        if files1 == files2:
            common_files = files2
        else:
            common_files = files1 & files2

            removed = files1 - files2
            added = files2 - files1

            for file in removed:
                logger.error(
                    "{!r} file was removed from the callgraph".format(file)
                )

            for file in added:
                logger.error(
                    "{!r} file was added to the callgraph".format(file)
                )

            files_are_same = False

        for file in common_files:
            funcs1 = set(c1[file])
            funcs2 = set(c2[file])

            if funcs1 == funcs2:
                common_funcs = funcs2
            else:
                common_funcs = funcs1 & funcs2

                removed = funcs1 - funcs2
                added = funcs2 - funcs1

                for func in removed:
                    logger.error(
                        "{!r} function from {!r} file was removed from the callgraph".format(
                            func, file
                        )
                    )

                for func in added:
                    logger.error(
                        "{!r} function from {!r} file was added to the callgraph".format(
                            func, file
                        )
                    )

            for func in common_funcs:
                called_in_files1 = set(c1[file][func].get("called_in", []))
                called_in_files2 = set(c2[file][func].get("called_in", []))

                if called_in_files1 == called_in_files2:
                    common_called_in_files = called_in_files2
                else:
                    common_called_in_files = (
                        called_in_files1 & called_in_files2
                    )

                    removed = called_in_files1 - called_in_files2
                    added = called_in_files2 - called_in_files1

                    for called_in_file in removed:
                        logger.error(
                            "{!r} function from {!r} file is no longer called in {!r} file".format(
                                func, file, called_in_file
                            )
                        )

                    for called_in_file in added:
                        logger.error(
                            "{!r} function from {!r} file is now called in {!r} file".format(
                                func, file, called_in_file
                            )
                        )

                    called_in_files_are_same = False

                for called_in_file in common_called_in_files:
                    called_in_funcs1 = set(
                        c1[file][func]["called_in"][called_in_file]
                    )
                    called_in_funcs2 = set(
                        c2[file][func]["called_in"][called_in_file]
                    )

                    if called_in_funcs1 == called_in_funcs2:
                        common_called_in_funcs = called_in_funcs2
                    else:
                        common_called_in_funcs = (
                            called_in_funcs1 & called_in_funcs2
                        )

                        removed = called_in_funcs1 - called_in_funcs2
                        added = called_in_funcs2 - called_in_funcs1

                        for called_in_func in removed:
                            logger.error(
                                "{!r} function from {!r} file is no longer called in {!r} func from {!r} file".format(
                                    func, file, called_in_func, called_in_file
                                )
                            )

                        for called_in_func in added:
                            logger.error(
                                "{!r} function from {!r} file is now called in {!r} func from {!r} file".format(
                                    func, file, called_in_func, called_in_file
                                )
                            )

                        called_in_funcs_are_same = False

                    for called_in_func in common_called_in_funcs:
                        call_lines1 = set(
                            c1[file][func]["called_in"][called_in_file][
                                called_in_func
                            ]
                        )
                        call_lines2 = set(
                            c2[file][func]["called_in"][called_in_file][
                                called_in_func
                            ]
                        )

                        if call_lines1 == call_lines2:
                            common_call_lines = call_lines2
                        else:
                            common_call_lines = call_lines1 & call_lines2

                            removed = call_lines1 - call_lines2
                            added = call_lines2 - call_lines1

                            for call_line in removed:
                                logger.error(
                                    "{!r} function from {!r} file is no longer called in {!r} func from {!r} file on line {!r}".format(
                                        func,
                                        file,
                                        called_in_func,
                                        called_in_file,
                                        call_line,
                                    )
                                )

                            for call_line in added:
                                logger.error(
                                    "{!r} function from {!r} file is now called in {!r} func from {!r} file on line {!r}".format(
                                        func,
                                        file,
                                        called_in_func,
                                        called_in_file,
                                        call_line,
                                    )
                                )

                            call_lines_are_same = False

                        if common_call_lines:
                            call_line = list(common_call_lines)[0]

                            match_type1 = c1[file][func]["called_in"][called_in_file][called_in_func][call_line]["match_type"]
                            match_type2 = c2[file][func]["called_in"][called_in_file][called_in_func][call_line]["match_type"]

                            if match_type1 != match_type2:
                                logger.error(
                                    "Match type of {!r} ({!r}) call in {!r} ({!r}) was changed from {!r} to {!r}".format(
                                        func,
                                        file,
                                        called_in_func,
                                        called_in_file,
                                        match_type1,
                                        match_type2,
                                    )
                                )

                                match_types_are_same = False

        if (
            files_are_same
            and funcs_are_same
            and called_in_files_are_same
            and called_in_funcs_are_same
            and call_lines_are_same
            and match_types_are_same
        ):
            logger.info("Callgraphs are the same")
        else:
            logger.info("Callgraphs are different")

    @staticmethod
    def __get_extension_list(work_dir):
        return [f for f in os.listdir(work_dir) if os.path.isdir(os.path.join(work_dir, f))]

    def __ext_work_dirs_exist(self, ext_name):
        a = os.path.join(self.work_dir1, ext_name)
        b = os.path.join(self.work_dir2, ext_name)

        if os.path.exists(a) and os.path.exists(b):
            return True
        else:
            return False


def parse_argv(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument("work_dir1", metavar="<folder>")
    parser.add_argument("work_dir2", metavar="<folder>")

    parser.add_argument(
        "-l",
        "--log-level",
        help="set logging level (ERROR, INFO, or DEBUG)",
        metavar="LEVEL",
        default="INFO",
    )

    return parser.parse_args(argv)


def main(argv=sys.argv[1:]):
    args = parse_argv(argv)

    d = Diff(args.work_dir1, args.work_dir2, log_level=args.log_level)
    d.compare()


if __name__ == "__main__":
    main(sys.argv[1:])
