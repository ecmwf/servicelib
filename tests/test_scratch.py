# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import pytest

from servicelib import scratch
from servicelib.compat import env_var


def test_invalid_strategy(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_SCRATCH_STRATEGY", "invalid-strategy"))
    with pytest.raises(Exception) as exc:
        scratch.instance()
    assert str(exc.value) == "Invalid value for `scratch_strategy`: invalid-strategy"
