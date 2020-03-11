# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Tests for errors raised in services."""

import json
import sys

import pytest

from servicelib import compat, errors


@pytest.fixture(
    params=[
        ("Exception", "foo"),
        ("FloatingPointError", "bar"),
        ("ImportWarning", "oops"),
        ("KeyError", "moo"),
    ]
)
def builtin_error(request):
    exc_name, exc_message = request.param
    exc_class = __builtins__[exc_name]
    return exc_name, exc_class, exc_message


def test_built_in_error_types_are_preserved(worker, builtin_error):
    """Original types of built-in errors are preserved.

    """
    exc_name, exc_class, exc_message = builtin_error

    with pytest.raises(errors.TaskError) as exc:
        worker.http_post("/services/raise", data=json.dumps([exc_name, exc_message]))

    exc = exc.value.exc_value
    assert type(exc) == exc_class
    assert exc.args[0] == exc_message


@pytest.fixture(
    params=[("BadRequest", "foo"), ("RetryLater", "Server too busy", "42"),]
)
def serializable_error(request):
    exc_name, exc_args = request.param[0], list(request.param[1:])
    exc_class = getattr(errors, exc_name)
    return exc_name, exc_class, exc_args


def test_serializable_errors_are_preserved(worker, serializable_error):
    """Errors subclassing `servicelib.errors.Serializable` are preserved.

    """
    exc_name, exc_class, exc_args = serializable_error

    with pytest.raises(exc_class) as exc:
        worker.http_post("/services/raise", data=json.dumps([exc_name] + exc_args))

    assert str(exc.value) == exc_args[0]


def test_io_errors_preserved(worker):
    """Errors of type `IOError` are more-or-less preserved.

    """
    with pytest.raises(errors.TaskError) as exc:
        worker.http_post(
            "/services/raise", data=json.dumps(["IOError", "/no-such-file.txt"])
        )
    exc = exc.value.exc_value
    if compat.PY2:
        assert isinstance(exc, IOError)
    else:
        assert isinstance(exc, FileNotFoundError)
    assert str(exc) == "[Errno 2] No such file or directory"


def test_custom_errors_not_preserved(worker):
    """The type of on-builtin errors is not preserved.

    """
    with pytest.raises(errors.TaskError) as exc:
        worker.http_post("/services/raise", data=json.dumps(["CustomError", "Oops!"]))

    exc = exc.value.exc_type
    assert exc == Exception


try:
    raise Exception("Some error")
except Exception:
    exc_type, exc_value, exc_tb = sys.exc_info()


@pytest.mark.parametrize(
    "error",
    [
        errors.BadRequest("foo"),
        errors.CommError("Can't hear you"),
        errors.RetryLater("Server too busy", 42),
        errors.ServiceError("Who knows"),
        errors.TaskError("some-service", exc_type, exc_value, exc_tb),
        errors.Timeout("I'm tired"),
    ],
)
def test_serialize_roundtrip(error):
    ser = error.as_dict()
    err = errors.Serializable.from_dict(ser)
    assert err == error


@pytest.mark.parametrize(
    "err, expected",
    [(errors.BadRequest("pepe"), "pepe"), (errors.BadRequest(None), "None"),],
)
def test_string_representation(err, expected):
    assert str(err) == expected
