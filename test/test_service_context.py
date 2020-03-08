# Copyright (c) ECMWF 2020

from __future__ import absolute_import, unicode_literals

import os
import subprocess

import pytest

from servicelib import process
from servicelib.context.service import ServiceContext
from servicelib.compat import env_var
from servicelib.core import Request


def test_trackers_vary_per_request(servicelib_ini):
    c1 = ServiceContext("some-service", "/some/dir", None, Request())
    c2 = ServiceContext("some-service", "/some/dir", None, Request())
    assert c1.tracker != c2.tracker


@pytest.fixture(scope="function")
def context(request, monkeypatch, tmp_path):
    home_dir = tmp_path / "service-home"
    home_dir.mkdir()

    scratch_dirs = [tmp_path / d for d in ("scratch01", "scratch02")]
    for d in scratch_dirs:
        d.mkdir()
    scratch_dirs = ":".join(str(d) for d in scratch_dirs)
    monkeypatch.setenv(*env_var("SERVICELIB_SCRATCH_DIRS", scratch_dirs))
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_CLASS", "local-files"))
    monkeypatch.setenv(*env_var("SERVICELIB_RESULTS_DIRS", scratch_dirs))

    return ServiceContext("some-service", str(home_dir), None, Request())


def test_create_temp_file(context):
    fname = context.create_temp_file()
    assert os.access(fname, os.F_OK)


def test_temp_files_are_removed(context):
    fname = context.create_temp_file()
    context.cleanup()
    assert not os.access(fname, os.F_OK)


def test_create_result(context):
    r = context.create_result("text/plain").as_dict()
    assert "location" in r
    assert "contentType" in r
    assert "contentLength" in r


def test_spawn_process(context):
    cmdline = ["df", "-h"]

    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("df", cmdline)

        def results(self):
            return self.output.decode("utf-8")

    res = context.spawn_process(p())
    assert res == subprocess.check_output(cmdline).decode("utf-8")


def test_spawn_invalid_process(context):
    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("no-such-program", ["/usr/bin/no-such-program"])

        def results(self):
            return self.output.decode("utf-8")

    with pytest.raises(Exception) as exc:
        context.spawn_process(p())
    assert str(exc.value).startswith(
        "Failed to start '/usr/bin/no-such-program': [Errno 2] No such file or directory"
    )


def test_spawn_failing_process(context):
    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("ls-root", ["ls", "-l", "/root"])

        def results(self):
            return self.output.decode("utf-8")

    with pytest.raises(Exception) as exc:
        context.spawn_process(p())
    assert str(exc.value).startswith("'ls-root' failed, return code 2")


def test_get_data_downloads_only_once(context):
    location = {"location": "https://www.ecmwf.int/"}
    one = context.get_data(location)
    assert one.stat()

    two = context.get_data(location)
    assert two.stat()
    assert one == two


def test_get_data_files_persist(context):
    fname = context.get_data({"location": "https://www.ecmwf.int/"})
    context.cleanup()
    assert fname.stat()
