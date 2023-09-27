# Documentation for Clade developers

## Installing prerequisites for development

The following sections assume that you already installed all the required
Python packages for testing, measuring code coverage and profiling, using the
following command:

``` shell
python3 -m pip install -e ".[dev]"
```

Note that this command installs Clade in "editable" mode directly from the
repository (you need to clone it on your computer beforehand and execute
the command from the root of the repository).

## Testing

You can check that Clade works as expected on your machine by running
the test suite from the repository (doesn't work on Windows yet):

``` shell
pytest
```

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
- Each extension has a *working directory*, which can be used to store files.
    It is available via `self.work_dir`.
- `Abstract` class implements a bunch of helpful methods, which can be used to
    simplify various things. For example, it implements an API to execute jobs
    on intercepted commands in parallel.
