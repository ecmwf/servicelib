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


def test_command_line_options(worker_cmd):
    with worker_cmd("--worker-num-processes=1") as w:
        res = w.http_get("/stats").json()
        assert res["config"]["num_processes"] == 1

    with worker_cmd("--worker-num-processes=2") as w:
        res = w.http_get("/stats").json()
        assert res["config"]["num_processes"] == 2


def test_invalid_command_line_options(worker_cmd):
    with pytest.raises(Exception) as exc:
        w = worker_cmd("--pepe")
        with w:
            pass
    assert "unrecognized arguments: --pepe" in str(exc.value)
