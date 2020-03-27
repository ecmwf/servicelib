# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import json
import os
import socket
import time

from servicelib import compat, logutils
from servicelib.timer import Timer


__all__ = []


HOSTNAME = socket.getfqdn().split(".")[0]


class Metadata(object):

    log = logutils.get_logger(__name__)

    def __init__(self, name=None):
        self._name = name
        self._timers = {}
        self._extra = {}
        self._kids = []
        self._notes = {}
        self._host = HOSTNAME
        self._start = time.time()
        self._pid = os.getpid()
        self._stop = 0.0

    def annotate(self, key, value):
        if isinstance(value, compat.string_types) or isinstance(
            value, (int, float, list, dict, tuple)
        ):
            self._notes[key] = value

    def update_metadata(self, other):
        if self != other:
            self._kids.append(other)

    def timer(self, name):
        if name not in self._timers:
            self._timers[name] = Timer()
        return self._timers[name]

    def start(self):
        self._start = time.time()

    def stop(self):
        self._stop = time.time()

    def as_http_headers(self):
        ret = {
            "task": self._name,
            "host": self._host,
            "pid": str(self._pid),
            "start": str(self._start),
            "stop": str(self._stop),
            "kids": json.dumps([k.as_dict() for k in self._kids]),
        }

        ret.update(
            {"note-{}".format(k): json.dumps(v) for (k, v) in self._notes.items()}
        )

        timers = dict((k, v.as_dict()) for k, v in self._timers.items())
        timers.update(self._extra)
        ret["timers"] = json.dumps(timers)

        return ret

    @classmethod
    def from_http_headers(cls, h):
        ret = cls(h["task"])
        ret._timers = {
            k: Timer.from_dict(v) for k, v in json.loads(h["timers"]).items()
        }
        ret._kids = [cls.from_dict(k) for k in json.loads(h["kids"])]
        ret._host = h["host"]
        ret._pid = int(h["pid"])
        ret._start = float(h["start"])
        ret._stop = float(h["stop"])
        ret._notes = {
            k[len("note-") :]: json.loads(v)
            for (k, v) in h.items()
            if k.startswith("note-")
        }
        return ret

    def as_dict(self):
        r = {
            "task": self._name,
            "host": self._host,
            "pid": self._pid,
        }
        r["kids"] = [k.as_dict() for k in self._kids]
        r["timers"] = dict((k, v.as_dict()) for k, v in self._timers.items())
        r["timers"].update(self._extra)

        if self._start:
            r["start"] = self._start

        if self._stop:
            r["stop"] = self._stop

        r["notes"] = self._notes
        r.update(self._notes)
        return r

    @classmethod
    def from_dict(cls, d):
        ret = cls(d["task"])
        ret._timers = {k: Timer.from_dict(v) for k, v in d["timers"].items()}
        ret._kids = [cls.from_dict(k) for k in d["kids"]]
        ret._notes = d["notes"]
        ret._host = d["host"]
        ret._pid = d["pid"]
        if "start" in d:
            ret._start = d["start"]
        if "stop" in d:
            ret._stop = d["stop"]
        return ret

    def __repr__(self):
        return (
            "Metadata(name={!r}, "
            "timers={!r}, "
            "extra={!r}, "
            "kids={!r}, "
            "notes={!r}, "
            "host={!r}, "
            "start={!r}, "
            "pid={!r}, "
            "stop={!r})"
        ).format(
            self._name,
            self._timers,
            self._extra,
            self._kids,
            self._notes,
            self._host,
            self._start,
            self._pid,
            self._stop,
        )

    def __eq__(self, other):
        if isinstance(other, Metadata):
            return (
                self._name == other._name
                and self._timers == other._timers
                and self._extra == other._extra
                and self._kids == other._kids
                and self._notes == other._notes
                and self._host == other._host
                and self._pid == other._pid
                and abs(self._start - other._start) < 0.01
                and abs(self._stop - other._stop) < 0.01
            )
        return False
