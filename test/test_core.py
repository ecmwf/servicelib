# Copyright (C) ECMWF 2017.

from __future__ import absolute_import, unicode_literals

import pytest

from servicelib import core, errors
from servicelib.metadata import Metadata


@pytest.mark.parametrize("tracker", [core.tracker() for _ in range(100)])
def test_tracker_format(tracker):
    assert core.is_valid_tracker(tracker)


def test_invalid_tracker():
    assert not core.is_valid_tracker("foo")


def test_request_serialize_roundtrip():
    req = core.Request(["foo", 42, 42.0], cache=False, tracker=core.tracker())
    ser = core.Request.from_http(req.http_body, req.http_headers)
    assert ser == req


@pytest.mark.parametrize("value", ["some-value", errors.BadRequest("Oops"),])
def test_response_serialize_roundtrip(value):
    res = core.Response(value, Metadata("some-service"))
    ser = core.Response.from_http(res.http_status, res.http_body, res.http_headers)
    assert ser == res
