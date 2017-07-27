from __future__ import unicode_literals

try:
    from configparser import ConfigParser as compat_configparser  # Python 3
except ImportError:
    from ConfigParser import ConfigParser as compat_configparser  # Python 2

__all__ = ['compat_configparser']
