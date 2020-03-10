# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals


def hola(context, name):
    return "Homa, {}!".format(name)


def bonjour(context, name):
    return "Bonjour, {}!".format(name)


def main():
    from servicelib import service

    service.start_services(
        {"name": "hola", "execute": hola}, {"name": "bonjour", "execute": bonjour},
    )
