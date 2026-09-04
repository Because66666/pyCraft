import unittest

# Compatibility with Python 3.12+, which removed these deprecated aliases:
if not hasattr(unittest.TestCase, 'assertEquals'):
    unittest.TestCase.assertEquals = unittest.TestCase.assertEqual
if not hasattr(unittest.TestCase, 'assertRaisesRegexp'):
    unittest.TestCase.assertRaisesRegexp = unittest.TestCase.assertRaisesRegex
