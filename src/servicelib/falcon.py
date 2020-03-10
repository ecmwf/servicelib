# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Falcon support for servicelib."""

from __future__ import absolute_import, unicode_literals

import json

import falcon
import psutil

from servicelib import config, errors, logutils
from servicelib.core import Request


__all__ = [
    "HealthResource",
    "StatsResource",
    "WorkerResource",
]


class HealthResource(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200


class StatsResource(object):
    def on_get(self, req, resp):
        proc = psutil.Process()
        with proc.oneshot():
            parent = proc.parent()
            nofile_soft = proc.rlimit(psutil.RLIMIT_NOFILE)

        with parent.oneshot():
            # Assume all processes with our parent as ancestor are
            # part of this worker instance.
            proc_set = [
                p.as_dict(
                    attrs=[
                        "cmdline",
                        "connections",
                        "cpu_percent",
                        "cpu_times",
                        "memory_info",
                        "num_fds",
                        "pid",
                        "ppid",
                    ]
                )
                for p in parent.children(recursive=True)
            ]

        stats = {
            "config": {
                "num_processes": int(config.get("worker_num_processes")),
                "num_threads": int(config.get("worker_num_threads")),
                "max_num_fds": nofile_soft,
            },
            "totals": {"cpu_percent": 0.0, "mem": {"rss": 0, "vms": 0,},},
            "procs": proc_set,
        }

        for p in proc_set:
            stats["totals"]["cpu_percent"] += p["cpu_percent"]
            stats["totals"]["mem"]["rss"] += p["memory_info"][0]
            stats["totals"]["mem"]["vms"] += p["memory_info"][1]

        resp.status = falcon.HTTP_200
        resp.data = json.dumps(stats).encode("utf-8")


class WorkerResource(object):

    log = logutils.get_logger(__name__)

    def __init__(self, service_instances):
        self.service_instances = service_instances

    def on_post(self, req, resp, service):
        try:
            svc = self.service_instances[service]
        except KeyError:
            self.log.error("Unknown service '%s'", service)
            raise falcon.HTTPNotFound()

        if req.content_type and "application/json" not in req.content_type:
            self.log.error("Unsupported request content type '%s'", req.content_type)
            raise falcon.HTTPUnsupportedMediaType()

        try:
            body = req.bounded_stream.read()
            headers = req.headers
            svc_req = Request.from_http(body, headers)
        except Exception as exc:
            self.log.error(
                "Bad request (body: %s, headers: %s): %s", body, headers, exc
            )
            exc = errors.BadRequest(str(exc))
            resp.status = exc.http_response_code
            resp.data = json.dumps(exc.as_dict()).encode("utf-8")
            self.log.debug("Response body: %s", resp.data)
        else:
            svc_resp = svc._execute(svc_req)
            resp.status = svc_resp.http_status
            resp.data = svc_resp.http_body
            for k, v in svc_resp.http_headers.items():
                resp.append_header(k, v)
