# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import json
import sys

from servicelib import client, logutils


def main():
    p = argparse.ArgumentParser()
    p.add_argument("service")
    p.add_argument("params", nargs="*")
    args = p.parse_args()

    logutils.configure_logging()

    params = [json.loads(param) for param in args.params]
    broker = client.Broker()
    try:
        res = broker.execute(args.service, *params).result
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1
    print(json.dumps(res))


if __name__ == "__main__":
    sys.exit(main())
