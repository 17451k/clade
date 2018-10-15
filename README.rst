.. image:: https://travis-ci.org/17451k/clade.svg?branch=master
    :target: https://travis-ci.org/17451k/clade
.. image:: https://coveralls.io/repos/github/17451k/clade/badge.svg?branch=master
    :target: https://coveralls.io/github/17451k/clade?branch=master
.. image:: https://img.shields.io/pypi/pyversions/clade.svg
    :target: https://pypi.python.org/pypi/clade

Clade
=====

Clade is a tool for intercepting build commands (stuff like compilation,
linking, mv, rm, and all other commands that are executed during build).
Intercepted commands can be parsed (to search for input and output files,
and options) and then used for various purposes:

- obtaining information about the dependencies between source and object files;
- obtaining information about the source code;
- generating of the function call graph;
- running software verification tools;
- visualization of the all collected information;
- *and for much more*.

The interception of build commands is independent of the project type
and used programming languages.
However, all other functionality available in Clade IS dependent.
Currently only C projects are supported, but other languages and additional
functionality can be supported through the built-in extension mechanism.

Installation prerequisites
--------------------------

An important part of Clade - a build commands intercepting library -
is written in C and it needs to be compiled before use.
It will be performed automatially at the installation stage, but you will
need to install some prerequisites beforehand:

- Python 3 (>=3.4)
- cmake (>=3.3)
- make
- C and C++ compiler (gcc or clang)

Clade is working on Linux and macOS.
Partial support for Windows will be implemented soon.

Installation
------------

Just run the following command:

.. code-block:: bash

    $ pip3 install clade

For development purposes you may install Clade in "editable" mode
directly from the source code:

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
    /work/simple_make||1||/Library/Developer/CommandLineTools/usr/bin/make||/Library/Developer/CommandLineTools/usr/bin/make
    /work/simple_make||2||/usr/bin/gcc||gcc||main.c||-o||main
    /work/simple_make||3||/Library/Developer/CommandLineTools/usr/bin/gcc||/Library/Developer/CommandLineTools/usr/bin/gcc||main.c||-o||main
    /work/simple_make||4||/usr/bin/xcrun||/usr/bin/xcrun||clang||main.c||-o||main
    /work/simple_make||5||/Library/Developer/CommandLineTools/usr/bin/clang||/Library/Developer/CommandLineTools/usr/bin/clang||main.c||-o||main
    /work/simple_make||6||/Library/Developer/CommandLineTools/usr/bin/clang||/Library/Developer/CommandLineTools/usr/bin/clang||-cc1||-triple||x86_64-apple-macosx10.14.0||-Wdeprecated-objc-isa-usage||-Werror=deprecated-objc-isa-usage||-emit-obj||-mrelax-all||-disable-free||-disable-llvm-verifier||-discard-value-names||-main-file-name||main.c||-mrelocation-model||pic||-pic-level||2||-mthread-model||posix||-mdisable-fp-elim||-fno-strict-return||-masm-verbose||-munwind-tables||-target-cpu||penryn||-dwarf-column-info||-debugger-tuning=lldb||-target-linker-version||409.12||-resource-dir||/Library/Developer/CommandLineTools/usr/lib/clang/10.0.0||-fdebug-compilation-dir||/work/simple_make||-ferror-limit||19||-fmessage-length||120||-stack-protector||1||-fblocks||-fencode-extended-block-signature||-fobjc-runtime=macosx-10.14.0||-fmax-type-align=16||-fdiagnostics-show-option||-fcolor-diagnostics||-o||/var/folders/w7/d45mjl5d79v0hl9gqzzfkdgh0000gn/T/main-31ba54.o||-x||c||main.c
    /work/simple_make||7||/Library/Developer/CommandLineTools/usr/bin/ld||/Library/Developer/CommandLineTools/usr/bin/ld||-demangle||-lto_library||/Library/Developer/CommandLineTools/usr/lib/libLTO.dylib||-no_deduplicate||-dynamic||-arch||x86_64||-macosx_version_min||10.14.0||-o||main||/var/folders/w7/d45mjl5d79v0hl9gqzzfkdgh0000gn/T/main-31ba54.o||-lSystem||/Library/Developer/CommandLineTools/usr/lib/clang/10.0.0/lib/darwin/libclang_rt.osx.a
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
        "command":[
            "gcc",
            "main.c",
            "-o",
            "main"
        ],
        "cwd":"/Users/siddhartha",
        "id":"3",
        "pid":"2",
        "which":"/usr/bin/gcc"
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

Parsing of intercepted commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*not written yet*
