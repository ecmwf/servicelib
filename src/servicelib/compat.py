# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import six

__all__ = [
    "PY2",
    "PY3",
    "Path",
    "env_var",
    "open",
    "raise_from",
    "scandir",
    "string_types",
    "urlparse",
]

PY2 = six.PY2
PY3 = six.PY3
raise_from = six.raise_from
string_types = six.string_types
urlparse = six.moves.urllib_parse.urlparse

_builtin_open = open

try:
    from pathlib import Path
    from os import scandir

    def env_var(k, v):
        return k, v

    open = _builtin_open
except ImportError:
    from pathlib2 import Path
    from scandir import scandir

    def env_var(k, v):
        return k.encode("utf-8"), v.encode("utf-8")

    def open(path, *args, **kwargs):
        return _builtin_open(str(path), *args, **kwargs)
