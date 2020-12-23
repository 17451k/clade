[![Build status](https://travis-ci.org/17451k/clade.svg?branch=master)](https://travis-ci.org/17451k/clade)
[![GitHub Actions status](https://github.com/17451k/clade/workflows/test/badge.svg)](https://github.com/17451k/clade/actions?query=workflow%3Atest)
[![Code coverage information](https://coveralls.io/repos/github/17451k/clade/badge.svg?branch=master)](https://coveralls.io/github/17451k/clade?branch=master)
[![Supported Versions of Python](https://img.shields.io/pypi/pyversions/clade.svg)](https://pypi.org/project/clade)
[![PyPI package version](https://img.shields.io/pypi/v/clade.svg)](https://pypi.org/project/clade)

# Clade

Clade is a tool for intercepting build commands (stuff like compilation,
linking, mv, rm, and all other commands that are executed during build).
Intercepted commands can be parsed (to search for input and output files,
and options) and then used for various purposes:

- generating [compilation database](https://clang.llvm.org/docs/JSONCompilationDatabase.html);
- obtaining information about dependencies between source and object files;
- obtaining information about the source code (source code querying);
- generating function call graph;
- running software verification tools;
- visualization of all collected information;
- *and for much more*.

The interception of build commands is independent of the project type
and used programming languages.
However, all other functionality available in Clade **IS** dependent.
Currently only C projects are supported, but other languages and additional
functionality can be supported through the built-in *extension mechanism*.

## Prerequisites

An important part of Clade - a build commands intercepting library -
is written in C and it needs to be compiled before use.
It will be performed automatically at the installation stage, but you will
need to install some prerequisites beforehand:

- Python 3 (>=3.5)
- pip (Python package manager)
- cmake (>=3.3)

*Linux only*:

- make
- C **and** C++ compiler (gcc or clang)
- python3-dev (Ubuntu) or python3-devel (openSUSE) package
- gcc-multilib (Ubuntu) or gcc-32bit (openSUSE) package
  to intercept build commands of projects leveraging multilib capabilities

*Windows only*:

- Microsoft Visual C++ Build Tools

Optional dependencies:

- For obtaining information about the C code you will need [CIF](https://github.com/17451k/cif)
  installed. CIF is an interface to [Aspectator](https://github.com/17451k/aspectator) which in turn is a GCC
  based tool that implements aspect-oriented programming for the C programming
  language. You may download compiled CIF on [CIF releases](https://github.com/17451k/cif/releases) page.
- Graphviz for some visualization capabilities.

Clade works on Linux, macOS and partially on Windows.

## Hardware requirements

If you want to run Clade on a large project, like the Linux kernel,
you will need at least 16GB of RAM and 100GB of free disk space
for temporary files. The size of generated data will be approximately
10GB, so the space used for temporary files will be freed at the end.
Also several CPU cores are recommended, since in some cases Clade takes
twice as long time than a typical build process.

## Installation

To install the latest stable version just run the following command:

``` shell
$ python3 -m pip install clade
```

## Documentation

Following documentation is available:
* [Basic usage](docs/usage.md)
* [Available configuration options](docs/configuration.md)
* [Troubleshooting](docs/troubleshooting.md)
* [Development documentation](docs/dev.md)

## Acknowledgments

Clade is inspired by the [Bear](https://github.com/rizsotto/Bear) project created by [László Nagy](https://github.com/rizsotto).
