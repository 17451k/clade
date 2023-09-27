# Extensions

Most of the functionality in Clade is implemented as *extensions*.
These extensions can be separated into the following groups:

## Extensions that parse a particular type of build commands

- C compilation commands: `CC` and `CL` extensions.
- C++ compilation commands: `CXX` extension.
- `ar` commands, which are used to create, modify, and extract
    from archives: `AR` extension.
- Assembler commands: `AS` extension
- Link commands: `LN` extension.
- Move commands: `MV` extension.
- Object copy commands: `Objcopy` extension.
- Copy commands (Windows-specific): `Copy` extension.

Each of these extensions has a corresponding [configuration](configuration.md)
option, which precisely describes which commands it parse.
These options can be found on the [presets.json](../clade/extensions/presets/presets.json) file.

These extensions output a list of json files with parsed commands.
Each parsed command consists of a list of input files, a list of
output files, and a list of options. Some extensions may add
additional data, for example, `CC` extension also adds a list
of dependencies (header files that were used by the intercepted
compile command).

## Extensions that generate information by using a list of all intercepted commands

- `PidGraph` extension, which produces parent-child graph between intercepted
    commands.

More about it you can read in the [usage docs](usage.md).

## Extensions that generate information using data from other extensions

Extensions may interact with each other, and thus refine and produce data
from several sources. Extensions in this group are:

- `CmdGraph` extension, which uses parsed commands from other extensions,
    and connects them by their input and output files, creating dependency
    graph between these commands.
- `SrcGraph` extension, which shows for each source file (C or C++ only)
    a list of commands in which it was compiled, and a list of commands
    in which it was indirectly used.
- `Alternatives` extension, which parses build commands that create
    *identical* file copies (ln, cp, install, etc.) and allows to determine
    that different paths are in fact related to the same file.
- `CDB` extension, which is used to create compilation databases.

## Helper extensions

These are extensions that implement functionality useful for other extensions.

- `Path` extension: provides functions to normalize file paths.
- `Storage` extension: adds ability to save files to the Clade
    working directory, and to retrieve them later. This allows the following
    scenario: Clade intercepts build process on one computer, and then parses
    the ouput on another, using cmds.txt file and file copies stored in the
    Storage.

## Extensions that use information about the source code (C only)

- `Info` is the main extension here: it uses [CIF](https://github.com/17451k/cif) to parse source code and extract various info about it. All extensions
    in this group are using data from the `Info` extension.
- `Functions` extension parses information about function definitions and
    declarations.
- `Callgraph` extension creates a function callgraph.
- `Macros` extension pares information about macros definitions and expansions.
- `Typedefs` extension parses information about typedefs.
- `UsedIn` extension parses information about functional pointers
- `CallsByPtr` extension parses information about function calls by pointers.
- `Variables` extension parses information about global variable initializations.

## Parent extensions

These extensions are not meant to be used as is, they are parent classes for other extensions. They usually implement some common functionality.

- `Abstract` extension (parent of all other extensions).
- `Common` extension (for extensions that parse intercepted
    commands into input, output files, and a list of options.
- `Link` extension (parent of compiler extensions that also
    parse linker commands)
- `CommonInfo` extension, implements common functionality for extensions
    that parse output of `Info` extension.

