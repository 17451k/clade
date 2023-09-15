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
