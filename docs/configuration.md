# Configuration

There is a bunch of options that can be changed to alter the behaviour of the
*clade* command. The configuration can be passed via the "-c" option like this:

``` shell
clade -c conf.json make
```

where `conf.json` is a json file with some configuration options:

``` json
{
    "PidGraph.as_picture": true,
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

conf = {"PidGraph.as_picture": True}
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
option to change the list of regexes for `LD` extension.

## Visualization options

Currently there are two small options to visualize `pid graph` and `cmd graph`
using Graphviz:

```
{
    "PidGraph.as_picture": true,
    "CmdGraph.as_picture": true
}
```

If they are set, then next to `pid_graph.json` and `cmd_graph.json` files
respectively pdf files containing Graphviz output will appear.

## List of commands to parse

If you want to generate `command graph`, or `source graph`, or `call graph`,
then you need to specify which commands to parse via `CmdGraph.requires`
option. By default all commands that are supported now are parsed,
but you can reduce their number:

``` json
{
    "CmdGraph.requires": ["CC", "LD"]
}
```

## Presets

There is a predefined set of options for the following projects that can be used
in addition to the user-defined configuration:

* Linux kernel (preset linux_kernel)
* Busybox (preset busybox_linux)
* Apache (preset apache_linux)

If you want to execute Clade on one of these projects, then it might be a
*good idea* to use these presets, since they will definitely save you from having
to deal with various problems and mess with the configuration:

``` shell
clade -p linux_kernel make
```

or

``` python
from clade import Clade

c = Clade(work_dir="clade", cmds_file="cmds.txt", preset="linux_kernel")
```

## Other options

List of available options (without any comments) can be found in the
[presets.json](../clade/extenstions/../extensions/presets/presets.json) file.
Some day they will be described here as well.
