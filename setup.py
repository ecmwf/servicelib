# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from setuptools import find_packages, setup


setup(
    name="servicelib",
    entry_points={"console_scripts": ["servicelib-worker=servicelib.cmd.worker:main"],},
    extras_require={
        "docs": ["sphinx"],
        "tests": ["pyflakes", "pytest", "pytest-lazy-fixture",],
    },
    include_package_data=True,
    install_requires=[
        "falcon",
        "psutil",
        "python-json-logger",
        "redis",
        "requests",
        "six",
        "structlog",
        "uwsgi",
    ],
    package_dir={"": "src",},
    packages=find_packages("src"),
    version="0.1.0",
    zip_safe=False,
)
