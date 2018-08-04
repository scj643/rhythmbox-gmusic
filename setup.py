import sys

from setuptools import find_packages
from setuptools import setup

version = "4.0"

setup(
    name="rhythmbox-gmusic",
    version=version,
    description="Rhythmbox Google Play Music Plugin",
    author="Joel Goguen",
    author_email="jgoguen@users.noreply.github.com",
    url="https://github.com/jgoguen/rhythmbox-gmusic/",
    license="BSD",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=["gmusicapi", "futures"],
    data_files=[
        (
            f"{sys.prefix}/share/rhythmbox/plugins/googleplaymusic",
            ["googleplaymusic.plugin"],
        ),
        (
            f"{sys.prefix}/share/locale/ru/LC_MESSAGES/",
            ["po/ru/rhythmbox-gmusic.po"],
        ),
    ],
)
