try:
    from distutils.version import StrictVersion as SV
except ImportError:  # Python 3.12+ removed distutils
    def SV(version):
        parts = version.split('.')
        if not 2 <= len(parts) <= 3 or not all(p.isdigit() for p in parts):
            raise ValueError("invalid version number '%s'" % version)
import unittest

import minecraft


class VersionTest(unittest.TestCase):
    def test_module_version_is_a_valid_pep_386_strict_version(self):
        SV(minecraft.__version__)

    def test_protocol_version_is_an_int(self):
        for version in minecraft.SUPPORTED_PROTOCOL_VERSIONS:
            self.assertTrue(type(version) is int)
