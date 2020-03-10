# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""JSON support code."""

from __future__ import absolute_import, unicode_literals

import importlib
import json

try:
    from bson import json_util as mongo_json
except ImportError:
    mongo_json = None

from servicelib import logutils


__all__ = [
    "dump",
    "dumps",
    "load",
    "loads",
    "serializable",
]


# See http://tinyurl.com/ykhqrre
#
# ``str`` seems to do the job best, at least under Python 2.5:
#
#   * ``repr(1.1)``          gives ``1.1000000000000001``
#   * ``"%.3f" % 0.0001``    gives ``0.000``
#   * ``"%g" % time.time()`` gives ``1.27384e+09``
json.encoder.FLOAT_REPR = str


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        """Adds support for data types which implement ``as_dict``.

        """
        if hasattr(obj, "as_dict"):
            return obj.as_dict()
        if mongo_json is not None:
            return mongo_json.default(obj)
        return json.JSONEncoder.default(self, obj)


class JSONDecoder(json.JSONDecoder):

    """Decodes JSON objects with a ``_type`` field as objects of that Python
    class.

    """

    log = logutils.get_logger(__name__)

    def __init__(self, *args, **kwargs):
        """Constructor.

        Overrides keyword argument ``object_hook``.

        """

        def _hook(obj):
            if isinstance(obj, dict) and "_type" in obj:
                tname = str(obj["_type"])
                bits = tname.split(".")
                modname = ".".join(bits[:-1])
                clsname = bits[-1]
                mod = importlib.import_module(modname)
                cls = mod.__dict__[clsname]
                del obj["_type"]
                return cls(**obj)
            return obj

        kwargs["object_hook"] = _hook
        json.JSONDecoder.__init__(self, *args, **kwargs)


def dump(*args, **kwargs):
    """Serialize ``obj`` to a JSON-formatted string.

    Overrides keyword argument ``cls`` with a reference to `JSONEncoder`.

    """
    kwargs["cls"] = JSONEncoder
    return json.dump(*args, **kwargs)


def dumps(obj, *args, **kwargs):
    """Serialize ``obj`` to a JSON-formatted string.

    Overrides keyword argument ``cls`` with a reference to `JSONEncoder`.

    """
    kwargs["cls"] = JSONEncoder
    return json.dumps(obj, *args, **kwargs)


def load(fp, *args, **kwargs):
    """Deserialize ``fp`` (a ``.read()``-supporting file-like object
    containinga JSON document) to a Python object.

    Overrides keyword argument ``cls`` with a reference to `JSONDecoder`.

    """
    kwargs["cls"] = JSONDecoder
    return json.load(fp, *args, **kwargs)


def loads(data, *args, **kwargs):
    """Deserialize ``data`` (a ``str`` or ``unicode`` instance containing a
    JSON document) to a Python object.

    Overrides keyword argument ``cls`` with a reference to `JSONDecoder`.

    """
    kwargs["cls"] = JSONDecoder
    return json.loads(data, *args, **kwargs)


def serializable(cls):
    """Class decorator to add serialization capabilities.

    """

    def as_dict(self):
        """Provides a JSON-serializable representation of this object.

        """
        ret = {"_type": "%s.%s" % (self.__module__, self.__class__.__name__)}
        for field in self.__init__.__func__.func_code.co_varnames[1:]:
            try:
                ret[field] = getattr(self, field)
            except Exception:
                raise TypeError("%s not serializable: Missing field '%s'" % cls, field)
        return ret
