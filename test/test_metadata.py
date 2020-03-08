# Copyright (c) ECMWF 2019

from __future__ import absolute_import, unicode_literals

from servicelib.metadata import Metadata


def test_roundtrip_encoding():
    m = Metadata("some-service")
    ser = Metadata.from_dict(m.as_dict())
    assert ser == m
