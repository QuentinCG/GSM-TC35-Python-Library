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

  __default_serial_for_setup = [
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
  def getDefaultConfigForSetup():
    return MockSerial.__default_serial_for_setup + []

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
  def test_fail_cmd(self):
    logging.debug("test_fail_cmd")
    # Request failed because nothing requested
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((['--baudrate', '115200', '--serialPort', 'COM_Invalid', '--pin', '1234', '--puk', '12345678', '--pin2', '1234', '--puk2', '12345678', '--nodebug', '--debug']))
    self.assertNotEqual(cm.exception.code, 0)

    # Request failed because invalid argument
    with self.assertRaises(SystemExit) as cm:
      GSMTC35.main((['--undefinedargument']))
    self.assertNotEqual(cm.exception.code, 0)

  def test_all_cmd_help(self):
    logging.debug("test_all_cmd_help")
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
    logging.debug("test_fail_setup")
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
    self.assertFalse(gsm.setup(_port="COM_FAKE"))

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
    logging.debug("test_success_setup")
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    gsm = GSMTC35.GSMTC35()
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

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
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

  @patch('serial.Serial', new=MockSerial)
  def test_success_pin_during_setup(self):
    logging.debug("test_success_pin_during_setup")
    # Entered PIN/PUK/PIN2/PUK2
    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PUK2\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN=87654321\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PIN2\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN=4321\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PUK\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN=12345678\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PIN\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN=1234\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: READY\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertTrue(gsm.setup(_port="COM_FAKE", _pin="1234", _puk="12345678", _pin2="4321", _puk2="87654321"))

    # No PIN/PUK/PIN2/PUK2 specified in entry (bypassing)
    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PUK2\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PIN2\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PUK\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PIN\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

  @patch('serial.Serial', new=MockSerial)
  def test_fail_pin_during_setup(self):
    logging.debug("test_fail_pin_during_setup")
    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PUK2\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN=87654321\r\n'}, {'OUT': b'ERROR\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertFalse(gsm.setup(_port="COM_FAKE", _pin="1234", _puk="12345678", _pin2="4321", _puk2="87654321"))

    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PIN2\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN=4321\r\n'}, {'OUT': b'ERROR\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertFalse(gsm.setup(_port="COM_FAKE", _pin="1234", _puk="12345678", _pin2="4321", _puk2="87654321"))

    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PUK\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN=12345678\r\n'}, {'OUT': b'ERROR\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertFalse(gsm.setup(_port="COM_FAKE", _pin="1234", _puk="12345678", _pin2="4321", _puk2="87654321"))

    MockSerial.initializeMock([
      {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATE0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'ATV1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMEE=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN?\r\n'}, {'OUT': b'+CPIN: SIM PIN\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CPIN=1234\r\n'}, {'OUT': b'ERROR\r\n'},
      {'IN': b'AT+CLIP=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CNMI=0,0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT^SCTM=0\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+CMGF=1\r\n'}, {'OUT': b'OK\r\n'},
      {'IN': b'AT+IPR=115200\r\n'}, {'OUT': b'OK\r\n'}
    ])
    gsm = GSMTC35.GSMTC35()
    self.assertFalse(gsm.setup(_port="COM_FAKE", _pin="1234", _puk="12345678", _pin2="4321", _puk2="87654321"))

  @patch('serial.Serial', new=MockSerial)
  def test_all_change_baudrate(self):
    logging.debug("test_all_change_baudrate")
    gsm = GSMTC35.GSMTC35()

    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup() + [{'IN': b'AT+IPR=9600\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertTrue(gsm.changeBaudrateMode(115200, 9600, "COM_FAKE"))

    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup() + [{'IN': b'AT+IPR=9600\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertFalse(gsm.changeBaudrateMode(115200, 9600, "COM_FAKE"))

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
    self.assertFalse(gsm.changeBaudrateMode(115200, 9600, "COM_FAKE"))

  @patch('serial.Serial', new=MockSerial)
  def test_all_is_initialized(self):
    logging.debug("test_fail_pin_during_setup")
    gsm = GSMTC35.GSMTC35()

    MockSerial.initializeMock([])
    self.assertFalse(gsm.isInitialized())

    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([])
    self.assertTrue(gsm.isInitialized())

  @patch('serial.Serial', new=MockSerial)
  def test_all_close(self):
    logging.debug("test_all_close")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock([{'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(gsm.close(), None)
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))
    MockSerial.initializeMock([{'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(gsm.close(), None)

  @patch('serial.Serial', new=MockSerial)
  def test_all_reboot(self):
    logging.debug("test_all_reboot")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT+CFUN=1,1\r\n'}, {'OUT': b'OK\r\n'},
                               {'OUT': b'... Rebooting ...\r\n'}, {'OUT': b'^SYSSTART\r\n'},
                               {'IN': b'AT+IPR=0\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertTrue(gsm.reboot())

    MockSerial.initializeMock([{'IN': b'AT+CFUN=1,1\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertFalse(gsm.reboot())

  @patch('serial.Serial', new=MockSerial)
  def test_all_is_alive(self):
    logging.debug("test_all_is_alive")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertTrue(gsm.isAlive())

    MockSerial.initializeMock([{'IN': b'AT\r\n'}])
    self.assertFalse(gsm.isAlive())

  @patch('serial.Serial', new=MockSerial)
  def test_all_get_manufacturer_id(self):
    logging.debug("test_all_get_manufacturer_id")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT+CGMI\r\n'}, {'OUT': b'FAKE_MANUFACTURER\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(str(gsm.getManufacturerId()), "FAKE_MANUFACTURER")

    MockSerial.initializeMock([{'IN': b'AT+CGMI\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertEqual(str(gsm.getManufacturerId()), "")

  @patch('serial.Serial', new=MockSerial)
  def test_all_get_model_id(self):
    logging.debug("test_all_get_model_id")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT+CGMM\r\n'}, {'OUT': b'FAKE_MODEL\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(str(gsm.getModelId()), "FAKE_MODEL")

    MockSerial.initializeMock([{'IN': b'AT+CGMM\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertEqual(str(gsm.getModelId()), "")

  @patch('serial.Serial', new=MockSerial)
  def test_all_get_revision_id(self):
    logging.debug("test_all_get_revision_id")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT+CGMR\r\n'}, {'OUT': b'FAKE_REVISION\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(str(gsm.getRevisionId()), "FAKE_REVISION")

    MockSerial.initializeMock([{'IN': b'AT+CGMR\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertEqual(str(gsm.getRevisionId()), "")

  @patch('serial.Serial', new=MockSerial)
  def test_all_get_imei(self):
    logging.debug("test_all_get_imei")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT+CGSN\r\n'}, {'OUT': b'FAKE_IMEI\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(str(gsm.getIMEI()), "FAKE_IMEI")

    MockSerial.initializeMock([{'IN': b'AT+CGSN\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertEqual(str(gsm.getIMEI()), "")

  @patch('serial.Serial', new=MockSerial)
  def test_all_get_imsi(self):
    logging.debug("test_all_get_imsi")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT+CIMI\r\n'}, {'OUT': b'FAKE_IMSI\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(str(gsm.getIMSI()), "FAKE_IMSI")

    MockSerial.initializeMock([{'IN': b'AT+CIMI\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertEqual(str(gsm.getIMSI()), "")

  @patch('serial.Serial', new=MockSerial)
  def test_all_set_module_to_manufacturer_state(self):
    logging.debug("test_all_set_module_to_manufacturer_state")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT&F0\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertTrue(gsm.setModuleToManufacturerState())

    MockSerial.initializeMock([{'IN': b'AT&F0\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertFalse(gsm.setModuleToManufacturerState())
  @patch('serial.Serial', new=MockSerial)

  def test_all_switch_off(self):
    logging.debug("test_all_switch_off")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT^SMSO\r\n'}, {'OUT': b'MS OFF\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertTrue(gsm.switchOff())

    MockSerial.initializeMock([{'IN': b'AT^SMSO\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertFalse(gsm.switchOff())

  @patch('serial.Serial', new=MockSerial)
  def test_all_get_operator_name(self):
    logging.debug("test_all_get_operator_name")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT+COPS=3,0\r\n'}, {'OUT': b'OK\r\n'},
                               {'IN': b'AT+COPS?\r\n'}, {'OUT': b'+COPS: 0,1,\"FAKE_OPERATOR\"\r\n'},
                               {'OUT': b'OK\r\n'}])
    self.assertEqual(str(gsm.getOperatorName()), "FAKE_OPERATOR")

    MockSerial.initializeMock([{'IN': b'AT+COPS=3,0\r\n'}, {'OUT': b'OK\r\n'},
                               {'IN': b'AT+COPS?\r\n'}, {'OUT': b'+COPS: \"FAKE_OPERATOR\"\r\n'}])
    self.assertEqual(str(gsm.getOperatorName()), "")

    MockSerial.initializeMock([{'IN': b'AT+COPS=3,0\r\n'}, {'OUT': b'OK\r\n'},
                               {'IN': b'AT+COPS?\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertEqual(str(gsm.getOperatorName()), "")

    MockSerial.initializeMock([{'IN': b'AT+COPS=3,0\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertEqual(str(gsm.getOperatorName()), "")

  @patch('serial.Serial', new=MockSerial)
  def test_all_get_signal_strength(self):
    logging.debug("test_all_get_signal_strength")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT+CSQ\r\n'}, {'OUT': b'+CSQ: 60,USELESS\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(gsm.getSignalStrength(), 7)

    MockSerial.initializeMock([{'IN': b'AT+CSQ\r\n'}, {'OUT': b'+CSQ: 100,USELESS\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(gsm.getSignalStrength(), -1)

    MockSerial.initializeMock([{'IN': b'AT+CSQ\r\n'}, {'OUT': b'+CSQ: -1,USELESS\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(gsm.getSignalStrength(), -1)

    MockSerial.initializeMock([{'IN': b'AT+CSQ\r\n'}, {'OUT': b'+CSQ: WRONG,USELESS\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(gsm.getSignalStrength(), -1)

    MockSerial.initializeMock([{'IN': b'AT+CSQ\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertEqual(gsm.getSignalStrength(), -1)

  @patch('serial.Serial', new=MockSerial)
  def test_all_get_operator_names(self):
    logging.debug("test_all_get_operator_names")
    gsm = GSMTC35.GSMTC35()
    MockSerial.initializeMock(MockSerial.getDefaultConfigForSetup())
    self.assertTrue(gsm.setup(_port="COM_FAKE"))

    MockSerial.initializeMock([{'IN': b'AT+COPN\r\n'}, {'OUT': b'+COPN: 1,\"FAKE1\"\r\n'},
                               {'OUT': b'+COPN: 2,\"FAKE 2\"\r\n'}, {'OUT': b'+COPN: 3,\"Fake Three\"\r\n'},
                               {'OUT': b'+COPN: DUMMY_ERROR\r\n'},{'OUT': b'DUMMY_ERROR\r\n'}, {'OUT': b'OK\r\n'}])
    self.assertEqual(gsm.getOperatorNames(), ["FAKE1", "FAKE 2", "Fake Three"])

    MockSerial.initializeMock([{'IN': b'AT+COPN\r\n'}, {'OUT': b'ERROR\r\n'}])
    self.assertEqual(gsm.getOperatorNames(), [])

if __name__ == '__main__':
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)
  unittest.main()
