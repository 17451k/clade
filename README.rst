.. image:: https://travis-ci.org/17451k/clade.svg?branch=master
    :target: https://travis-ci.org/17451k/clade
    :alt: Build status
.. image:: https://coveralls.io/repos/github/17451k/clade/badge.svg?branch=master
    :target: https://coveralls.io/github/17451k/clade?branch=master
    :alt: Code coverage information
.. image:: https://img.shields.io/pypi/pyversions/clade.svg
    :target: https://pypi.org/project/clade/
    :alt: Supported versions of Python
.. image:: https://img.shields.io/pypi/v/clade.svg
    :target: https://pypi.org/project/clade
    :alt: PyPi package version

Clade
=====

Clade is a tool for intercepting build commands (stuff like compilation,
linking, mv, rm, and all other commands that are executed during build).
Intercepted commands can be parsed (to search for input and output files,
and options) and then used for various purposes:

- generating `compilation database`_;
- obtaining information about dependencies between source and object files;
- obtaining information about the source code (source code querying);
- generating function call graph;
- running software verification tools;
- visualization of all collected information;
- *and for much more*.

.. _compilation database: https://clang.llvm.org/docs/JSONCompilationDatabase.html

The interception of build commands is independent of the project type
and used programming languages.
However, all other functionality available in Clade IS dependent.
Currently only C projects are supported, but other languages and additional
functionality can be supported through the built-in *extension mechanism*.

Prerequisites
-------------

An important part of Clade - a build commands intercepting library -
is written in C and it needs to be compiled before use.
It will be performed automatially at the installation stage, but you will
need to install some prerequisites beforehand:

- Python 3 (>=3.4)
- cmake (>=3.3)
- make
- C **and** C++ compiler (gcc or clang)
- *Linux only*: python3-dev package (or python3-devel)
- *Optional*: for obtaining information about the C code you will need CIF_
  installed. CIF is an interface to Aspectator_ which in turn is a GCC
  based tool that implements aspect-oriented programming for the C programming
  language. You may download compiled CIF on `CIF releases`_ page.
- *Optional*: graphviz for some visualization capabilities

.. _CIF: https://github.com/17451k/cif
.. _Aspectator: https://github.com/17451k/aspectator
.. _CIF releases: https://github.com/17451k/cif/releases

Clade works on Linux and macOS.
Partial support for Windows will be implemented soon.

Installation
------------

To install the latest stable version just run the following command:

.. code-block:: bash

    $ pip3 install clade

For development purposes you may install Clade in "editable" mode
directly from the repository (clone it on your computer beforehand):

.. code-block:: bash

    $ pip3 install -e .


How to use
----------

All functionality is available both as command-line scripts and
as Python modules that you can import and use, so the following
examples will include both use cases.

Build command intercepting
~~~~~~~~~~~~~~~~~~~~~~~~~~

Intercepting of build commands is quite easy: all you need is to
wrap your main build command like this:

.. code-block:: bash

    $ clade-intercept make

where *make* should be replaced by your project build command.
The output file called *cmds.txt* will be stored in the current directory
and will contain all intercepted commands, one per line.

You can change the path to to the file where intercepted commands will be
saved using -o (--output) option:

.. code-block:: bash

    $ clade-intercept -o /work/cmds.txt make

In case the build process of your project consists of several independent
steps, you can still create one single *cmds.txt* file using
-a (--append) option:

.. code-block:: bash

    $ clade-intercept make step_one
    $ clade-intercept -a make step_two

As a result, build commands of the second make command will be appended
to the cmds.txt file created previously.

Alternatively, you can intercept build commands from a python script:

.. code-block:: python

    from clade.intercept import Interceptor
    i = Interceptor(command=["make"], output="cmds.txt", append=False)
    i.execute()

Content of *cmds.txt* file
~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's look at the simple makefile:

.. code-block:: make

    all:
        gcc main.c -o main
        rm main

If we try to intercept *make all* command,
the following *cmds.txt* file will be produced (on macOS):

::

    /work/simple_make||0||/usr/bin/make||make||all
    /work/simple_make||1||/Library/Developer/CommandLineTools/usr/bin/make||/Library/Developer/CommandLineTools/usr/bin/make||all
    /work/simple_make||2||/usr/bin/gcc||gcc||main.c||-o||main||-O3
    /work/simple_make||3||/Library/Developer/CommandLineTools/usr/bin/gcc||/Library/Developer/CommandLineTools/usr/bin/gcc||main.c||-o||main||-O3
    /work/simple_make||4||/usr/bin/xcrun||/usr/bin/xcrun||clang||main.c||-o||main||-O3
    /work/simple_make||5||/Library/Developer/CommandLineTools/usr/bin/clang||/Library/Developer/CommandLineTools/usr/bin/clang||main.c||-o||main||-O3
    /work/simple_make||6||/Library/Developer/CommandLineTools/usr/bin/clang||/Library/Developer/CommandLineTools/usr/bin/clang||-cc1||-triple||x86_64-apple-macosx10.14.0||-Wdeprecated-objc-isa-usage||-Werror=deprecated-objc-isa-usage||-emit-obj||-disable-free||-disable-llvm-verifier||-discard-value-names||-main-file-name||main.c||-mrelocation-model||pic||-pic-level||2||-mthread-model||posix||-mdisable-fp-elim||-fno-strict-return||-masm-verbose||-munwind-tables||-target-cpu||penryn||-dwarf-column-info||-debugger-tuning=lldb||-target-linker-version||409.12||-resource-dir||/Library/Developer/CommandLineTools/usr/lib/clang/10.0.0||-O3||-fdebug-compilation-dir||/work/simple_make||-ferror-limit||19||-fmessage-length||150||-stack-protector||1||-fblocks||-fencode-extended-block-signature||-fobjc-runtime=macosx-10.14.0||-fmax-type-align=16||-fdiagnostics-show-option||-fcolor-diagnostics||-vectorize-loops||-vectorize-slp||-o||/var/folders/w7/d45mjl5d79v0hl9gqzzfkdgh0000gn/T/main-de88a6.o||-x||c||main.c
    /work/simple_make||7||/Library/Developer/CommandLineTools/usr/bin/ld||/Library/Developer/CommandLineTools/usr/bin/ld||-demangle||-lto_library||/Library/Developer/CommandLineTools/usr/lib/libLTO.dylib||-dynamic||-arch||x86_64||-macosx_version_min||10.14.0||-o||main||/var/folders/w7/d45mjl5d79v0hl9gqzzfkdgh0000gn/T/main-de88a6.o||-lSystem||/Library/Developer/CommandLineTools/usr/lib/clang/10.0.0/lib/darwin/libclang_rt.osx.a
    /work/simple_make||2||/bin/rm||rm||main


You can try to use *cmds.txt* file directly, but its format is not quite
user-friendly and is subject to change.
It is a good idea not to rely on the format of *cmds.txt* file
and use the interface module instead:

.. code-block:: python

    from clade.cmds import get_all_cmds
    cmds = get_all_cmds("cmds.txt")

where *cmds* is a list of dictionaries representing each intercepted command.
For example, dictionary that represents *gcc* command from the above makefile
looks like this:

.. code-block:: json

    {
        "command": [
            "gcc",
            "main.c",
            "-o",
            "main",
            "-O3"
        ],
        "cwd": "/work/simple_make",
        "id": "3",
        "pid": "2",
        "which": "/usr/bin/gcc"
    }

where:

- *command* - is intercepted command itself;
- *cwd* - is a path to the directory where the command was executed;
- *id* - is a unique identifier assigned to the command;
- *pid* - is an identifier of the parent command
  (command that executed the current one - in our example
  it is an identifier of the make command);
- *which* - path to an executable file that was executed
  as a result of this command.

It should be noted that all other functionality available in Clade use
*cmds.txt* file as input.
Due to this you do not need to rebuild your project every time you want
to use it - you can just use previously generated *cmds.txt* file.

Parsing of intercepted commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once build commands are intercepted they can be parsed to search for input
and output files, and options. Currently there are *extensions* in Clade
for parsing following commands:

- C compilation commands (cc, gcc, clang, various cross compilers);
- linker commands (ld);
- assembler commands (as);
- archive commands (ar);
- move commands (mv);
- object copy commands (objcopy, Linux only).

These extensions can be executed from command line through *clade-cc*,
*clade-ld*, *clade-as*, *clade-ar*, *clade-mv*, *clade-objcopy* commands
respectively. They all have similar input interface and the format
of output files, so let's just look at *clade-cc* command. It can be executed
as follows:

.. code-block:: bash

    $ clade-cc cmds.txt

As a result, a working directory named *clade* will be created:

::

    clade/
    ├── CC/
    │   ├── cmds.json
    │   ├── cmds/
    │   ├── deps/
    │   ├── opts/
    │   └── unparsed/
    ├── PidGraph/
    └── Storage/

Top-level directories are in turn working directories of corresponding
extensions that were executed inside *clade-cc* command.
*CC* extension is the one we wanted to execute, but there are also
other extensions - *PidGraph* and *Storage* - that were executed implicitly
by *CC* because it depends on the results of their work.
Let's skip them for now.

Inside *CC* directory there is a bunch of other directories and *cmds.json*
file with parsed compilation commands.
Again, it is a list of dictionaries representing each parsed command.
Let's look at the parsed command from the above example:

.. code-block:: json

    {
        "command":"gcc",
        "cwd":"/work/simple_make",
        "id":"3",
        "in":[
            "main.c"
        ],
        "opts":[
            "-O3"
        ],
        "out":[
            "main"
        ]
    }

Its structure is quite simple: there is a list of input files,
a list of output files, a list of options, and some other info that is
self-explanatory.

*CC* extension also identify *dependencies* of the main source file
for each compillation command.
Dependencies are the names of all included header files,
even ones included indirectly.
Clade stores them inside *deps* subfolder.
For example, dependencies of the parsed command with id="3" can be found
in *deps/3.json* file:

::

    [
        "/usr/include/secure/_common.h",
        "/usr/include/sys/_types/_u_int32_t.h",
        "/usr/include/machine/_types.h",
        "/usr/include/sys/_types/_u_int16_t.h",
        "/usr/include/_stdio.h",
        "/usr/include/sys/cdefs.h",
        "/usr/include/secure/_stdio.h",
        "/usr/include/sys/_types/_size_t.h",
        "/usr/include/sys/_types/_u_int8_t.h",
        "/usr/include/stdio.h",
        "/usr/include/sys/_types/_ssize_t.h",
        "/usr/include/sys/_symbol_aliasing.h",
        "/usr/include/sys/_types/_int32_t.h",
        "/usr/include/sys/_pthread/_pthread_types.h",
        "/usr/include/sys/_types/_int8_t.h",
        "main.c",
        "/usr/include/sys/_types/_int16_t.h",
        "/usr/include/sys/_types/_uintptr_t.h",
        "/usr/include/sys/_types/_null.h",
        "/usr/include/sys/_types/_off_t.h",
        "/usr/include/sys/stdio.h",
        "/usr/include/_types.h",
        "/usr/include/AvailabilityInternal.h",
        "/usr/include/sys/_types/_va_list.h",
        "/usr/include/Availability.h",
        "/usr/include/sys/_posix_availability.h",
        "/usr/include/sys/_types/_u_int64_t.h",
        "/usr/include/sys/_types/_intptr_t.h",
        "/usr/include/sys/_types.h",
        "/usr/include/sys/_types/_int64_t.h",
        "/usr/include/i386/_types.h",
        "/usr/include/i386/types.h",
        "/usr/include/machine/types.h"
    ]

Besides dependencies, all other parsed commands (ld, mv, and so on)
will also look this way: as a list of dictionaries representing each
parsed command, with "command", "id", "in", "opts" and "out" fields.

*CC* extension (and all others, of course) can also be imported and used
as a Python module:

.. code-block:: python

    from clade.extensions.cc import CC

    # Initialize extension with a path to the working directory
    c = CC(work_dir="clade")

    # Execute parsing of intercepted commands
    # This step can be skipped if commands are already parsed
    # and stored in the working directory
    c.parse("cmds.txt)

    # Get a list of all parsed commands
    parsed_cmds = c.load_all_cmds()
    for cmd in parsed_cmds:
        # Get a list of dependencies
        deps = c.load_deps_by_id(cmd["id"])
        ...

Pid graph
~~~~~~~~~

Each intercepted command, execept for the first one, is executed by another,
parent command. For example, *gcc* internally executes
*cc1* and *as* commands, so *gcc* is their parent.
Clade knows about this connection and tracks it by assigning to each intercepted
command two attributes: a unique identifier (id) and identifier of its parent
(pid).
This information is stored in the *pid graph* and can be obtained using
*clade-pid-graph* command line tool:

.. code-block:: bash

    $ clade-pid-graph cmds.txt
    $ tree clade -L 2

    clade
    └── PidGraph
        ├── pid_by_id.json
        └── pid_graph.json

Two files will be generated. First one - *pid_by_id.json* - is a simple
mapping from ids to their pids and looks like this:

.. code-block:: json

    {
        "1": "0",
        "2": "1",
        "3": "2",
        "4": "2",
        "5": "1"
    }

Another one - *pid_graph.json* - stores information about all parent commands
for a given id:

.. code-block:: json

    {
        "1": ["0"],
        "2": ["1", "0"],
        "3": ["2", "1", "0"],
        "4": ["2", "1", "0"],
        "5": ["1", "0"]
    }

*Pid graph* can be imported and used as a Python module:

.. code-block:: python

    from clade.extensions.pid_graph import PidGraph

    # Initialize extension with a path to the working directory
    c = PidGraph(work_dir="clade")

    # Execute parsing of intercepted commands
    # This step can be skipped if commands are already parsed
    # and stored in the working directory
    c.parse("cmds.txt)

    # Get all information
    pid_by_id = c.load_pid_by_id()
    pid_graph = c.load_pid_graph()

Other extensions use *pid graph* to filter *duplicate* commands.
For example, on macOS executing "*gcc main.c*" command leads to the
chain of execution of the following commands:

- /usr/bin/gcc main.c
- /Library/Developer/CommandLineTools/usr/bin/gcc main.c
- /usr/bin/xcrun clang main.c
- /Library/Developer/CommandLineTools/usr/bin/clang main.c
- /Library/Developer/CommandLineTools/usr/bin/clang -cc1 ...

So, for a single compilation command, several commands will be actually
intercepted. You probably need only one of them (the very first one),
so Clade filter all *duplicate* ones using *pid graph*: Clade simply
do not parse all child commands of already parsed command.
This behavior is of course configurable and can be disabled.

*Pid graph* can be visualized with Graphviz using one of
the configuration options:

.. image:: docs/pics/pid_graph.png
    :alt: An example of the pid graph

Note: *pid graph* can be used with any project
(not only with ones written in C).

Command graph
~~~~~~~~~~~~~

Clade can connect commands by their input and output files.
This information is stored in the *command graph* and can be obtained using
*clade-cmd-graph* command line tool.

To appear in the *command graph* an intercepted command needs to be parsed
to search for input and output files.
By default only commands parsed by *CC*, *LD* and *MV* extensions
are parsed and appeared in the *command graph*.
This behavior can be changed via configuration, which will be described below.


Let's consider the following makefile:

.. code-block:: make

    all:
        gcc -S main.c -o main.s  # id = 1
        as main.s -o main.o      # id = 2
        mv main.o main           # id = 3

Using *clade-cmd-graph* these commands can be connected:

.. code-block:: bash

    $ clade-pid-graph cmds.txt

    clade
    ├── CmdGraph/
    │   └── cmd_graph.json
    ├── CC/
    ├── LD/
    ├── MV/
    ├── PidGraph
    └── Storage/

where *cmd_graph.json* looks like this (commands are represented by their
identifiers and the type of extensions that parsed it):

.. code-block:: json

    {
        "1":{
            "type": "CC",
            "used_by": ["2", "3"],
            "using": []
        },
        "2":{
            "type": "AS",
            "used_by": ["3"],
            "using": ["1"]
        },
        "3":{
            "type": "MV",
            "used_by": [],
            "using": ["1", "2"]
        }
    }

*Command graph* can be imported and used as a Python module:

.. code-block:: python

    from clade.extensions.cmd_graph import CmdGraph

    # Initialize extension with a path to the working directory
    c = CmdGraph(work_dir="clade")

    # Execute parsing of intercepted commands
    # This step can be skipped if commands are already parsed
    # and stored in the working directory
    c.parse("cmds.txt)

    # Get the command graph
    cmd_graph = c.load_cmd_graph()

*Command graph* can be visualized with Graphviz using one of
the configuration options:

.. image:: docs/pics/cmd_graph.png
    :alt: An example of the command graph

Source graph
~~~~~~~~~~~~

For a given source file Clade can show in which commands this file
is compiled, and in which commands it is inderectly used.
This information is called *source graph* and can be generated
using *clade-src-graph* command line utility:

.. code-block:: bash

    $ clade-src-graph cmds.txt

    clade
    ├── SrcGraph/
    │   └── src_graph.json
    ├── CmdGraph/
    ├── CC/
    ├── LD/
    ├── MV/
    ├── PidGraph
    └── Storage/

*Source graph* for the Makefile presented in the *command graph* section above
will be located in the *src_graph.json* file and look like this:

.. code-block:: json

    {
        "/usr/include/stdio.h": {
            "compiled_in": ["1"],
            "loc": 414,
            "used_by": ["2", "3"]
        },
        "main.c":{
            "compiled_in": ["1"],
            "loc": 5,
            "used_by": ["2", "3"],
        },
        "main.s":{
            "compiled_in": ["2"],
            "loc": 20,
            "used_by": ["3"],
        }
    }

For simplicity information about other files has been removed from
the presented *source graph*.
As always, commands are represented through their unique identifiers.
*loc* field contains information about the size of the source file:
number of the lines of code.

*Source graph* can be imported and used as a Python module:

.. code-block:: python

    from clade.extensions.src_graph import SrcGraph

    # Initialize extension with a path to the working directory
    c = SrcGraph(work_dir="clade")

    # Execute parsing of intercepted commands
    # This step can be skipped if commands are already parsed
    # and stored in the working directory
    c.parse("cmds.txt)

    # Get the source graph
    src_graph = c.load_src_graph()

Call graph
~~~~~~~~~~

*not written yet*

Configuration
~~~~~~~~~~~~~

*not written yet*

Compilation database
~~~~~~~~~~~~~~~~~~~~

*not written yet*

Troubleshooting
---------------

*not written yet*


Acknowledgments
---------------

*not written yet*
