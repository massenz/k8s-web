#!/usr/bin/env python

import os
import pathlib
import re


VERSION_PATTERN = re.compile(r"^\s*version\s*=\s*(?P<version>[0-9.]+)-?(?P<build>\w+)?$")
FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
DATE_FMT = '%m/%d/%Y %H:%M:%S'
SENSITIVE_KEYS = (
    'SESSION_COOKIE_DOMAIN',
    'SESSION_COOKIE_PATH',
    'RUNNING_AS',
    'SECRET_KEY',
)

DEFAULT_MONGODB_URI = 'mongodb://localhost:27017/k8s-web-data'
MONGO_HEALTH_KEYS = (
    "debug", "ok", "version"
)


class SaneBool(object):
    """ A class to enable sane conversion of a string to boolean value

        Honestly, I'm amazed Python does this by default:
            bool('False') == True

        This class will convert any string value that matched any of the ```TRUE_VALUES```
        (case insensitive) into a ```True``` boolean, or any of the ```FALSE_VALUES``` into a
        ```False``` instead.

        Use it like thus:

            >>> from app.utils import SaneBool
            >>> SaneBool('true')
            True
            >>> bool('True')
            True
            >>> bool('False')
            True
            >>> SaneBool('False')
            False
            >>> assert bool('True') == bool('False')
            >>> assert SaneBool('True') == SaneBool('False')
            Traceback (most recent call last):
              File "<input>", line 1, in <module>
            AssertionError

        This class also supports conversion from int values to bool, using Python's default (
        which *is* sane).

        In fact, this will also support conversion from any object whose ````str()``` repr can
        be converted into a boolean value according to the above::

            class Foo(object):
                def __repr__(self):
                    return 'y'

            assert SaneBool(Foo())

        :raises ValueError: if the given string doesn't match any of the set values
    """
    TRUE_VALUES = ['true', '1', 't', 'y', 'yes']
    FALSE_VALUES = ['false', '0', 'f', 'n', 'no']

    def __new__(cls, *args, **kwargs):
        if not args:
            return False
        if isinstance(args[0], bool):
            return args[0]
        if isinstance(args[0], int):
            return bool(args[0])
        value = str(args[0]).lower()
        if value in cls.TRUE_VALUES:
            return True
        elif value in cls.FALSE_VALUES:
            return False
        else:
            raise ValueError("Could not convert {} to a valid bool value".format(value))


# We should really 'unify' the variable names, between configuration, osenv and yaml
# However, one big hurdle is the fact that customarily they follow different conventions, and to
# add to the complexity, YAML would generate them with dotted notation, which bash wouldn't even
# allow as env vars.
# One option would be 'encode' all the keys to all lowercase, and replace dots with underscores
def choose(key, default, config=None, config_attr=None):
    """ Helper method to retrieve a config value that may (or may) not have been defined

    This method tries (safely) to return a configuration option from a configuration object (
    possibly None) the OS Env and, finally a default value.

    In priority descending order, it will return:

    - the option from the ```config``` object;
    - the OS Env variable value
    - the default value

    :param key: the name of the option to retrieve
    :type key: str
    :param default: the default value to return, if all else fails
    :param config: an optional configuration namespace, as returned by ```argparse```
    :type config: L{argparse.Namespace}
    :param config_attr: optionally, the config attribute name may be different from ```key```
    :type config_attr: str or None
    :return: the value of the option, if defined anywhere, or ```default``` (should never be
        ```None```)
    :rtype: str
    """
    # TODO: should add the option to use a YAML configuration file
    config_attr = config_attr or key
    config_value = None
    if config and hasattr(config, config_attr):
        config_value = getattr(config, config_attr)
    os_env_value = os.getenv(key, default)
    return config_value if config_value is not None else os_env_value


def version():
    for line in settings():
        m = re.match(VERSION_PATTERN, line)
        if m:
            return m.group('version')


def build():
    for line in settings():
        m = re.match(VERSION_PATTERN, line)
        if m:
            return m.group('build')


def settings(basedir=None):
    """ Returns the Project's settings as an iterable"""
    basedir = basedir or pathlib.Path.cwd()
    build_settings = basedir / "build.settings"
    if not build_settings.exists():
        ex = FileNotFoundError()
        ex.filename = str(build_settings.absolute())
        ex.errno = 'ENOENT'
        ex.strerror = "Build settings file missing (no version information available)"
        raise ex
    with build_settings.open() as f:
        for line in f.readlines():
            if not line.startswith("#"):
                yield line
