# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, print_function, unicode_literals

import copy

from servicelib import logutils


__all__ = [
    "ConfigDict",
]


class ConfigDict(object):

    log = logutils.get_logger(__name__)

    def __init__(self, values=None):
        if values is None:
            values = {}
        else:
            values = copy.deepcopy(values)
        self._values = values

    def get(self, key):
        """Returns the value for the given key, raising ``KeyError`` if the
        key is not found.

        """
        bits = key.split(".")

        try:
            b = int(bits[-1], base=10)
        except ValueError:
            pass
        else:
            if b < 0:
                raise KeyError(key)
            values = self.get(".".join(bits[:-1]))
            try:
                return values[b]
            except Exception:
                raise KeyError(key)

        values = self._values
        while bits:
            b = bits.pop(0)
            if b not in values:
                self.log.debug("Key %s not found in %s", key, self._values)
                raise KeyError(key)
            if not bits:
                return values[b]
            values = values[b]

    def set(self, key, value):
        """Sets the value for the given key.

        """
        if not key:
            raise ValueError("Invalid key `{}`".format(key))
        bits = key.split(".")
        values = self._values
        prev = None
        prev_b = None
        while bits:
            b = bits.pop(0)
            if not bits:
                try:
                    b = int(b, base=10)
                    if b < 0:
                        raise KeyError("Invalid key `{}`".format(key))
                    values = prev[prev_b]
                    if type(values) is not list:
                        values = prev[prev_b] = []
                    values.extend([None] * (b + 1 - len(values)))
                except ValueError:
                    pass
                except KeyError as exc:
                    raise ValueError(exc.args[0])
                values[b] = copy.deepcopy(value)
            else:
                prev = values
                prev_b = b
                values = values.setdefault(b, {})

    def reset(self, new_values):
        """Resets the values.

        """
        self._values = copy.deepcopy(new_values)

    def delete(self, key):
        """Deletes the value for the given key, raising ``KeyError`` if the
        key is not found.

        """
        bits = key.split(".")
        values = self._values
        while bits:
            b = bits.pop(0)
            print("b: {}".format(b))
            if not bits:
                try:
                    b = int(b, base=10)
                    if b < 0:
                        raise KeyError("Invalid key `{}`".format(key))
                except KeyError as exc:
                    raise ValueError(exc.args[0])
                except ValueError:
                    pass
                try:
                    del values[b]
                except TypeError:
                    raise KeyError("Invalid key `{}`".format(key))
                return
            if b not in values:
                raise KeyError(key)
            values = values[b]

    def as_dict(self):
        """Returns a dict version of the keys and values.

        """
        return copy.deepcopy(self._values)

    def __deepcopy__(self, memo):
        ret = self.__class__()
        ret._values = copy.deepcopy(self._values, memo)
        return ret
