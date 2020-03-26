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
import pprint
import threading
import time

import pytest

from servicelib import client, errors
from servicelib.compat import env_var
from servicelib.timer import Timer


def test_call(broker):
    """Calling services works.

    """
    res = broker.execute("dump_request", "foo", 42, 42.0, None, True, False).result
    assert res["args"] == ["foo", 42, 42.0, None, True, False]


def test_call_with_non_serializable_arg(broker):
    with pytest.raises(Exception) as exc:
        broker.execute("echo", object())
    assert str(exc.value).startswith("object in call")


def test_call_with_error(broker):
    """Exceptions in services are handled properly.

    """
    with pytest.raises(errors.BadRequest) as exc:
        broker.execute("raise", "BadRequest", "some-error").result
    assert str(exc.value) == "some-error"


def test_execute_sync(broker):
    """Calls to ``servicelib.client.Broker.execute()`` are asynchronous

    Accessing the ``result`` or ``metadata`` fields of the returned value,
    however, are synchronous operations.

    """
    delay = 1

    with Timer() as t_complete:
        with Timer() as t_submit:
            res = broker.execute("sleep", delay)
        assert res.result

    assert t_submit.elapsed < delay
    assert t_complete.elapsed > delay

    with Timer() as t_complete:
        with Timer() as t_submit:
            res = broker.execute("sleep", delay)
        assert res.metadata

    assert t_submit.elapsed < delay
    assert t_complete.elapsed > delay


def test_nested_metadata(broker):
    res = broker.execute("echo", "foo")
    top = res.metadata.as_dict()["kids"][0]
    assert top["task"] == "echo", pprint.pformat(top)
    assert len(top["kids"]) == 0, pprint.pformat(top)

    res = broker.execute("proxy", "echo", "foo")
    top = res.metadata.as_dict()["kids"][0]
    assert top["task"] == "proxy", pprint.pformat(top)
    assert len(top["kids"]) == 1, pprint.pformat(top)
    top = top["kids"][0]
    assert top["task"] == "echo", pprint.pformat(top)
    assert len(top["kids"]) == 0, pprint.pformat(top)

    res = broker.execute("proxy", "proxy", "echo", "foo")
    top = res.metadata.as_dict()["kids"][0]
    assert top["task"] == "proxy", pprint.pformat(top)
    assert len(top["kids"]) == 1, pprint.pformat(top)
    top = top["kids"][0]
    assert top["task"] == "proxy", pprint.pformat(top)
    assert top["kids"][0]["task"] == "echo", pprint.pformat(top)
    assert len(top["kids"][0]["kids"]) == 0, pprint.pformat(top)

    res = broker.execute("proxy", "proxy", "proxy", "echo", "foo")
    top = res.metadata.as_dict()["kids"][0]
    assert top["task"] == "proxy", pprint.pformat(top)
    assert len(top["kids"]) == 1, pprint.pformat(top)
    top = top["kids"][0]
    assert top["task"] == "proxy", pprint.pformat(top)
    assert len(top["kids"]) == 1, pprint.pformat(top)
    top = top["kids"][0]
    assert top["task"] == "proxy", pprint.pformat(top)
    assert top["kids"][0]["task"] == "echo", pprint.pformat(top)
    assert len(top["kids"][0]["kids"]) == 0, pprint.pformat(top)


@pytest.mark.flaky(reruns=5)
def test_parallel_requests(broker):
    """All instances of services handle requests concurrently.

    """
    w = broker.worker_info
    num_calls = (w["num_processes"] * w["num_threads"]) + 1
    delay = 2
    overhead = 1

    def sleep():
        broker.execute("sleep", delay).wait()

    calls = []
    with Timer() as t:
        for _ in range(num_calls):
            c = threading.Thread(target=sleep)
            c.start()
            calls.append(c)

        for c in calls:
            c.join()

    assert t.elapsed >= 2 * delay
    assert t.elapsed < 2 * delay + overhead


def test_timeout_in_call(broker):
    timeout = 1
    delay = timeout + 0.5
    with Timer() as t:
        with pytest.raises(errors.Timeout) as exc:
            broker.execute("sleep", delay, timeout=timeout).result
    assert exc.value.args[0].endswith("/services/sleep")
    assert t.elapsed < delay
    assert t.elapsed > timeout


def test_default_timeout_in_call(broker):
    default_timeout = client.get_default_timeout()
    client.Result._default_timeout = 1
    delay = client.Result._default_timeout + 0.5

    try:
        with Timer() as t:
            with pytest.raises(errors.Timeout) as exc:
                broker.execute("sleep", delay).result
        assert exc.value.args[0].endswith("/services/sleep")
        assert t.elapsed < delay
        assert t.elapsed > client.Result._default_timeout
    finally:
        client.Result._default_timeout = default_timeout


def test_invalid_timeout_in_call(broker):
    with pytest.raises(ValueError) as exc:
        broker.execute("echo", timeout="pepe").result
    assert str(exc.value) == "Invalid timeout: pepe"


def test_timeout_in_wait(broker):
    timeout = 1
    delay = timeout + 0.5

    res = broker.execute("sleep", delay)

    # The first call to `wait()` times out.
    with Timer() as t:
        with pytest.raises(errors.Timeout) as exc:
            res.wait(timeout)
        assert exc.value.args[0].endswith("/services/sleep")
    assert t.elapsed < delay
    assert t.elapsed > timeout

    # Ensure enough time passes for the server side to complete its
    # call.
    time.sleep(delay)

    # The second one succeeds.
    res.wait(timeout)


def test_command_line_script(worker, monkeypatch, script_runner):
    monkeypatch.setenv(
        *env_var("SERVICELIB_CONFIG_URL", str(worker.servicelib_yaml_file.as_uri()))
    )
    r = script_runner.run("servicelib-client", "echo", '["foo",{"bar":42,"baz":true}]')
    assert r.success
    assert json.loads(r.stdout) == [["foo", {"bar": 42, "baz": True}]]

    r = script_runner.run("servicelib-client", "no-such-service")
    assert not r.success
