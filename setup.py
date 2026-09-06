from setuptools import setup
from minecraft import __version__


def read(filename):
    """
    Puts a file into a string.
    """
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()


# Original pyCraft authors (project is a fork of
# https://github.com/ammaraskar/pyCraft, Apache License 2.0).

URL = "https://github.com/Because66666/pyCraft"

setup(name="pycraft-minecraft",
      version=__version__,
      description="Python MineCraft library",
      long_description=read("README.md"),
      long_description_content_type="text/markdown",
      url=URL,
      download_url=URL + "/tarball/" + __version__,
      author="Because66666",
      install_requires=["cryptography>=1.5",
                        "requests",
                        "pynbt",
                        ],
      packages=["minecraft",
                "minecraft.microsoft",
                "minecraft.networking",
                "minecraft.networking.packets",
                "minecraft.networking.packets.clientbound",
                "minecraft.networking.packets.clientbound.status",
                "minecraft.networking.packets.clientbound.handshake",
                "minecraft.networking.packets.clientbound.login",
                "minecraft.networking.packets.clientbound.play",
                "minecraft.networking.packets.clientbound.configuration",
                "minecraft.networking.packets.serverbound",
                "minecraft.networking.packets.serverbound.status",
                "minecraft.networking.packets.serverbound.handshake",
                "minecraft.networking.packets.serverbound.login",
                "minecraft.networking.packets.serverbound.play",
                "minecraft.networking.packets.serverbound.configuration",
                "minecraft.networking.types",
                ],
      keywords=["MineCraft", "networking", "pyCraft", "minecraftdev", "mc"],
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: Apache Software License",
                   "Natural Language :: English",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 2",
                   "Programming Language :: Python :: 2.7",
                   "Programming Language :: Python :: 3",
                   "Programming Language :: Python :: 3.3",
                   "Programming Language :: Python :: 3.4",
                   "Programming Language :: Python :: 3.5",
                   "Programming Language :: Python :: 3.6",
                   "Topic :: Games/Entertainment",
                   "Topic :: Software Development :: Libraries",
                   "Topic :: Utilities"
                   ]
      )
