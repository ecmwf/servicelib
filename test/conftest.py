# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import

import os
import shutil
import signal
import subprocess
import tempfile

import pytest
import requests

from servicelib import errors, logutils, utils
from servicelib.compat import Path, open


__all__ = [
    "servicelib_ini",
    "worker",
]


logutils.configure_logging()


@pytest.fixture
def servicelib_ini(request, monkeypatch):
    monkeypatch.setenv(
        "SERVICELIB_CONFIG_FILE",
        os.path.join(os.path.dirname(__file__), "sample-servicelib.ini"),
    )


UWSGI_INI_TEMPLATE = """
[uwsgi]
chdir = {services_dir}
daemonize = {log_file}
die-on-term = true
enable-threads = true
http-socket = {host}:{port}
manage-script-name = true
master = true
module = servicelib.wsgi
need-app = true
processes = 2
safe-pidfile = {pid_file}
threads = 1
"""

SERVICELIB_INI_TEMPLATE = """
[worker]
serve_results = {scratch_dir}
services_dir = {services_dir}
uwsgi_config_file = {uwsgi_config_file}

[inventory]
class = default

[log]
level = debug
type = text

[results]
class = http-files
dirs = {scratch_dir}
http_hostname = {host}
http_port = {port}

[scratch]
strategy = random
dirs = {scratch_dir}

"""


class Worker(object):

    log = logutils.get_logger()

    def __init__(
        self, uwsgi_ini_file, servicelib_ini_file, pid_file, log_file, scratch_dir
    ):
        self.servicelib_ini_file = servicelib_ini_file
        self.pid_file = pid_file
        self.log_file = log_file
        self.host = "127.0.0.1"
        self.port = utils.available_port()

        servicelib_dir = Path(__file__, "..", "..").resolve()
        services_dir = servicelib_dir / "samples"

        self.uwsgi_ini = UWSGI_INI_TEMPLATE.format(
            host=self.host,
            log_file=log_file,
            pid_file=pid_file,
            port=self.port,
            services_dir=services_dir,
        )
        with open(uwsgi_ini_file, "wt") as f:
            f.write(self.uwsgi_ini)

        self.servicelib_ini = SERVICELIB_INI_TEMPLATE.format(
            host=self.host,
            port=self.port,
            scratch_dir=scratch_dir,
            services_dir=services_dir,
            uwsgi_config_file=uwsgi_ini_file,
        )
        with open(servicelib_ini_file, "wt") as f:
            f.write(self.servicelib_ini)

        scratch_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        env = dict(os.environ)
        env["SERVICELIB_CONFIG_FILE"] = str(self.servicelib_ini_file)
        subprocess.Popen("servicelib-worker", shell=True, env=env).wait()
        utils.wait_for_port_open(self.port, self.host)
        return self

    def __exit__(self, *exc_info):
        # self.log.debug("uwsgi.ini:\n%s", self.uwsgi_ini)
        # self.log.debug("servicelib.ini:\n%s", self.servicelib_ini)
        try:
            with open(self.log_file, "rt") as f:
                self.log.debug("uwsgi.log:\n%s", f.read())
        except Exception:
            pass

        with open(self.pid_file, "rt") as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)

    def http_post(self, path, **kwargs):
        res = requests.post(
            "http://{}:{}{}".format(self.host, self.port, path), **kwargs
        )
        if res.status_code == 200:
            return res.json()
        try:
            err = res.json()
        except Exception:
            raise Exception("{}\n\n{}".format(res.status_code, res.content))
        try:
            err = errors.Serializable.from_dict(err)
        except Exception:
            raise Exception("{}\n\n{}".format(res.status_code, res.content))
        else:
            raise err

    def http_get(self, path, **kwargs):
        return requests.get(
            "http://{}:{}{}".format(self.host, self.port, path), **kwargs
        )


@pytest.fixture(scope="session")
def worker():
    tmp_path = Path(tempfile.mkdtemp())
    try:
        with Worker(
            tmp_path / "uwsgi.ini",
            tmp_path / "servicelib.ini",
            tmp_path / "uwsgi.pid",
            tmp_path / "uwsgi.log",
            tmp_path / "scratch",
        ) as s:
            yield s
    finally:
        shutil.rmtree(str(tmp_path), ignore_errors=True)
