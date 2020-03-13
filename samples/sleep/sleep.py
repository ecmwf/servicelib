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

from servicelib.process import Process


def sleep_spawn(context, n):
    class p(Process):
        def results(self):
            pass

    return context.spawn_process(p("sleep", ["sleep", int(n)]))


def sleep(context, n):
    n = int(n)
    time.sleep(n)
    return n


def main():
    from servicelib import service

    service.start_services(
        {"name": "sleep", "execute": sleep},
        {"name": "sleep-test", "execute": sleep_spawn},
    )
