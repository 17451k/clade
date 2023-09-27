# Configuration

There is a bunch of options that can be changed to alter the behaviour of the
*clade* command. The configuration can be passed via the "-c" option like this:

``` shell
clade -c conf.json make
```

where `conf.json` is a json file with some configuration options:

``` json
{
    "CC.ignore_cc1": true,
    "CmdGraph.requires": [
        "CC",
        "LD",
        "MV",
        "AR",
        "Objcopy"
    ],
    "CC.which_list": ["/usr.bin.gcc", "^.*clang$"]
}
```

The configuration can be also passed as a Python dictionary:

``` python
from clade import Clade

conf = {"CC.ignore_cc1": True}
c = Clade(work_dir="clade", cmds_file="cmds.txt", conf=conf)
```

## which list

Let's highlight some notable configuration options and let's start with
options for extensions that parse intercepted commands to search for input
and output files, and options. These extensions need to know which commands
to parse. They have a list of predefined regular expressions that they try
to match with the `which` field of an intercepted command.
For example, `CC` extension have the following list:

``` json
[
    "cc$",
    "cc1$",
    "[mg]cc(-?\\d+(\\.\\d+){0,2})?$",
    "clang(-?\\d+(\\.\\d+){0,2})?$"
]
```

Obviously, execution of `/usr/bin/gcc` will be matched, as well as
`/usr/bin/clang`, or `/usr/local/bin/powerpc-elf-gcc-7`, so all such commands
will be treated as compilation commands and parsed accordingly.
Sometimes this list is not enough, so there is an option to change it:

```
"CC.which_list": ["regexp_to_match_your_compiler"]
```

Options for other such extensions look the same, you just need to replace `CC`
by the name of the extension, so, for example, `LD.which_list` will be the
option to change the list of regexes for `LD` extension. The following
extensions have `.which_list` options:
`AR, AS, CC, CXX, LD, MV, LN, Install, Objcopy, CL, Link, Copy`.

## Presets

There is a predefined set of options for the following projects that can be 
used in addition to the user-defined configuration:

* Linux kernel (preset linux_kernel)
* Busybox (preset busybox_linux)
* Apache (preset apache_linux)

If you want to execute Clade on one of these projects, then it might be a
*good idea* to use these presets, since they will definitely save you from
having to deal with various problems and mess with the configuration:

``` shell
clade -p linux_kernel make
```

or

``` python
from clade import Clade

c = Clade(work_dir="clade", cmds_file="cmds.txt", preset="linux_kernel")
```

## Other options

List of all available options can be found in the
[presets.json](../clade/extensions/presets/presets.json) file.
Let's describe some of them.

### Generic options

- "log_level" allows you to change the verbosity of the logger. You can
    pass the following values: "INFO", "DEBUG", "WARNING", "ERROR".
- "force" is a boolean value. If true, Clade will overwrite the existing
    working directory if it already exists (left from the previous launch,
    for example). The default behaviour is to exit with error.
- "extensions" is a list of extension names to use during this Clade run.
    Default value is `["SrcGraph]`, which will run 
- "cpu_count" limits the number of CPU cores used by Clade.

### Wrapper options

These options regulate the behavior of the `wrapper` based mechanism of
intercepting build commands.

- "Wrapper.wrap_list" is a lists of paths to the executable files (compilers,
    for example), calls to which you want to intercept.
- "Wrapper.recursive_wrap" is a boolean. If true, it allows to add directories
    to the "Wrapper.wrap_list" option, and create wrappers for all executables
    inside them, including all subdirectories.

### CC options

- "CC.ignore_cc1" - if true (default), then options like `gcc -cc1` will be
    ignored (they are rarely useful).
- "CC.with_system_header_files": if true, there will be system header files
    in the output of `CC` extension. If false, only project headers will be
    included in the output, even if the system headers were also used.
- "CC.process_ccache" allows to turn on or off `ccache` support.

### CL options

- "CL.pre_encoding" allows you to manually specify encoding of preprocessed
    files (requires "Compiler.preprocess_cmds" to be true). Otherwise, encoding
    will be determined automatically (may be wrong).

### Linker options

- "Linker.searchdirs" is a list of directories, in which linker may search for
    libraries.

### Compiler options

These are common options for extensions that implement Compiler interface
(`CC`, `LD`, `CL`, `CXX`).

- "Compiler.deps_encoding" allows to explicitly specify encoding of the
    [dependency files](https://gcc.gnu.org/news/dependencies.html).
- "Compiler.get_deps" if true (default value), then Clade adds information 
    about dependencies to the output of the extension.
- "Compiler.store_deps" if true (default value), copies all dependencies 
    to the Clade Storage.
- "Compiler.preprocess_cmds" if true (default false), source files are
    preprocessed and stored in the Clade Storage.
- "Compiler.extra_preprocessor_opts" is a list of additional
    options that you may want to pass to the compiler before preprocessing.
    This options requires "Compiler.preprocess_cmds" to be true.

### Storage options

- "Storage.convert_to_utf8" if true (default false) then Clade re-encodes
    all files saved to the Storage to utf8. By default file encoding is not
    changed.
- "Storage.decoding_errors" allows to specify how to treat decoding errors.
    Possible values are "strict" (default, raises exception),
    "ignore", "replace". See [Codec Base Classes](https://docs.python.org/3/library/codecs.html#codec-base-classes) for explanation.
- "Storage.files_to_add" is a list of files, which you may want to explicitly
    include to the Clade Storage.

### Alternatives options

- "Alternatives.use_canonical_paths" if true (default value), then if the some
    file from the intercepted commands has several paths associated with him
    (for example, if there are symlinks, or the file was moved during build)
    then one of this paths is chosen as canonical and used everywhere in
    Clade.
- "Alternatives.requires" is a list of extensions which can be used to find
    possible alternative paths (in order to find a canonical one).
    Default value is `LN` and `Install`.

### CmdGraph options

- "CmdGraph.requires" is a list of commands to parse. If you want to generate
    `command graph`, `source graph`, or `call graph`, then you need to specify
    which commands to parse via this option. By default all commands that are
    supported now are parsed, but you can reduce their number by passing
    a list of extension names. Example: `"CmdGraph.requires": ["CC", "LD"]`

### SrcGraph options

 - "SrcGraph.requires" is a list of extensions to use to create source graph.
    By default this list consists of C Compiler extensions (`CC` and `CL`),
    but it may be extended with `CXX` and possibly others.

### Common options

- "Common.exclude_list" is a list of regexes. If an extension implements
    Common interface and one of files from a parsed command is matched by
    regex from this list, then the parsed command is discarded and not
    included in the Clade output. This is a *block* list.
- "Common.exclude_list_in" is a list of regexes. If an extension implements
    Common interface and one of *input* files from a parsed command is
    matched by regex from this list, then the parsed command is discarded
    and not included in the Clade output. This is a *block* list.
- "Common.exclude_list_out"  is a list of regexes. If an extension implements
    Common interface and one of *output* files from a parsed command is
    matched by regex from this list, then the parsed command is discarded
    and not included in the Clade output. This is a *block* list.
- "Common.include_list"  is a list of regexes. If an extension implements
    Common interface and one of files from a parsed command is
    matched by regex from this list, then the parsed command is *included*
    in the Clade output. This is a *white* list.

### CXX options

- "CXX.process_ccache" allows to turn on or off `ccache` support.

### Info options

- "Info.extra_CIF_opts" is a list of additional options that you may want
    to pass to CIF. Empty by default.
- "Info.extra_supported_opts" is a list of options that should be passed to
    CIF if they were present in the intercepted command. By default only
    subset of options is passed to CIF, and this list may be extended here.
- "Info.use_preprocessed_files" if true (default false), CIF will be
    executed on preprocessed files.
- "Info.cif" allows to specify path to the CIF.
- "Info.aspectator" allows to specify path to the Aspectator.
- "Info.aspect" allows to change the aspect file, which will be used by CIF
    to gather additional information about source code.

### PidGraph options

- "PidGraph.filter_cmds_by_pid" if true (default value), Clade will not parse
    child commands of already parsed commands. See `PidGraph` [docs](usage.md)
    for explanation.

### CDB options

- "CDB.filter_opts" if true (default false), generated compile_commands.json
    will contain reduced number of options, which may improve compatibility
    with some external tools.
