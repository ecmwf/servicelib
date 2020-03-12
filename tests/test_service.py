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
import re

import pytest
import requests

from servicelib import errors
from servicelib.compat import Path


def test_invalid_endpoint(worker):
    with pytest.raises(Exception) as exc:
        worker.http_post("/no-such-endpoint", data=json.dumps([]))
    assert str(exc.value).startswith("404")


def test_call_unknown_service(worker):
    with pytest.raises(Exception) as exc:
        worker.http_post("/services/no-such-service", data=json.dumps([]))
    assert str(exc.value).startswith("404")


def test_call_service(worker):
    res = worker.http_post(
        "/services/hello",
        data=json.dumps(["world"]),
        headers={"content-type": "application/json"},
    )
    assert res == "Hello, world!"

    res = worker.http_post(
        "/services/bonjour",
        data=json.dumps(["world"]),
        headers={"content-type": "application/json"},
    )
    assert res == "Bonjour, world!"


def test_invalid_content_type(worker):
    with pytest.raises(Exception) as exc:
        worker.http_post(
            "/services/hello",
            data="world, valid text/plain, but not supported",
            headers={"content-type": "text/plain"},
        )
    assert str(exc.value).startswith("415")


@pytest.mark.parametrize(
    "req,expected",
    [
        (
            "This is not valid JSON",
            set(
                [
                    errors.BadRequest("No JSON object could be decoded"),
                    errors.BadRequest("Expecting value: line 1 column 1 (char 0)"),
                ]
            ),
        ),
        (
            json.dumps("Valid JSON, but list expected"),
            set([errors.BadRequest("List expected")]),
        ),
    ],
)
def test_malformed_request(worker, req, expected):
    with pytest.raises(errors.BadRequest) as exc:
        worker.http_post("/services/hello", data=req)
    assert exc.value in expected


def test_malformed_response(worker):
    with pytest.raises(errors.TaskError) as exc:
        worker.http_post("/services/malformed_response", data=json.dumps([]))
    exc = exc.value.exc_value
    assert isinstance(exc, TypeError)
    assert str(exc).startswith("Cannot encode")


def test_process_based_service(worker):
    res = worker.http_post("/services/df", data=json.dumps(["-h", "/"]))
    assert re.match(r"Filesystem\s+\Size\s+Used\s+Avail\s+", res)


def test_downloadable_result(worker):
    this_dir = str(Path(__file__, "..").resolve())
    res = worker.http_post("/services/tar-create", data=json.dumps([this_dir]))
    tar_file = requests.get(res["location"])
    assert len(tar_file.content) == res["contentLength"]


def test_downloadable_result_as_argument(worker):
    this_dir = str(Path(__file__, "..").resolve())
    tar_file = worker.http_post("/services/tar-create", data=json.dumps([this_dir]))

    res = worker.http_post("/services/tar-list", data=json.dumps([tar_file]))
    assert this_dir[1:] in res


def test_health_endpoint(worker):
    res = worker.http_get("/health")
    assert res.status_code == 200


def test_stats_endpoint(worker):
    res = worker.http_get("/stats")
    assert res.status_code == 200
    assert res.json()


def test_swagger_yaml_endpoint(worker):
    res = worker.http_get("/services/swagger.yaml")
    assert res.status_code == 200
    assert "A dummy OpenAPI definitions file" in res.content.decode("utf-8")


def test_swagger_ui_endpoint(worker):
    res = worker.http_get("/docs")
    assert res.status_code == 200
    assert "A placeholder for the real Swagger UI"
