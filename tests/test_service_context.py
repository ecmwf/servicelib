# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import os

import pytest

from servicelib.context.service import ServiceContext
from servicelib.core import Request


def test_trackers_vary_per_request(servicelib_yaml):
    c1 = ServiceContext("some-service", "/some/dir", None, Request())
    c2 = ServiceContext("some-service", "/some/dir", None, Request())
    assert c1.tracker != c2.tracker


def test_create_temp_file(context):
    fname = context.create_temp_file()
    assert os.access(fname, os.F_OK)


def test_temp_files_are_removed(context):
    fname = context.create_temp_file()
    context.cleanup()
    assert not os.access(fname, os.F_OK)


def test_handle_errors_in_temp_file_cleanup(context):
    fname = context.create_temp_file()
    os.unlink(fname)
    context.cleanup()
    assert not os.access(fname, os.F_OK)


def test_create_result(context):
    r = context.create_result("text/plain").as_dict()
    assert "location" in r
    assert "contentType" in r
    assert "contentLength" in r


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


def test_download_unsupported_url_schemes(context):
    with pytest.raises(Exception) as exc:
        context.get_data({"location": "ftp://localhost/whatever"})
    assert str(exc.value) == "ftp://localhost/whatever: Unsupported URL scheme 'ftp'"


def test_download_errors(context):
    with pytest.raises(Exception):
        context.get_data({"location": "http://no-such-host"})
