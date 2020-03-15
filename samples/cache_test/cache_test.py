# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import time

from servicelib.cache import cache_control


def mock_preload(context, request):
    delay = request.get("delay")
    if delay:
        time.sleep(delay)

    return {"preload": request}


@cache_control(time=1)
def mock_retrieve(context, request):
    ret = []

    for data in (b"field-1", b"field-2", b"field-3"):
        res = context.create_result("application/x-grib")
        with res:
            res.write(data)
        ret.append({"request": "whatever", "result": res})

    return ret


def main():
    from servicelib import service

    service.start_services(
        {"name": "mock_preload", "execute": cache_control(time=1)(mock_preload)},
        {
            "name": "mock_preload_long_ttl",
            "execute": cache_control(time=86400)(mock_preload),
        },
        {"name": "mock_retrieve", "execute": mock_retrieve},
    )
