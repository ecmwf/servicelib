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
