# Scripts

In the [scripts](../clade/scripts/) directory there are several scripts that
showcase the usage of the Clade API (both public and
internal ones). Thus, these scripts may be seen as examples, but they may
be useful on their own as well.

The following scripts are available:

- `clade-check` simply checks that Clade working directory exists and is not
    corrupted.
- `clade-cdb` can be used to create compilation database.
- `clade-trace` can be used to visualize callgraph between specified functions.
- `clade-file-graph` can be used to visualize file dependencies between
    intercepted commands.
- `clade-pid-graph` can be used to visualize parent-child relationship between
    intercepted commands.
- `clade-cmds` outputs some statistics based on the `cmds.txt` file.
- `clade-diff` can output diff between 2 Clade working directories.
    (Though, this one probably isn't working right now).
