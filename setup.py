# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os

from setuptools import find_packages, setup


def read_requirements():
    ret = []
    fname = os.path.join(os.path.dirname(__file__), "requirements.txt")
    with open(fname, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ret.append(line)
    return ret


setup(
    name="servicelib",
    entry_points={"console_scripts": ["servicelib-worker=servicelib.cmd.worker:main"],},
    include_package_data=True,
    package_dir={"": "src",},
    packages=find_packages("src"),
    install_requires=read_requirements(),
    version="0.1.0",
    zip_safe=False,
)
