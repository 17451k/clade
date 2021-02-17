# Troubleshooting

## File with intercepted commands is empty

Access control mechanisms on different operating systems might disable
library injection that is used by Clade to intercept build commands:

- SELinux on Fedora, CentOS, RHEL;
- System Integrity Protection on macOS;
- Mandatory Integrity Control on Windows (disables similar mechanisms)

A solution is to use another intercepting mechanism that is based on
*wrappers* (see [usage documentation](usage.md)).

## File with intercepted commands is not complete

Sometimes some commands are intercepted, so file `cmds.txt` is present and not
empty, but other commands are clearly missing.
Such behaviour should be reported so the issue can be fixed, but until then
you can try to use another intercepting mechanism that is based on
*wrappers*.

## Wrong ELF class

Build command intercepting may result in the following error:

```
ERROR: ld.so: object 'libinterceptor.so' from LD_PRELOAD cannot be preloaded (wrong ELF class: ELFCLASS64): ignored.
```

It is because your project leverages multilib capabilities, but
`libinterceptor` library that is used to intercept build commands is
compiled without multilib support.
You need to install `gcc-multilib` (Ubuntu) or `gcc-32bit` (openSUSE) package
and **reinstall Clade**. `libinterceptor` library will be recompiled and your
issue will be fixed.

## Not all intercepted compilation commands are parsed

The reason is because `CC` extension that parse intercepted commands cannot
identify a command as a compilation command. You can help it by specifying
`CC.which_list` [configuration](configuration.md) option, in which you should write a list of
[regexes](https://en.wikipedia.org/wiki/Regular_expression) that will match your compiler. For example, if path to your compiler
is `~/.local/bin/c_compiler`, than `CC.which_list` may be set like this:

```
"CC.which_list": ["c_compiler$"]
```

If you want to parse not only commands executed by your compiler, but by system
`gcc` as well, then you can add it to the list too:

```
"CC.which_list": ["c_compiler$", ""gcc$"]
```

How to set configuration option is described in the [configuration](configuration.md) section of
this documentation.

## Compilation database miss some commands

Same as above.

## Command graph is not connected properly

Most certainly it is due to the fact that some type of commands is unparsed.
If there is an extension in Clade that can parse them, then you will need
to specify it via the option "CmdGraph.requires":


``` json
{
    "CmdGraph.requires": ["CC", "LD", "MV", "AR", "Objcopy"]
}
```

Otherwise such extension should be developed.

Similar problems with the *source graph* and the *call graph* can be fixed
via the same option, since they use the *command graph* internally.

## BitBake support

BitBake limits environment of the worker processes it creates, which
doesn't allow Clade to correctly intercept build commands. To overcome it,
you can use [BB_ENV_EXTRAWHITE](https://www.yoctoproject.org/docs/1.6/bitbake-user-manual/bitbake-user-manual.html#var-BB_ENV_EXTRAWHITE)
BitBake environment variable, which specifies a set of variables to pass
to the build processes:

``` shell
$ export BB_ENV_EXTRAWHITE="CLADE_INTERCEPT CLADE_ID_FILE CLADE_PARENT_ID LD_PRELOAD LD_LIBRARY_PATH $BB_ENV_EXTRAWHITE"
$ clade bitbake <target>
```
