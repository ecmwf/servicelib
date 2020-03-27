# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Assorted bits and pieces."""

from __future__ import absolute_import, unicode_literals

import time


__all__ = [
    "Timer",
]


class Timer(object):

    """A context manager for measuring execution time of code fragments."""

    def __init__(self):
        self._elapsed = 0.0
        self._start = None

    def start(self):
        """Start the timer.

        """
        self._start = time.time()

    def stop(self):
        """Stop the timer and invoke the handler.

        The attribute ``elapsed`` will contained the elapsed time since this
        timer was started.

        """
        if self._start is None:
            raise Exception("Timer %s has not been started" % self)

        now = time.time()
        self.elapsed += now - self._start

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def elapsed():
        def fget(self):
            return self._elapsed

        def fset(self, val):
            self._elapsed = val
            try:
                self.handler(self)
            except Exception:
                pass

        return locals()

    elapsed = property(**elapsed())

    def as_dict(self):
        return {
            "elapsed": self.elapsed,
            "start": self._start,
        }

    @classmethod
    def from_dict(cls, d):
        ret = cls()
        ret._elapsed = d["elapsed"]
        ret._start = d["start"]
        return ret

    def __eq__(self, other):
        if isinstance(other, Timer):
            return self._start == other._start and self._elapsed == other._elapsed
        return False
