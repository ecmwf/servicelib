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
        *env_var("SERVICELIB_RESULTS_DIRS", json.dumps([str(d) for d in dirs]))
    )

    return results.LocalFileResults()


def test_create_local_result(local_files_results):
    r = local_files_results.create("text/plain")
    assert r.location.startswith("file:///")


@pytest.mark.parametrize(
    "content_type,expected_ext",
    [
        ("application/x-netcdf", ".nc"),
        ("application/x-bufr", ".bufr"),
        ("application/x-grib", ".grib"),
        ("application/x-odb", ".odb"),
        ("unknown/content-type", ""),
    ],
)
def test_results_extension(local_files_results, content_type, expected_ext):
    r = local_files_results.create(content_type)
    assert r.path.suffix == expected_ext


@pytest.fixture
def http_files_results(request, monkeypatch, tmp_path):
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_CLASS", "http-files"))
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_HTTP_PORT", "8080"))

    dirs = [tmp_path / d for d in ("scratch01", "scratch02")]
    for d in dirs:
        d.mkdir()
    monkeypatch.setenv(
        *env_var("SERVICELIB_RESULTS_DIRS", json.dumps([str(d) for d in dirs]))
    )

    return results.HttpFileResults()


def test_create_http_result(http_files_results):
    r = http_files_results.create("text/plain")
    assert r.location.startswith("http://")


def test_http_results_port_defaults_to_worker_port(monkeypatch, tmp_path):
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_HTTP_HOSTNAME", "localhost"))
    monkeypatch.setenv(
        *env_var("SERVICELIB_RESULTS_DIRS", json.dumps([str(tmp_path / "wherever")]))
    )
    monkeypatch.setenv(*env_var("SERVICELIB_WORKER_PORT", "42"))

    r = results.HttpFileResults().create("text/plain")
    assert r.location.startswith("http://localhost:42/")

    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_HTTP_PORT", "8000"))
    r = results.HttpFileResults().create("text/plain")
    assert r.location.startswith("http://localhost:8000/")


def test_invalid_http_results_port(monkeypatch, tmp_path):
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_HTTP_HOSTNAME", "localhost"))
    monkeypatch.setenv(
        *env_var("SERVICELIB_RESULTS_DIRS", json.dumps([str(tmp_path / "wherever")]))
    )
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_HTTP_PORT", "pepe"))
    with pytest.raises(Exception) as exc:
        results.HttpFileResults()
    assert str(exc.value).startswith("Invalid config variable results.http_port=pepe")


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


def test_write_without_close(local_results):
    r = local_results.create("text/plain")
    with pytest.raises(Exception) as exc:
        r.write("foo")
    assert str(exc.value).endswith(": Not open")


def test_error_in_closing_result(local_results):
    r = local_results.create("text/plain")
    old_file_obj = None
    try:
        with pytest.raises(Exception) as exc:
            with r:
                old_file_obj = r._file_obj
                r._file_obj = None
        assert str(exc.value) == "'NoneType' object has no attribute 'close'"
    finally:
        old_file_obj.close()


def test_error_in_closing_result_does_not_hide_errors(local_results):
    r = local_results.create("text/plain")
    old_file_obj = None
    try:
        with pytest.raises(Exception) as exc:
            with r:
                old_file_obj = r._file_obj
                r._file_obj = None
                raise Exception("Boom!")
        assert str(exc.value) == "Boom!"
    finally:
        old_file_obj.close()


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


def test_results_metadata(local_results):
    r = local_results.create("text/plain")
    r["foo"] = 42
    r["bar"] = "43"
    assert r.as_dict()["foo"] == 42
    assert r.as_dict()["bar"] == "43"


@pytest.mark.parametrize(
    "reserved_key,value",
    [
        ("location", "http://some-url"),
        ("contentType", "text/plain"),
        ("contentLength", 42),
    ],
)
def test_invalid_results_metadata(local_results, reserved_key, value):
    r = local_results.create("text/plain")
    with pytest.raises(ValueError) as exc:
        r[reserved_key] = value
    assert str(exc.value) == "Invalid key '{}'".format(reserved_key)


@pytest.fixture
def cds_cache_results(request, monkeypatch, tmp_path):
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_CLASS", "cds-cache"))
    monkeypatch.setenv(
        *env_var(
            "SERVICELIB_RESULTS_CDS_DOWNLOAD_HOST", "some-host.copernicus-climate.eu"
        )
    )
    monkeypatch.setenv(
        *env_var("SERVICELIB_RESULTS_CDS_DOWNLOAD_PATH_PREFIX", "/cache-compute-0000/")
    )

    dirs = [tmp_path / d for d in ("scratch01", "scratch02")]
    for d in dirs:
        d.mkdir()
    monkeypatch.setenv(
        *env_var("SERVICELIB_RESULTS_DIRS", json.dumps([str(d) for d in dirs]))
    )

    return results.CDSCacheResults()


def test_cds_cache_results(cds_cache_results):
    r = cds_cache_results.create("application/postscript")
    assert r.location.startswith(
        "http://some-host.copernicus-climate.eu/cache-compute-0000"
    )


def test_invalid_results_factory(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_CLASS", "no-such-impl"))
    with pytest.raises(Exception) as exc:
        results.instance()
    assert str(exc.value) == "Invalid value for `results.class`: no-such-impl"
