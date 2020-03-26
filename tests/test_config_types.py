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

from servicelib.config import types


def test_config_dict_get():
    s = types.ConfigDict()
    with pytest.raises(KeyError):
        s.get("foo")

    s = types.ConfigDict({"foo": 42})
    assert s.get("foo") == 42
    with pytest.raises(KeyError):
        s.get("bar")

    s = types.ConfigDict({"foo": 42, "bar": {"baz": 43}})
    assert s.get("foo") == 42
    assert s.get("bar") == {"baz": 43}
    assert s.get("bar.baz") == 43


def test_config_dict_delete():
    s = types.ConfigDict({"foo": 42, "bar": {"baz": 43}})

    with pytest.raises(KeyError):
        s.delete("no-such-key")

    with pytest.raises(KeyError):
        s.delete("no-such-key.no-such-key-either")

    with pytest.raises(KeyError):
        s.delete("foo.no-such-key")

    s.delete("foo")
    with pytest.raises(KeyError):
        s.get("foo")

    s.delete("bar")
    with pytest.raises(KeyError):
        s.get("bar.baz")
    with pytest.raises(KeyError):
        s.get("bar")


def test_config_dict_set():
    s = types.ConfigDict()
    with pytest.raises(KeyError):
        s.get("foo")

    s.set("foo", 42)
    assert s.get("foo") == 42

    s.set("bar.baz", 43)
    assert s.get("bar") == {"baz": 43}
    assert s.get("bar.baz") == 43
    with pytest.raises(ValueError):
        s.set("", 42)


def test_config_dict_supports_array_indexes():
    s = types.ConfigDict()
    s.set("foo.2", "bar")
    assert s.get("foo") == [None, None, "bar"]
    assert s.get("foo.0") is None
    assert s.get("foo.1") is None
    assert s.get("foo.2") == "bar"

    with pytest.raises(ValueError) as exc:
        s.set("foo.-42", "Cannot happpen")
    assert str(exc.value) == "Invalid key `foo.-42`"

    with pytest.raises(KeyError):
        s.get("foo.3")

    with pytest.raises(KeyError):
        s.get("foo.-1")

    s.set("foo.0", 42)
    assert s.get("foo") == [42, None, "bar"]

    s.delete("foo.1")
    assert s.get("foo") == [42, "bar"]

    with pytest.raises(ValueError) as exc:
        s.delete("foo.-1")
    assert str(exc.value) == "Invalid key `foo.-1`"


def test_config_dict_as_dict():
    s = types.ConfigDict({"foo": 42, "bar": {"baz": 43}})
    assert s.as_dict() == {"foo": 42, "bar": {"baz": 43}}


def test_config_dict_reset():
    s = types.ConfigDict({"moo": 1})
    assert s.get("moo") == 1

    s.reset({"foo": 42, "bar": {"baz": 43}})
    with pytest.raises(KeyError):
        s.get("moo")
    assert s.as_dict() == {"foo": 42, "bar": {"baz": 43}}
