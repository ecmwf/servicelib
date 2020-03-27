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

import json


__all__ = [
    "dumps",
    "loads",
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
        return json.JSONEncoder.default(self, obj)


def dumps(obj, *args, **kwargs):
    """Serialize ``obj`` to a JSON-formatted string.

    Overrides keyword argument ``cls`` with a reference to `JSONEncoder`.

    """
    kwargs["cls"] = JSONEncoder
    return json.dumps(obj, *args, **kwargs)


loads = json.loads
