# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, print_function, unicode_literals

import time
import sys

from multiprocessing import Process, Pipe

import pytest
import requests

from servicelib import utils
from servicelib.config import client


def test_config_server_in_read_write_mode(config_server):
    config_server.initial_config = {"foo": 42}
    config_server.start()
    c = config_server.client
    assert c.get("foo") == 42

    c.set("foo", 43)
    assert c.get("foo") == 43

    c.delete("foo")
    with pytest.raises(Exception) as exc:
        c.get("foo")
    assert str(exc.value).startswith("No config value for `foo`")


def test_config_server_in_read_only_mode(config_server):
    config_server.initial_config = {"foo": 42}
    config_server.read_only = True
    config_server.start()
    c = config_server.client
    assert c.get("foo") == 42

    with pytest.raises(Exception) as exc:
        c.set("foo", 43)
    assert str(exc.value) == "Config server in read-only mode"
    assert c.get("foo") == 42

    with pytest.raises(Exception) as exc:
        c.delete("foo")
    assert str(exc.value) == "Config server in read-only mode"
    assert c.get("foo") == 42


def test_client_uses_cached_values_when_server_is_down(config_server):
    config_server.initial_config = {"foo": 42}
    config_server.start()
    assert config_server.client.get("foo") == 42

    config_server.stop()
    with pytest.raises(requests.ConnectionError):
        requests.get(config_server.client.url)
    time.sleep(config_server.client.poll_interval + 1)
    assert config_server.client.get("foo") == 42


def test_client_needs_cached_values_when_server_is_down(config_server):
    config_server.stop()
    with pytest.raises(requests.ConnectionError):
        requests.get(config_server.client.url)

    with pytest.raises(requests.ConnectionError):
        config_server.client.get("foo")

    config_server.initial_config = {"foo": 42}
    config_server.start()
    assert config_server.client.get("foo") == 42


def test_settings_change_in_child_process(config_server):
    config_server.start()

    parent_conn, child_conn = Pipe()

    def child(conn):
        c = client.instance(url=config_server.url)
        while True:
            try:
                msg = conn.recv()
                if msg == "quit":
                    return
                conn.send(c.get(msg))
            except Exception as exc:
                print(exc, file=sys.stderr)
                sys.stderr.flush()

    config_server.client.set("foo", 42)

    p = Process(target=child, args=(child_conn,))
    p.start()

    try:
        parent_conn.send("foo")
        assert parent_conn.recv() == 42

        config_server.client.set("foo", 43)
        time.sleep(config_server.client.poll_interval + 1)

        parent_conn.send("foo")
        assert parent_conn.recv() == 43
    finally:
        parent_conn.send("quit")
        p.join()


@pytest.mark.parametrize("invalid_key", ["", None])
def test_set_with_invalid_key(config_server, invalid_key):
    with pytest.raises(ValueError) as exc:
        config_server.client.set(invalid_key, 42)
    assert str(exc.value) == "Invalid key `{}`".format(invalid_key)


def test_delete_entry(config_server):
    config_server.initial_config = {"foo": 42}
    config_server.start()
    c = config_server.client
    assert c.get("foo") == 42

    with pytest.raises(KeyError):
        c.delete("no-such-key")

    c.delete("foo")
    with pytest.raises(Exception) as exc:
        c.get("foo")
    assert str(exc.value).startswith("No config value for `foo`")


def test_health_endpoint(config_server):
    config_server.start()
    res = config_server.http_get("/health")
    assert res.status_code == 200


def test_run_in_foreground(config_server):
    config_server.initial_config = {"foo": 42}
    config_server.start(background=False)
    utils.wait_for_url(config_server.url)

    assert config_server.client.get("foo") == 42


def test_empty_post_request(config_server):
    config_server.initial_config = {"foo": 42}
    config_server.start()

    res = config_server.http_post(
        "/settings/foo", headers={"content-type": "application/json"}
    )
    assert res.status_code == 200
    assert config_server.client.get("foo") == 42


def test_error_saving_config(config_server):
    config_server.initial_config = {"foo": 42}
    config_server.start()
    c = config_server.client
    assert c.get("foo") == 42

    config_server.config_file.parent.chmod(0o555)
    try:
        with pytest.raises(Exception) as exc:
            c.set("foo", 43)
        assert "Cannot save config" in str(exc.value)
        assert c.get("foo") == 42

        with pytest.raises(Exception) as exc:
            c.delete("foo")
        assert "Cannot save config" in str(exc.value)
        assert c.get("foo") == 42
    finally:
        config_server.config_file.parent.chmod(0o755)
