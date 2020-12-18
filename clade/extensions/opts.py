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

# These are options like "-include header.h" with space betwen option and value
# Options with values that are not separated by space should not be included here

import os
import re

gcc_opts = [
    "-x",
    "-o",
    "-aux-info",
    "-auxbase-strip",
    "-D",
    "-U",
    "-include",
    "-imacros",
    "-MF",
    "-MD",
    "-MT",
    "-MQ",
    "-Xpreprocessor",
    "-Xassembler",
    "-l",
    "-Xlinker",
    "-T",
    "-u",
    "-z",
    "-I",
    "-iquote",
    "-isystem",
    "-idirafter",
    "-iprefix",
    "-iwithprefix",
    "-iwithprefixbefore",
    "-isysroot",
    "-imultilib",
    "-imultiarch",
    "-auxbase",
    "-dumpbase",
    "-G",
]

clang_opts = [
    "--CLASSPATH",
    "--assert",
    "--bootclasspath",
    "--classpath",
    "--config",
    "--define-macro",
    "--dyld-prefix",
    "--encoding",
    "--extdirs",
    "--for-linker",
    "--force-link",
    "--include-directory",
    "--include-directory-after",
    "--include-prefix",
    "--include-with-prefix",
    "--include-with-prefix-after",
    "--include-with-prefix-before",
    "--language",
    "--library-directory",
    "--mhwdiv",
    "--output",
    "--output-class-directory",
    "--param",
    "--prefix",
    "--print-file-name",
    "--print-prog-name",
    "--resource",
    "--rtlib",
    "--serialize-diagnostics",
    "--std",
    "--stdlib",
    "--sysroot",
    "--system-header-prefix",
    "--target",
    "--undefine-macro",
    "-F",
    "-I",
    "-MQ",
    "-MT",
    "-Wa-Wl-Wp-Xanalyzer",
    "-Xanalyzer",
    "-Xarch_device",
    "-Xarch_host",
    "-Xassembler",
    "-Xclang",
    "-Xcuda-fatbinary",
    "-Xcuda-ptxas",
    "-Xlinker",
    "-Xopenmp-target",
    "-Xopenmp-target=<triple>",
    "-Xpreprocessor",
    "-add-plugin",
    "-allowable_client",
    "-analyze-function",
    "-analyzer-checker",
    "-analyzer-config",
    "-analyzer-constraints",
    "-analyzer-disable-checker",
    "-analyzer-inline-max-function-size",
    "-analyzer-inline-max-stack-depth",
    "-analyzer-inlining-mode",
    "-analyzer-ipa",
    "-analyzer-max-loop",
    "-analyzer-max-nodes",
    "-analyzer-output",
    "-analyzer-purge",
    "-analyzer-store",
    "-arch",
    "-arch_only",
    "-arcmt-migrate-report-output",
    "-ast-dump-filter",
    "-ast-merge",
    "-backend-option",
    "-bundle_loader",
    "-c-isystem",
    "-chain-include",
    "-code-completion-at",
    "-coverage-file",
    "-coverage-notes-file",
    "-cxx-abi",
    "-cxx-isystem",
    "-dependency-dot",
    "-dependency-file",
    "-diagnostic-log-file",
    "-dump-build-information",
    "-dwarf-debug-flags",
    "-dwarf-debug-producer",
    "-dylib_file",
    "-error-on-deserialized-decl",
    "-exported_symbols_list",
    "-fconstant-string-class",
    "-fconstexpr-backtrace-limit",
    "-fconstexpr-depth",
    "-fdebug-compilation-dir",
    "-fdiagnostics-format",
    "-fdiagnostics-show-category",
    "-ferror-limit",
    "-filelist",
    "-filetype",
    "-fmacro-backtrace-limit",
    "-fmessage-length",
    "-fmodule-cache-path",
    "-fmodule-implementation-of",
    "-fmodule-name",
    "-fnew-alignment",
    "-force_load",
    "-fprofile-remapping-file",
    "-framework",
    "-frewrite-map-file",
    "-ftabstop",
    "-ftemplate-backtrace-limit",
    "-ftemplate-depth",
    "-ftrapv-handler",
    "-fvisibility",
    "-gcc-toolchain",
    "-header-include-file",
    "-idirafter",
    "-iframework",
    "-imacros",
    "-image_base",
    "-imultilib",
    "-include",
    "-include-pch",
    "-include-pth",
    "-init",
    "-ino-system-prefix",
    "-install_name",
    "-internal-externc-isystem",
    "-internal-isystem",
    "-iprefix",
    "-iquote",
    "-isysroot",
    "-isystem",
    "-isystem-prefix",
    "-iwithprefix",
    "-iwithprefixbefore",
    "-iwithsysroot",
    "-lazy_framework",
    "-lazy_library",
    "-load",
    "-main-file-name",
    "-mcode-model",
    "-mdebug-pass",
    "-meabi",
    "-mfloat-abi",
    "-mlimit-float-precision",
    "-mlink-bitcode-file",
    "-mllvm",
    "-module-dependency-dir",
    "-mregparm",
    "-mrelocation-model",
    "-mt-migrate-directory",
    "-mthread-model",
    "-multiply_defined",
    "-multiply_defined_unused",
    "-o",
    "-objc-isystem",
    "-objcxx-isystem",
    "-pic-level",
    "-pie-level",
    "-plugin-arg-plugin",
    "-print-file-name-print-prog-name-remap-file",
    "-read_only_relocs",
    "-resource-dir",
    "-rpath",
    "-sectalign",
    "-sectcreate",
    "-sectobjectsymbols",
    "-sectorder",
    "-seg_addr_table",
    "-seg_addr_table_filename",
    "-segaddr",
    "-segcreate",
    "-segprot",
    "-segs_read_only_addr",
    "-segs_read_write_addr",
    "-serialize-diagnostic-file",
    "-serialize-diagnostics",
    "-stack-protector",
    "-stack-protector-buffer-size",
    "-std",
    "-stdlib",
    "-target",
    "-target-abi",
    "-target-cpu",
    "-target-feature",
    "-target-linker-version",
    "-token-cache",
    "-triple",
    "-umbrella",
    "-unexported_symbols_list",
    "-weak_framework",
    "-weak_library",
    "-weak_reference_mismatches",
    "-working-directory",
    "-x",
    "-z"
]

cc_preprocessor_opts = [
    "-E",
    "-M",
    "-MM",
    "-MF",
    "-MG",
    "-MT",
    "-MQ",
    "-MD",
    "-dependency-file",
]

# Warning: --start-group archives --end-group options are not supported
ld_gnu_opts = [
    "--audit",
    "--bank-window",
    "--base-file",
    "--dll-search-prefix",
    "--exclude-libs",
    "--exclude-modules-for-implib",
    "--exclude-symbols",
    "--heap",
    "--image-base",
    "--major-image-version",
    "--major-os-version",
    "--major-subsystem-version",
    "--minor-image-version",
    "--minor-os-version",
    "--minor-subsystem-version",
    "--output-def",
    "--out-implib",
    "--stack",
    "--subsystem",
    "--library-path",
    "--library",
    "-A",
    "-F",
    "-G",
    "-L",
    "-O",
    "-P",
    "-R",
    "-T",
    "-Y",
    "-a",
    "-assert",
    "-b",
    "-c",
    "-dT",
    "-e",
    "-f",
    "-h",
    "-l",
    "-m",
    "-o",
    "-u",
    "-y",
    "-z",
    "-plugin",
    "-dynamic-linker",
]

# Warning: next options are not supported:
# -alias symbol_name alternate_symbol_name option is not supported
# -move_to_rw_segment segment_name filename
# -move_to_ro_segment segment_name filename
# -rename_section orgSegment orgSection newSegment newSection
# -rename_segment orgSegment newSegment
# -section_order segname colon_separated_section_list
# -sectalign segname sectname value
# -segprot segname max_prot init_prot
# -sectobjectsymbols segname sectname
# -sectorder segname sectname orderfile
ld_osx_opts = [
    "-A",
    "-U",
    "-Y",
    "-alias_list",
    "-allowable_client",
    "-arch",
    "-bitcode_symbol_map",
    "-bundle_loader",
    "-cache_path_lto",
    "-client_name",
    "-commons",
    "-compatibility_version",
    "-current_version",
    "-dirty_data_list",
    "-dot",
    "-dtrace",
    "-dylib_file",
    "-dylinker_install_name",
    "-e",
    "-exported_symbol",
    "-exported_symbols_list",
    "-exported_symbols_order",
    "-filelist",
    "-final_output",
    "-force_load",
    "-framework",
    "-headerpad",
    "-image_base",
    "-init",
    "-install_name",
    "-interposable_list",
    "-ios_version_min",
    "-lazy_framework",
    "-lazy_library",
    "-lto_library",
    "-macosx_version_min",
    "-max_default_common_align",
    "-max_relative_cache_size_lto",
    "-map",
    "-multiply_defined",
    "-multiply_defined_unused",
    "-non_global_symbols_no_strip_list",
    "-non_global_symbols_strip_list",
    "-o",
    "-object_path_lto",
    "-order_file",
    "-pagezero_size",
    "-prune_after_lto",
    "-prune_interval_lto",
    "-read_only_relocs",
    "-reexported_symbols_list",
    "-sect_diff_relocs",
    "-seg_addr_table",
    "-seg_addr_table_filename",
    "-segaddr",
    "-segalign",
    "-segment_order",
    "-seg_page_size",
    "-segs_read_only_addr",
    "-segs_read_write_addr",
    "-stack_size",
    "-sub_library",
    "-sub_umbrella",
    "-syslibroot",
    "-reexport_framework",
    "-reexport_library",
    "-rpath",
    "-sectcreate",
    "-stack_addr",
    "-u",
    "-umbrella",
    "-undefined",
    "-unexported_symbol",
    "-unexported_symbols_list",
    "-upward_framework",
    "-upward_library",
    "-weak_framework",
    "-weak_library",
    "-weak_reference_mismatches",
    "-why_live",
]

# Warning: Input files may be separated from options by "--": -- | files ...
as_gnu_opts = ["--debug-prefix-map", "--defsym", "-I", "-o"]

as_osx_opts = ["-arch", "-o"]

objcopy_opts = [
    "--add-section",
    "--adjust-vma",
    "--adjust-section-vma",
    "--adjust-start",
    "--change-addresses",
    "--change-section-address",
    "--change-section-lma",
    "--change-section-vma",
    "--change-start",
    "--file-alignment",
    "--gap-fill",
    "--heap",
    "--image-base",
    "--long-section-names",
    "--redefine-sym",
    "--rename-section",
    "--section-alignment",
    "--set-section-flags",
    "--set-start",
    "--stack",
    "--subsystem",
    "-B",
    "-F",
    "-G",
    "-I",
    "-K",
    "-L",
    "-N",
    "-O",
    "-R",
    "-W",
    "-b",
    "-i",
    "-j",
]

cl_opts = [
    "/analyze:log",
    "-analyze:log",
    "/analyze:stacksize",
    "-analyze:stacksize",
    "/analyze:max_paths",
    "-analyze:max_paths",
    "/D",
    "-D",
    "/F",
    "-F",
    "/FI",
    "-FI",
    "/FU",
    "-FU",
    "/I",
    "-I",
    "/link",
    "-link",
    "/Tc",
    "-Tc",
    "/Tp",
    "-Tp",
    "/U",
    "-U",
]

cl_preprocessor_deps_opts = ["/EP", "-EP", "/E", "-E", "/P", "-P"]

requires_value = {
    "CC": set(gcc_opts + clang_opts),
    "CXX": set(gcc_opts + clang_opts),
    "LD": set(ld_gnu_opts + ld_osx_opts),
    "AS": set(as_gnu_opts + as_osx_opts),
    "Objcopy": set(objcopy_opts),
    "CL": set(cl_opts),
    "Link": set(),
}

cif_include_opts = [
    "-include",
    "-I",
    "-iquote",
    "-isystem",
    "-idirafter",
    "-imacros",
    "-isysroot",
]

gcc_optimization_opts = [
    "-O",
    "-O1",
    "-O2",
    "-O3",
    "-O0",
    "-Os",
    "-Ofast",
    "-Og",
]

cif_supported_opts = (
    ["-D", "-U", "-nostdinc", "-fshort-wchar", "-std", "--std"]
    + ["{}$".format(opt) for opt in gcc_optimization_opts]
    + cif_include_opts
)

i_regex = re.compile("(" + "|".join(cif_include_opts) + ")=?(.*)")
s_regex = re.compile("|".join(cif_supported_opts))


def filter_opts(opts, get_storage_path=None):
    if not cif_supported_opts:
        return []

    filtered_opts = []

    # Do not overwrite absolute paths within options except for the one
    # corresponding to isysroot when this option is specified.
    is_isysroot = any(opt.startswith("-isysroot") for opt in opts)

    opts = iter(opts)
    for opt in opts:
        if not s_regex.match(opt):
            continue

        m = i_regex.match(opt)

        if not m:
            filtered_opts.append(opt)

            if opt in requires_value["CC"]:
                filtered_opts.append(next(opts))

            continue

        name = m.group(1)
        path = m.group(2)

        if path:
            if (
                get_storage_path
                and os.path.isabs(path)
                and (not is_isysroot or name == "-isysroot")
            ):
                opt = opt.replace(path, get_storage_path(path))

            filtered_opts.append(opt)
        elif opt in requires_value["CC"]:
            filtered_opts.append(opt)
            path = next(opts)

            if (
                get_storage_path
                and os.path.isabs(path)
                and (not is_isysroot or name == "-isysroot")
            ):
                path = get_storage_path(path)

            filtered_opts.append(path)
        else:
            raise RuntimeError("Can't process CIF options")

    return filtered_opts
