# Copyright (C) 2009 ECMWF

"""Data types and code common to client- and server-side."""

from __future__ import absolute_import, unicode_literals

import re
import uuid

from servicelib import errors, logutils
from servicelib import encoding as json
from servicelib.metadata import Metadata


__all__ = [
    "Request",
    "Response",
    "is_valid_tracker",
    "tracker",
]


def make_id(prefix):
    """Returns an *unique* UUID.

    """
    return "%s-%s" % (prefix, uuid.uuid4().hex)


def tracker():
    """Generates a tracker string.

    """
    return make_id("tracker")


_tracker_re = re.compile(r"^tracker-[0-9a-f]{32}$")


def is_valid_tracker(t):
    """Returns true when `t` is a valid tracker ID.

    """
    try:
        return _tracker_re.match(t) is not None
    except Exception:
        return False


class Request(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = dict(kwargs)
        self.kwargs.setdefault("tracker", tracker())

    @property
    def tracker(self):
        return self.kwargs["tracker"]

    @property
    def uid(self):
        return self.kwargs.get("uid")

    @property
    def http_headers(self):
        ret = {}
        for k, v in self.kwargs.items():
            ret["x-servicelib-{}".format(k)] = json.dumps(v)
        return ret

    @property
    def http_body(self):
        return json.dumps(self.args)

    @classmethod
    def from_http(cls, body, headers):
        args = json.loads(body)
        if not isinstance(args, list):
            raise ValueError("List expected")

        kwargs = {}
        for k, v in headers.items():
            k = k.lower()
            if k.startswith("x-servicelib-"):
                kwargs[k[len("x-servicelib-") :]] = json.loads(v)

        return cls(*args, **kwargs)

    def __eq__(self, other):
        if isinstance(other, Request):
            return self.args == other.args and self.kwargs == other.kwargs
        return False


class Response(object):

    log = logutils.get_logger(__name__)

    def __init__(self, value, metadata, encoded=None):
        self.value = value
        self.metadata = metadata
        self._encoded_body = encoded

    @property
    def http_status(self):
        if hasattr(self.value, "http_response_code"):
            return self.value.http_response_code
        return "200 OK"

    @property
    def http_headers(self):
        return {
            "x-servicelib-{}".format(k): v
            for (k, v) in self.metadata.as_http_headers().items()
        }

    @property
    def http_body(self):
        if self._encoded_body is None:
            self._encoded_body = json.dumps(self.value).encode("utf-8")
        return self._encoded_body

    @classmethod
    def from_http(cls, status, body, headers):
        cls.log.debug("from_http(status=%s, body=<%s>): Entering", status, body)
        body_decoded = json.loads(body)
        if status.startswith("200 "):
            value = body_decoded
        else:
            value = errors.Serializable.from_dict(body_decoded)
        metadata = Metadata.from_http_headers(
            {
                k[len("x-servicelib-") :]: v
                for (k, v) in headers.items()
                if k.startswith("x-servicelib-")
            }
        )
        return cls(value, metadata, body)

    def __repr__(self):
        return "Response(value={!r}, metadata={!r})".format(self.value, self.metadata)

    def __eq__(self, other):
        if isinstance(other, Response):
            return self.value == other.value and self.metadata == other.metadata
        return False
