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
import signal
import subprocess
import sys
import threading
import time

import pytest

from servicelib import process
from servicelib.compat import open


def test_spawn_process(context):
    cmdline = ["echo", "foo"]

    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("echo", cmdline)

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


def test_spawn_process_with_truncated_output(context, tmp_path):
    zeroes = tmp_path / "zeroes"
    cmdline = ["cat", str(zeroes)]

    class p(process.Process):

        max_output_size = 42

        def __init__(self):
            super(p, self).__init__("cat-zeroes", cmdline)

        def results(self):
            return self.output.decode("utf-8")

    with open(zeroes, "wb") as f:
        f.write(("0" * p.max_output_size).encode("utf-8"))
        f.write("and some extra data which will be truncated".encode("utf-8"))

    res = context.spawn_process(p())
    assert res == "0" * p.max_output_size


def test_spawn_process_with_truncated_output_2(context, tmp_path):
    foo_bar = tmp_path / "foo-bar"
    cmdline = ["cat", str(foo_bar)]

    # The newline in the output will trigger two calls to the process object's
    # `stdout_data`, the first one of which fill fill the output capacity.
    with open(foo_bar, "wb") as f:
        f.write("foo\nbar".encode("utf-8"))

    class p(process.Process):

        max_output_size = 3

        def __init__(self):
            super(p, self).__init__("cat-foo-bar", cmdline)

        def results(self):
            return self.output.decode("utf-8")

    res = context.spawn_process(p())
    assert res == "foo"


def test_spawn_process_with_unlimited_output(context, tmp_path):
    zeroes = tmp_path / "zeroes"
    cmdline = ["cat", str(zeroes)]

    class p(process.Process):

        max_output_size = 0

        def __init__(self):
            super(p, self).__init__("cat-zeores", cmdline)

        def results(self):
            return self.output.decode("utf-8")

    with open(zeroes, "wb") as f:
        f.write(("0" * process.DEFAULT_MAX_PROCESS_OUTPUT_SIZE).encode("utf-8"))

    res = context.spawn_process(p())
    assert res == "0" * zeroes.stat().st_size


SLEEP_PY = """
import os
import sys
import time

with open(sys.argv[1], "wt") as f:
    f.write(str(os.getpid()))

time.sleep(10)
"""


def test_handle_signals_in_spawn_process(context, tmp_path):
    script = tmp_path / "script.py"
    with open(script, "wt") as f:
        f.write(SLEEP_PY)

    pid_file = tmp_path / "script.pid"
    cmdline = [sys.executable, str(script), str(pid_file)]

    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("sleep", cmdline)

        def results(self):
            return self.output.decode("utf-8")

    result = []

    def spawn():
        try:
            res = context.spawn_process(p())
            result.append(res)
        except Exception as exc:
            result.append(exc)

    t = threading.Thread(target=spawn)
    t.start()

    time.sleep(1)

    with open(pid_file, "rt") as f:
        pid = int(f.read().strip())

    os.kill(pid, signal.SIGTERM)
    t.join()

    assert isinstance(result[0], Exception)
    assert str(result[0]).startswith("'sleep' killed by signal")


def test_handle_errors_in_error_handler_of_spawn_process(context, tmp_path):
    cmdline = ["ls", "/no-such-file"]

    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("ls-foo", cmdline)

        def results(self):
            return self.output.decode("utf-8")

        def failed(self, rc, signal):
            raise Exception("Oops")

    with pytest.raises(Exception) as exc:
        context.spawn_process(p())
    assert str(exc.value).startswith("'ls-foo' failed, return code 2")


def test_handle_cleanup_errors_in_spawn_process(context):
    cmdline = ["echo", "foo"]

    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("echo", cmdline)

        def results(self):
            return self.output.decode("utf-8")

        def cleanup(self):
            raise Exception("Oops")

    res = context.spawn_process(p())
    assert res == subprocess.check_output(cmdline).decode("utf-8")


STDERR_PY = r"""
import sys

sys.stdout.write("foo\n")
sys.stdout.flush()
sys.stderr.write("bar\n")
sys.stderr.flush()
sys.stdout.write("baz\n")
sys.stdout.flush()
"""


def test_interleaved_output_in_spawn_process(context, tmp_path):
    script = tmp_path / "script.py"
    with open(script, "wt") as f:
        f.write(STDERR_PY)

    pid_file = tmp_path / "script.pid"
    cmdline = [sys.executable, str(script), str(pid_file)]

    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("stderr", cmdline)

        def results(self):
            return self.output.decode("utf-8")

    res = context.spawn_process(p())
    assert res == "foo\nbar\nbaz\n"
