# Documentation for Clade developers

## Installing prerequisites for development

The following sections assume that you already installed all the required
Python packages for testing, measuring code coverage and profiling, using the
following command:

``` shell
uv sync
```

or, without `uv`:

``` shell
python3 -m pip install -e . --group dev
```

Formatting and linting (`black`, `ruff`, `ty`) run on every commit through
[pre-commit](https://pre-commit.com); enable the hook once with
`uvx pre-commit install`, or run everything by hand with
`uvx pre-commit run --all-files`.

Note that this command installs Clade in "editable" mode directly from the
repository (you need to clone it on your computer beforehand and execute
the command from the root of the repository).

## Testing

You can check that Clade works as expected on your machine by running
the test suite from the repository (doesn't work on Windows yet):

``` shell
pytest
```

## Disable parallelism

Some issues in Clade are hard to debug, because a lot of stuff happens inside
child processes. You can disable parallelism by setting *CLADE_DEBUG*
environment value.

## Measuring code coverage

To measure coverage you need to execute the following commands:

``` shell
coverage run -m pytest && coverage combine && coverage html
```

Results can be observed by opening generated *htmlcov/index.html* file in the browser.

## Extensions

Most of the functionality in Clade is implemented as *extensions*. Each
extension implements and uses a simple API:

- Extension class must be a child of an `clade.extensions.abstract.Abstract` class.
- Extension must implement a `parse(self, cmds_file)` method,
    which will serve as an entry point. `cmds_file` may be used to
    parse intercepted commands, but this is not required.
- Extension may interact with other extensions by specifying them in the
    `requires` class attribute. Its value should be the list of names of
    required extensions, by default it is empty.
    This will regulate the correct order between extensions: of one extensions
    is required by other, then it will be executed first.
    Interaction with other extensions is possible via `self.extensions`
    dictionary, where keys are the names of required extensions, and values
    are corresponding objects. This way you can easily access their API.
- Extensions store their results in the SQLite database shared by the whole
    working directory (`clade.db`) through `self.dump_data()` /
    `self.load_data()` for single values and `self.dump_data_by_key()` /
    `self.load_data_by_key()` / `self.yield_data_by_key()` for maps that are
    usually read partially (by file, by function name). Values are JSON
    documents, so anything `orjson` can serialize works. Records are grouped
    by extension name, and `clade -fe` removes them together with the
    extension directory.
- Only the main process writes to the database. Jobs started through
    `self.execute_in_parallel()` may call `dump_*` too: their records are
    collected in the worker and written by the main process once the job
    finishes, so a job must not read back what it has just dumped.
- Each extension also has a *working directory* for things that must remain
    plain files, like logs or copies of source code.
    It is available via `self.work_dir`, but it is not created for you:
    call `os.makedirs()` before writing there, so that extensions that only
    use the database leave no empty directories behind. Whether an
    extension has already been parsed is recorded in `meta.json`, not by the
    presence of its directory.
- `Abstract` class implements a bunch of helpful methods, which can be used to
    simplify various things. For example, it implements an API to execute jobs
    on intercepted commands in parallel.
