#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  Automatic test of GSMTC35 library (not complete and without MOCK => not perfect at all)
  Feel free to create mock test for better unit-test.
"""

import unittest
from GSMTC35 import GSMTC35

class AutomaticTestGSMTC35(unittest.TestCase):
  def test_fail_setup(self):
    gsm = GSMTC35.GSMTC35()
    self.assertFalse(gsm.setup(_port="COM_Invalid", _pin="1234", _puk="12345678", _pin2="4321", _puk2="87654321"))

if __name__ == '__main__':
  unittest.main()
