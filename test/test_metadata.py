# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

from servicelib.metadata import Metadata


def test_roundtrip_encoding():
    m = Metadata("some-service")
    ser = Metadata.from_dict(m.as_dict())
    assert ser == m
