# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals


from servicelib import service


class Counter(service.ServiceInstance):

    name = "counter-1"

    def __init__(self):
        super(Counter, self).__init__()
        self.count = 0

    def execute(self, context, incr):
        self.count += incr
        return self.count


class AnotherCounter(service.ServiceInstance):
    def __init__(self, name):
        super(AnotherCounter, self).__init__(name)
        self.count = 0

    def execute(self, context, incr):
        self.count += incr
        return self.count


def main():
    service.start_services(Counter(), AnotherCounter("counter-2"))
