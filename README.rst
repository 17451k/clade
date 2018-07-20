Clade
=====

Clade is a tool for intercepting build commands (stuff like compilation,
linking, mv, rm, and all other commands that are executed during build).

Intercepted commands can be used for purposes such as generating
callgraph of a C project using compilation commands, visualization of
the dependencies graph between project files, and for much more.

Some of such use cases will be included in Clade later. Currently only
build command intercepting is supported.

Installation
------------

Just run the following command (Python 3 is required):

.. code-block:: bash

    $ pip install clade

For development purposes you may install Clade in "editable" mode
directly from the source code. An important part of Clade is written
in C, so in order to build it yourself you must have cmake, make and
the C compiler installed on your system.

.. code-block:: bash

    $ pip install -e .


How to use
----------

After installation the usage is like this:

.. code-block:: bash

    $ clade-intercept make

where 'make' should be replaced by your project build command.

The output file called cmds.json will be stored in the current directory.
Additional features are described in --help.

