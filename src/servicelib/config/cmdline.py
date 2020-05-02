# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import argparse


__all__ = [
    "parse_args",
]


def key_to_arg_flag(k):
    return "--{}".format(k.replace(".", "-").replace("_", "-"))


def key_to_arg(k):
    return k.replace(".", "_")


SUPPORTED_ENTRIES = {
    "worker.autoreload": {
        "type": int,
        "metavar": "N",
        "help": "check for changes every N seconds",
    },
    "worker.hostname": {
        "type": str,
        "metavar": "HOST",
        "help": "hostname to advertise for HTTP connections",
    },
    "worker.load_workers": {
        "type": str,
        "metavar": "NAME[,NAME,..]",
        "help": "comma-separated list of workers to load",
    },
    "worker.num_processes": {
        "type": int,
        "metavar": "N",
        "help": "number of worker processes to spawn",
    },
    "worker.num_threads": {
        "type": int,
        "metavar": "N",
        "help": "number of worker threads per process to spawn",
    },
    "worker.port": {
        "type": int,
        "metavar": "N",
        "help": "listening port for HTTP connections",
    },
    "worker.services_dir": {
        "type": str,
        "metavar": "PATH",
        "help": "path to service implementations",
    },
}


def parse_args(*enabled_entries):
    p = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    for e in enabled_entries:
        params = SUPPORTED_ENTRIES[e]
        p.add_argument(key_to_arg_flag(e), **params)

    args = p.parse_args()

    ret = {}
    for e in enabled_entries:
        try:
            ret[e] = getattr(args, key_to_arg(e))
        except AttributeError:
            pass
    return ret
