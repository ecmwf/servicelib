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
import shutil
import signal
import subprocess
import tempfile

import pytest
import requests

from servicelib import client, errors, logutils, utils
from servicelib.compat import Path, open, env_var


__all__ = [
    "broker",
    "servicelib_ini",
    "worker",
]


logutils.configure_logging()


@pytest.fixture
def broker(request, worker, monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_REGISTRY_CLASS", "redis"))
    monkeypatch.setenv(*env_var("SERVICELIB_REGISTRY_URL", "redis://localhost/0"))
    b = client.Broker()
    b.worker_info = {
        "num_processes": worker.num_processes,
        "num_threads": worker.num_threads,
    }
    try:
        yield b
    finally:
        b.http_session.close()


@pytest.fixture
def servicelib_ini(request, monkeypatch):
    monkeypatch.setenv(
        *env_var(
            "SERVICELIB_CONFIG_FILE",
            str(Path(__file__, "..", "sample-servicelib.ini").resolve()),
        )
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
processes = {num_processes}
safe-pidfile = {pid_file}
threads = {num_threads}
"""

SERVICELIB_INI_TEMPLATE = """
[worker]
hostname = {host}
port = {port}
serve_results = {scratch_dir}
services_dir = {services_dir}
static_map = /services-source-code={services_dir}
swagger_ui_path = {services_dir}/swagger-ui
uwsgi_config_file = {uwsgi_config_file}

[inventory]
class = default

[registry]
class = redis
url = redis://localhost/0

[cache]
class = memcached
memcached_addresses = localhost:11211

[log]
level = debug
type = text

[results]
class = http-files
dirs = {scratch_dir}
http_hostname = {host}


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

        # Some tests in `tests/test_client.py` call service `proxy`, which
        # calls other services. We need several uWSGI processes to be ready
        # to accept requests.
        self.num_processes = 4

        # Set to 1 because we're assuming `servicelib` (and the services built
        # upon it) are not thread-safe.
        #
        # We do want to set it explicitly to 1, so that Python's threading
        # machinery gets initialised.
        self.num_threads = 1

        servicelib_dir = Path(__file__, "..", "..").resolve()
        services_dir = servicelib_dir / "samples"

        self.uwsgi_ini = UWSGI_INI_TEMPLATE.format(
            host=self.host,
            log_file=log_file,
            num_processes=self.num_processes,
            num_threads=self.num_threads,
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
        utils.wait_for_url("http://{}:{}/health".format(self.host, self.port))
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
