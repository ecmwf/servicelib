# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

from servicelib import process


def execute(context, *args):
    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("df", ["df"] + list(args))

        def results(self):
            return self.output.decode("utf-8")

    return context.spawn_process(p())


def main():
    from servicelib import service

    service.start_service()
