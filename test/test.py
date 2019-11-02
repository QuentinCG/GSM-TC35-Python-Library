#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  Automatic test of GSMTC35 library (not complete and without MOCK => not perfect at all)
  Feel free to create mock test for better unit-test.
"""

import unittest
from GSMTC35 import GSMTC35
from unittest.mock import patch
import logging

class MockSerial:
  """
  TODO: Explanation of the class + functions
  """
  __is_open = True
  __read_write = []

  default_read_write_for_setup = [
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: READY\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ]

  @staticmethod
  def initializeMock(read_write, is_open = True):
    MockSerial.__is_open = is_open
    MockSerial.__read_write = read_write

  def __init__(self, port="", baudrate="", parity="", stopbits="", bytesize="", timeout=""):
    return

  def inWaiting(self):
    if MockSerial.__is_open and len(MockSerial.__read_write) > 0:
      if 'OUT' in MockSerial.__read_write[0]:
        return len(MockSerial.__read_write[0]['OUT'])
    return 0

  def read(self, dummy):
    if MockSerial.__is_open and len(MockSerial.__read_write) > 0:
      if 'OUT' in MockSerial.__read_write[0]:
        val = MockSerial.__read_write[0]['OUT']
        MockSerial.__read_write.pop(0)
        return val
    return ""

  def write(self, data):
    if MockSerial.__is_open and len(MockSerial.__read_write) > 0:
      if 'IN' in MockSerial.__read_write[0]:
        check_val = MockSerial.__read_write[0]['IN']
        if str(data) != str(check_val):
          raise AssertionError('Mock Serial: Should write "' + str(check_val) + '" but "'+str(data)+'" requested')
        MockSerial.__read_write.pop(0)
        return len(data)
    return 0

  def isOpen(self):
    return MockSerial.__is_open

  def close(self):
    return True

class TestGSMTC35(unittest.TestCase):
  """
  TODO: Explanation of the class + functions
  """
  def test_cmd_fail(self):
    # Request failed because nothing requested
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((['--baudrate', '115200', '--serialPort', 'COM_Invalid', '--pin', '1234', '--puk', '12345678', '--pin2', '1234', '--puk2', '12345678', '--nodebug', '--debug']))
    self.assertNotEqual(cm.exception.code, 0)

    # Request failed because invalid argument
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((['--undefinedargument']))
    self.assertNotEqual(cm.exception.code, 0)

  def test_cmd_help(self):
    # No paramaters
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main()
    self.assertNotEqual(cm.exception.code, 0)

    # Request basic help
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help"]))
    self.assertEqual(cm.exception.code, 0)

    # Request extended help
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "help"]))
    self.assertEqual(cm.exception.code, 0)

    # Request extended help
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "baudrate"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "serialport"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "pin"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "puk"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "pin2"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "puk2"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "isalive"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "call"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "hangupcall"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "issomeonecalling"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "pickupcall"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "sendsms"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "sendencodedsms"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "sendtextmodesms"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "getsms"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "getencodedsms"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "gettextmodesms"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "deletesms"]))
    self.assertEqual(cm.exception.code, 0)
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((["--help", "information"]))
    self.assertEqual(cm.exception.code, 0)

  @patch('serial.Serial', new=MockSerial)
  def test_fail_setup(self):
    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'ERROR\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertFalse(gsm.setup(_port="COM_FAKE", _pin="1234", _puk="12345678"))

    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'ERROR\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertFalse(gsm.setup(_port="COM_FAKE", _pin="1234", _puk="12345678"))

    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: READY\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'ERROR\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertFalse(gsm.setup(_port="COM_FAKE", _pin="1234", _puk="12345678"))

  @patch('serial.Serial', new=MockSerial)
  def test_success_setup(self):
    MockSerial.initializeMock(MockSerial.default_read_write_for_setup)

    gsm = GSMTC35.GSMTC35()
    self.assertTrue(gsm.setup(_port="COM_FAKE", _pin="1234", _puk="12345678"))

    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'ERROR\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'ERROR\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: READY\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'ERROR\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertTrue(gsm.setup(_port="COM_FAKE", _pin="1234", _puk="12345678"))

if __name__ == '__main__':
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)
  unittest.main()
