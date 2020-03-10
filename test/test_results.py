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

from servicelib import results
from servicelib.compat import Path, env_var


@pytest.fixture
def local_files_results(request, monkeypatch, tmp_path):
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_CLASS", "local-files"))

    dirs = [tmp_path / d for d in ("scratch01", "scratch02")]
    for d in dirs:
        d.mkdir()
    monkeypatch.setenv(
        *env_var("SERVICELIB_RESULTS_DIRS", ":".join(str(d) for d in dirs))
    )

    return results.LocalFileResults()


def test_create_local_result(local_files_results):
    r = local_files_results.create("text/plain")
    assert r.location.startswith("file:///")


@pytest.fixture
def http_files_results(request, monkeypatch, tmp_path):
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_CLASS", "http-files"))
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_HTTP_PORT", "8080"))

    dirs = [tmp_path / d for d in ("scratch01", "scratch02")]
    for d in dirs:
        d.mkdir()
    monkeypatch.setenv(
        *env_var("SERVICELIB_RESULTS_DIRS", ":".join(str(d) for d in dirs))
    )

    return results.HttpFileResults()


def test_create_http_result(http_files_results):
    r = http_files_results.create("text/plain")
    assert r.location.startswith("http://")


@pytest.fixture(params=["local_files_results", "http_files_results"])
def local_results(request):
    return pytest.lazy_fixture(request.param)


def test_write(local_results):
    r = local_results.create("text/plain")
    assert r.length == 0
    with r:
        n = r.write("123".encode("utf-8"))
        assert n == 3
        n = r.write("45678".encode("utf-8"))
        assert n == 5
    assert r.length == 8


def test_result_as_local_file(local_results):
    r = local_results.create("text/plain")
    assert local_results.as_local_file(r.as_dict()) == Path(r.path)


def test_invalid_size_result_as_local_file(local_results):
    r = local_results.create("text/plain")
    r = r.as_dict()
    r["contentLength"] = 42
    assert local_results.as_local_file(r) is None


def test_invalid_path_result_as_local_file(local_results):
    res = local_results.as_local_file({"location": "/etc/passwd", "contentLength": 42})
    assert res is None
