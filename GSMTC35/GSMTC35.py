#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  GSM TC35 library: Call, receive call, send/receive/delete SMS, enter the PIN, ...

  It is also possible to use command line to easily use this class from
  shell (launch this python file with '-h' parameter to get more information).

  Non-exhaustive class functionality list:
    - Check PIN state
    - Enter/Lock/Unlock/Change PIN
    - Send/Get/Delete SMS
    - Call/Re-call
    - Hang up/Pick-up call
    - Get/Add/Delete phonebook entries (phone numbers + contact names)
    - Sleep (Low power consumption)
    - Check if someone is calling
    - Check if there is a call in progress
    - Get last call duration
    - Check if module is alive
    - Get IDs (manufacturer, model, revision, IMEI, IMSI)
    - Set module to manufacturer state
    - Switch off
    - Reboot
    - Check sleep mode status
    - Get the current used operator
    - Get the signal strength (in dBm)
    - Set and get the date from the module internal clock
    - Get list of operators
    - Get list of neighbour cells
    - Get accumulated call meter and accumulated call meter max (in home units)
    - Get temperature status
    - Change the baudrate mode of the GSM module
"""
__author__ = 'Quentin Comte-Gaz'
__email__ = "quentin@comte-gaz.com"
__license__ = "MIT License"
__copyright__ = "Copyright Quentin Comte-Gaz (2019)"
__python_version__ = "3.+"
__version__ = "1.4 (2019/09/23)"
__status__ = "Usable for any project"

import binascii
import serial, serial.tools.list_ports
import time, sys, getopt
import logging
import datetime
from math import ceil
from random import randint

class GSMTC35:
  """GSM TC35 class

  Calling setup() function is necessary in order to make this class work properly
  If you don't know the serial port to use, call this script to show all of them:
  '''
  import serial, serial.tools.list_ports
  print(str(list(serial.tools.list_ports.comports())))
  '''
  """
  ######################### Enums and static variables #########################
  __BASE_AT = "AT"
  __NORMAL_AT = "AT+"
  __RETURN_OK = "OK"
  __RETURN_ERROR = "ERROR"
  __CTRL_Z = "\x1a"
  __DATE_FORMAT = "%y/%m/%d,%H:%M:%S"

  class eRequiredPin:
    READY = "READY"
    PIN   = "SIM PIN"
    PUK   = "SIM PUK"
    PIN2  = "SIM PIN2"
    PUK2  = "SIM PUK2"

  class eSMS:
    UNREAD_SMS = "REC UNREAD"
    READ_SMS = "REC READ"
    UNSENT_SMS = "STO UNSENT"
    SENT_SMS = "STO SENT"
    ALL_SMS = "ALL"

  class __eSmsPdu:
    UNREAD_SMS = "0"
    READ_SMS = "1"
    UNSENT_SMS = "2"
    SENT_SMS = "3"
    ALL_SMS = "4"

  @staticmethod
  def __smsTypeTextToPdu(smsTypeAsText):
    if smsTypeAsText == GSMTC35.eSMS.UNREAD_SMS:
      return GSMTC35.__eSmsPdu.UNREAD_SMS
    elif smsTypeAsText == GSMTC35.eSMS.READ_SMS:
      return GSMTC35.__eSmsPdu.READ_SMS
    elif smsTypeAsText == GSMTC35.eSMS.UNSENT_SMS:
      return GSMTC35.__eSmsPdu.UNSENT_SMS
    elif smsTypeAsText == GSMTC35.eSMS.SENT_SMS:
      return GSMTC35.__eSmsPdu.SENT_SMS
    elif smsTypeAsText == GSMTC35.eSMS.ALL_SMS:
      return GSMTC35.__eSmsPdu.ALL_SMS
    elif smsTypeAsText == GSMTC35.__eSmsPdu.UNREAD_SMS or \
         smsTypeAsText == GSMTC35.__eSmsPdu.READ_SMS or \
         smsTypeAsText == GSMTC35.__eSmsPdu.UNSENT_SMS or \
         smsTypeAsText == GSMTC35.__eSmsPdu.SENT_SMS or \
         smsTypeAsText == GSMTC35.__eSmsPdu.ALL_SMS:
      return smsTypeAsText
    else:
      # If an error occured, get all messages
      return GSMTC35.__eSmsPdu.ALL_SMS

  @staticmethod
  def __smsTypePduToText(smsTypeAsPdu):
    if smsTypeAsPdu == GSMTC35.__eSmsPdu.UNREAD_SMS:
      return GSMTC35.eSMS.UNREAD_SMS
    elif smsTypeAsPdu == GSMTC35.__eSmsPdu.READ_SMS:
      return GSMTC35.eSMS.READ_SMS
    elif smsTypeAsPdu == GSMTC35.__eSmsPdu.UNSENT_SMS:
      return GSMTC35.eSMS.UNSENT_SMS
    elif smsTypeAsPdu == GSMTC35.__eSmsPdu.SENT_SMS:
      return GSMTC35.eSMS.SENT_SMS
    elif smsTypeAsPdu == GSMTC35.__eSmsPdu.ALL_SMS:
      return GSMTC35.eSMS.ALL_SMS
    elif smsTypeAsPdu == GSMTC35.eSMS.UNREAD_SMS or \
         smsTypeAsPdu == GSMTC35.eSMS.READ_SMS or \
         smsTypeAsPdu == GSMTC35.eSMS.UNSENT_SMS or \
         smsTypeAsPdu == GSMTC35.eSMS.SENT_SMS or \
         smsTypeAsPdu == GSMTC35.eSMS.ALL_SMS:
      return smsTypeAsPdu
    else:
      # If an error occured, get all messages
      return GSMTC35.eSMS.ALL_SMS

  class eCall:
    NOCALL = -1
    ACTIVE = 0
    HELD = 1
    DIALING = 2
    ALERTING = 3
    INCOMING = 4
    WAITING = 5

  @staticmethod
  def eCallToString(data):
    if data == GSMTC35.eCall.NOCALL:
      return "NOCALL"
    elif data == GSMTC35.eCall.ACTIVE:
      return "ACTIVE"
    elif data == GSMTC35.eCall.HELD:
      return "HELD"
    elif data == GSMTC35.eCall.DIALING:
      return "DIALING"
    elif data == GSMTC35.eCall.ALERTING:
      return "ALERTING"
    elif data == GSMTC35.eCall.INCOMING:
      return "INCOMING"
    elif data == GSMTC35.eCall.WAITING:
      return "WAITING"

    return "UNDEFINED"

  class ePhonebookType:
    CURRENT = "" # Phonebook in use
    SIM = "SM" # Main phonebook on SIM card
    GSM_MODULE = "ME" # Main phonebook on GSM module
    LAST_DIALLING = "LD" # Last dialed numbers (stored in SIM card)
    MISSED_CALLS = "MC" # Last missed calls (stored in GSM module)
    RECEIVED_CALLS = "RC" # Last received calls (stored in GSM module)
    MSISDNS = "ON" # Mobile Station ISDN Numbers (stored in GSM module or SIM card)

  class __ePhoneNumberType:
    ERROR = -1
    LOCAL = 129
    INTERNATIONAL = 145

  class eForwardClass:
    VOICE = 1
    DATA = 2
    FAX = 4
    SMS = 8
    DATA_CIRCUIT_SYNC = 16
    DATA_CIRCUIT_ASYNC = 32
    DEDICATED_PACKED_ACCESS = 64
    DEDICATED_PAD_ACCESS = 128

  @staticmethod
  def eForwardClassToString(data):
    data = int(data)
    if data == GSMTC35.eForwardClass.VOICE:
      return "VOICE"
    elif data == GSMTC35.eForwardClass.DATA:
      return "DATA"
    elif data == GSMTC35.eForwardClass.FAX:
      return "FAX"
    elif data == GSMTC35.eForwardClass.SMS:
      return "SMS"
    elif data == GSMTC35.eForwardClass.DATA_CIRCUIT_SYNC:
      return "DATA_CIRCUIT_SYNC"
    elif data == GSMTC35.eForwardClass.DATA_CIRCUIT_ASYNC:
      return "DATA_CIRCUIT_ASYNC"
    elif data == GSMTC35.eForwardClass.DEDICATED_PACKED_ACCESS:
      return "DEDICATED_PACKED_ACCESS"
    elif data == GSMTC35.eForwardClass.DEDICATED_PAD_ACCESS:
      return "DEDICATED_PAD_ACCESS"

    return "UNDEFINED"

  class eForwardReason:
    UNCONDITIONAL = 0
    MOBILE_BUSY = 1
    NO_REPLY = 2
    NOT_REACHABLE = 3
    ALL_CALL_FORWARDING = 4
    ALL_CONDITIONAL_CALL_FORWARDING = 5

  @staticmethod
  def eForwardReasonToString(data):
    data = int(data)
    if data == GSMTC35.eForwardReason.UNCONDITIONAL:
      return "UNCONDITIONAL"
    elif data == GSMTC35.eForwardReason.MOBILE_BUSY:
      return "MOBILE_BUSY"
    elif data == GSMTC35.eForwardReason.NO_REPLY:
      return "NO_REPLY"
    elif data == GSMTC35.eForwardReason.NOT_REACHABLE:
      return "NOT_REACHABLE"
    elif data == GSMTC35.eForwardReason.ALL_CALL_FORWARDING:
      return "ALL_CALL_FORWARDING"
    elif data == GSMTC35.eForwardReason.ALL_CONDITIONAL_CALL_FORWARDING:
      return "ALL_CONDITIONAL_CALL_FORWARDING"

    return "UNDEFINED"

  ############################ STANDALONE FUNCTIONS ############################
  @staticmethod
  def changeBaudrateMode(old_baudrate, new_baudrate, port, pin="", puk="", pin2="", puk2="",
                         parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                         bytesize=serial.EIGHTBITS):
    """Change baudrate mode (can be done only if GSM module is not currently used)

    Keyword arguments:
      old_baudrate -- (int) Baudrate value usable to communicate with the GSM module
      new_baudrate -- (int) New baudrate value to communicate with the GSM module
                            /!\ Use "0" to let the GSM module use "auto-baudrate" mode
      port -- (string) Serial port name of the GSM serial connection
      pin -- (string, optional) PIN number if locked
      puk -- (string, optional) PUK number if locked
      pin2 -- (string, optional) PIN2 number if locked
      puk2 -- (string, optional) PUK2 number if locked
      parity -- (pySerial parity, optional) Serial connection parity (PARITY_NONE, PARITY_EVEN, PARITY_ODD PARITY_MARK, PARITY_SPACE)
      stopbits -- (pySerial stop bits, optional) Serial connection stop bits (STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO)
      bytesize -- (pySerial byte size, optional) Serial connection byte size (FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS)

    return: (bool) Baudrate changed
    """
    gsm = GSMTC35()
    if not gsm.setup(_port=port, _pin=pin, _puk=puk, _pin2=pin2, _puk2=puk2,
                     _baudrate=old_baudrate, _parity=parity,
                     _stopbits=stopbits, _bytesize=bytesize):
      logging.error("Impossible to initialize the GSM module")
      return False

    if not gsm.__selectBaudrateCommunicationType(new_baudrate):
      logging.error("Impossible to modify the baudrate")
      return False

    return True


  ################################### INIT ####################################
  def __init__(self):
    """Initialize the GSM module class with undefined serial connection"""
    self.__initialized = False
    self.__serial = serial.Serial()
    self.__timeout_sec = 0


  ################################### SETUP ####################################
  def setup(self, _port, _pin="", _puk="", _pin2="", _puk2="",
            _baudrate=115200, _parity=serial.PARITY_NONE,
            _stopbits=serial.STOPBITS_ONE, _bytesize=serial.EIGHTBITS,
            _timeout_sec=2):
    """Initialize the class (can be launched multiple time if setup changed or module crashed)

    Keyword arguments:
      _port -- (string) Serial port name of the GSM serial connection
      _baudrate -- (int, optional) Baudrate of the GSM serial connection
      _pin -- (string, optional) PIN number if locked (not needed to do it now but would improve reliability)
      _puk -- (string, optional) PUK number if locked (not needed to do it now but would improve reliability)
      _pin2 -- (string, optional) PIN2 number if locked (not needed to do it now but would improve reliability)
      _puk2 -- (string, optional) PUK2 number if locked (not needed to do it now but would improve reliability)
      _parity -- (pySerial parity, optional) Serial connection parity (PARITY_NONE, PARITY_EVEN, PARITY_ODD PARITY_MARK, PARITY_SPACE)
      _stopbits -- (pySerial stop bits, optional) Serial connection stop bits (STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO)
      _bytesize -- (pySerial byte size, optional) Serial connection byte size (FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS)
      _timeout_sec -- (int, optional) Default timeout in sec for GSM module to answer commands

    return: (bool) Module initialized
    """
    # Close potential previous GSM session
    self.__timeout_sec = _timeout_sec
    try:
      self.close()
    except Exception:
      pass

    # Create new GSM session
    try:
      self.__serial = serial.Serial(
                      port=_port,
                      baudrate=_baudrate,
                      parity=_parity,
                      stopbits=_stopbits,
                      bytesize=_bytesize,
                      timeout=_timeout_sec
                    )
    except serial.serialutil.SerialException:
      logging.error("Invalid serial port '"+str(_port)+"'")
      return False

    # Initialize the GSM module with specific commands
    is_init = True
    if self.__serial.isOpen():
      # Disable echo from GSM device
      if not self.__sendCmdAndCheckResult(GSMTC35.__BASE_AT+"E0"):
        logging.warning("Can't disable echo mode (ATE0 command)")
      # Use verbose answer (GSM module will return str like "OK\r\n" and not like "0")
      if not self.__sendCmdAndCheckResult(GSMTC35.__BASE_AT+"V1"):
        logging.error("Can't set proper answer type from GSM module (ATV command)")
        is_init = False
      # Use non-verbose error result ("ERROR" instead of "+CME ERROR: (...)")
      if not self.__sendCmdAndCheckResult(GSMTC35.__NORMAL_AT+"CMEE=0"):
        logging.warning("Can't set proper error format returned by GSM module (CMEE command)")

      # Enter PIN/PUK/PIN2/PUK2 as long as it is required (and that all goes well)
      # If PIN/PUK/PIN2/PUK2 in not specified but is needed, a warning will be displayed
      # but the function will continue.
      pin_status = ""
      while is_init and (pin_status != GSMTC35.eRequiredPin.READY):
        req_pin_result, pin_status = self.getPinStatus()
        if (not req_pin_result) or (len(pin_status) <=0):
          logging.error("Failed to get PIN status")
          is_init = False
        elif pin_status == GSMTC35.eRequiredPin.READY:
          logging.debug("No PIN needed")
          break
        elif pin_status == GSMTC35.eRequiredPin.PIN:
          if len(_pin) > 0:
            if not self.enterPin(_pin):
              logging.error("Invalid PIN \""+str(_pin)+"\" (YOU HAVE A MAXIMUM OF 3 TRY)")
              is_init = False
            else:
              logging.debug("PIN entered with success")
          else:
            logging.warning("Some initialization may not work without PIN activated")
            break
        elif pin_status == GSMTC35.eRequiredPin.PUK:
          if len(_puk) > 0:
            if not self.enterPin(_puk):
              logging.error("Invalid PUK \""+str(_puk)+"\"")
              is_init = False
            else:
              logging.debug("PUK entered with success")
          else:
            logging.warning("Some initialization may not work without PUK activated")
            break
        elif pin_status == GSMTC35.eRequiredPin.PIN2:
          if len(_pin2) > 0:
            if not self.enterPin(_pin2):
              logging.error("Invalid PIN2 \""+str(_pin2)+"\" (YOU HAVE A MAXIMUM OF 3 TRY)")
              is_init = False
            else:
              logging.debug("PIN2 entered with success")
          else:
            logging.warning("Some initialization may not work without PIN2 activated")
            break
        elif pin_status == GSMTC35.eRequiredPin.PUK2:
          if len(_puk2) > 0:
            if not self.enterPin(_puk2):
              logging.error("Invalid PUK2 \""+str(_puk2)+"\"")
              is_init = False
            else:
              logging.debug("PUK2 entered with success")
          else:
            logging.warning("Some initialization may not work without PUK2 activated")
            break

      #Disable asynchronous triggers (SMS, calls, temperature)
      self.__disableAsynchronousTriggers()

      # Set to text mode
      if not self.__sendCmdAndCheckResult(GSMTC35.__NORMAL_AT+"CMGF=1"):
        logging.error("Impossible to set module to text mode (CMGF command)")
        is_init = False
      # Select fixed baudrate communication
      if not self.__selectBaudrateCommunicationType(_baudrate):
        # Some function will not work if this is not activated (alarm, wake-up ACK, ...)
        logging.warning("Impossible to have fixed baudrate communication (IPR command)")

    self.__initialized = is_init
    if not self.__initialized:
      self.__serial.close()

    return self.__initialized

  def isInitialized(self):
    """Check if GSM class is initialized"""
    return self.__initialized

  def close(self):
    """Close GSM session (free the GSM serial port)"""
    # Try to put auto-baudrate mode back
    self.__selectBaudrateCommunicationType(0)

    # Then close the serial port
    self.__serial.close()


  def reboot(self, waiting_time_sec=10):
    """Reboot GSM module (you need to initialize the GSM module again after a reboot)

    Keyword arguments:
      additional_timeout -- (int, optional) Additional time (in sec) to reboot

    return: (bool) Reboot successful
    """
    restarted = self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CFUN=1,1",
                                             result="^SYSSTART",
                                             additional_timeout=waiting_time_sec)

    # Be sure user will not use the class without initializing it again
    if restarted:
      self.close()

    return restarted


  ######################### INTERNAL UTILITY FUNCTIONS #########################
  @staticmethod
  def __deleteQuote(quoted_string):
    """Delete first and last " or ' from {quoted_string}

    Keyword arguments:
      quoted_string -- (string) String to get rid of quotes

    return: (string) {quoted_string} without quotes
     """
    str_lengh = len(quoted_string)
    if str_lengh > 1:
      if (quoted_string[0] == '"') or (quoted_string[0] == "'"):
        # Delete first ' or "
        quoted_string = quoted_string[1:]
      str_lengh = len(quoted_string)
      if str_lengh >= 1:
        if (quoted_string[str_lengh-1] == '"') or (quoted_string[str_lengh-1] == "'"):
          # Delete last ' or "
          quoted_string = quoted_string[:str_lengh-1]
    return quoted_string


  def __readLine(self):
    """Read one line from the serial port (not blocking)

    Note: Even if the end of line is not found, the data is returned

    return: (string) Line without the end of line (empty if nothing received)
    """
    eol = '\r\n'
    leneol = len(eol)
    line = ""
    while True:
      c = self.__serial.read(1)
      if c:
        line += c.decode()
        if line[-leneol:] == eol:
          line = line[:len(line)-leneol]
          break
      else:
        if str(line).startswith(">"):
          logging.debug("Reading line while GSM is waiting content")
        else:
          logging.warning("Received data without eol: \""+str(line)+"\"")
        break
    logging.debug("[IN] "+str(line))
    return line


  def __deleteAllRxData(self):
    """Delete all received data from the serial port

    return: (int) Number of deleted bytes
    """
    bytesToRead = self.__serial.inWaiting()
    if bytesToRead <= 0:
      return 0

    data = self.__serial.read(bytesToRead)
    logging.debug("[DELETED]"+str(data))

    return bytesToRead


  def __waitDataContains(self, content, error_result, additional_timeout=0):
    """Wait to receive specific data from the serial port

    Keyword arguments:
      content -- (string) Data to wait from the serial port
      error_result -- (string) Line meaning an error occured (sent by the module), empty means not used
      additional_timeout -- (int) Additional time to wait the match (added with base timeout)

    return: (bool) Is data received before timeout (if {error_result} is received, False is returned)
    """
    start_time = time.time()
    while time.time() - start_time < self.__timeout_sec + additional_timeout:
      while self.__serial.inWaiting() > 0:
        line = self.__readLine()
        if content in line:
          return True
        if len(error_result) > 0 and error_result == line:
          logging.error("GSM module returned error \""+str(error_result)+"\"")
          return False
      # Wait 100ms if no data in the serial buffer
      time.sleep(.100)
    #logging.error("Impossible to get line containing \""+str(content)+"\" on time")
    return False


  def __getNotEmptyLine(self, content="", error_result=__RETURN_ERROR, additional_timeout=0):
    """Wait to receive a line containing at least {content} (or any char if {content} is empty)

    Keyword arguments:
      content -- (string) Data to wait from the serial port
      error_result -- (string) Line meaning an error occured (sent by the module)
      additional_timeout -- (int) Additional time to wait the match (added with base timeout)

    return: (string) Line received (without eol), empty if not found or if an error occured
    """
    start_time = time.time()
    while time.time() - start_time < self.__timeout_sec + additional_timeout:
      while self.__serial.inWaiting() > 0:
        line = self.__readLine()
        if len(error_result) > 0 and (str(error_result) == str(line)):
          logging.error("GSM module returned error \""+str(error_result)+"\"")
          return ""
        if (content in line) and len(line) > 0:
          return line
      # Wait 100ms if no data in the serial buffer
      time.sleep(.100)
    logging.error("Impossible to get line containing \""+str(content)+"\" on time")
    return ""


  def __sendLine(self, before, after=""):
    """Send line to the serial port as followed: {before}\r\n{after}

    Keyword arguments:
      before -- (string) Data to send before the end of line
      after -- (string) Data to send after the end of line

    return: (bool) Send line worked?
    """
    if self.__serial.write("{}\r\n".format(before).encode()):
      logging.debug("[OUT] "+str(before))
      if after != "":
        time.sleep(0.100)
        if self.__serial.write(after.encode()) > 0:
          logging.debug("[OUT] "+str(after))
          return True
        else:
          logging.warning("Failed to write \""+str(after)+"\" to GSM (after).")
      else:
        return True
    else:
      logging.warning("Failed to write \""+str(after)+"\" to GSM (before).")
    return False

  def __sendCmdAndGetNotEmptyLine(self, cmd, after="", additional_timeout=0,
                                  content="", error_result=__RETURN_ERROR):
    """Send command to the GSM module and get line containing {content}

    Keyword arguments:
      cmd -- (string) Command to send to the module (without eol)
      after -- (string, optional) Data to send to the module after the end of line
      additional_timeout -- (int, optional) Additional time (in sec) to wait the content to appear
      content -- (string, optional) Data to wait from the GSM module (line containing this will be returned
      error_result -- (string) Line meaning an error occured (sent by the module)

    return: (string) Line without the end of line containing {content} (empty if nothing received or if an error occured)
    """
    self.__deleteAllRxData()
    if self.__sendLine(cmd, after):
      return self.__getNotEmptyLine(content, error_result, additional_timeout)
    return ""


  def __sendCmdAndGetFullResult(self, cmd, after="", additional_timeout=0,
                                result=__RETURN_OK, error_result=__RETURN_ERROR):
    """Send command to the GSM module and get all lines before {result}

    Keyword arguments:
      cmd -- (string) Command to send to the module (without eol)
      after -- (string, optional) Data to send to the module after the end of line
      additional_timeout -- (int, optional) Additional time (in sec) to wait the content to appear
      result -- (string, optional) Line to wait from the GSM module (all lines will be returned BEFORE the {result} line)
      error_result -- (string) Line meaning an error occured (sent by the module)

    return: ([string,]) All lines without the end of line (empty if nothing received or if an error occured)
    """
    val_result = []

    self.__deleteAllRxData()
    if not self.__sendLine(cmd, after):
      return val_result

    start_time = time.time()
    while time.time() - start_time < self.__timeout_sec + additional_timeout:
      while self.__serial.inWaiting() > 0:
        line = self.__readLine()
        if (result == line) and len(line) > 0:
          return val_result
        if len(error_result) > 0 and (error_result == line):
          logging.error("Error returned by GSM module for \""+str(cmd)+"\" command")
          return []
        elif line != "":
          val_result.append(line)
      # Wait 100ms if no data in the serial buffer
      time.sleep(.100)

    logging.error("Impossible to get line equal to \""+str(result)+"\" on time")
    return val_result


  def __sendCmdAndCheckResult(self, cmd, after="", additional_timeout=0,
                              result=__RETURN_OK, error_result=__RETURN_ERROR):
    """Send command to the GSM module and wait specific result

    Keyword arguments:
      cmd -- (string) Command to send to the module (without eol)
      after -- (string, optional) Data to send to the module after the end of line
      additional_timeout -- (int, optional) Additional time (in sec) to wait the result
      result -- (string, optional) Data to wait from the GSM module
      error_result -- (string) Line meaning an error occured (sent by the module)

    return: (bool) Command successful (result returned from the GSM module)
    """
    self.__deleteAllRxData()
    if not self.__sendLine(cmd, after):
      return False

    result = self.__waitDataContains(result, error_result, additional_timeout)

    if not result:
      logging.error("Sending \""+str(cmd)+"\" and \""+str(after)+"\" failed")

    return result


  def __deleteSpecificSMS(self, index):
    """Delete SMS with specific index

    Keyword arguments:
      index -- (int) Index of the SMS to delete from the GSM module (can be found by reading SMS)

    Note: Even if this function is not done for that: On some device, GSMTC35.eSMS.ALL_SMS,
      GSMTC35.eSMS.UNREAD_SMS and GSMTC35.eSMS.READ_SMS may be used instead of
      {index} to delete multiple SMS at once (not working for GSMTC35).

    return: (bool) Delete successful
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CMGD="+str(index))


  @staticmethod
  def __guessPhoneNumberType(phone_number):
    """Guess phone number type from phone number

    Keyword arguments:
      phone_number -- (string) Phone number

    return: (GSMTC35.__ePhoneNumberType) Phone number type
    """
    # Is it an international phone number?
    if len(phone_number) > 1 and phone_number[0] == "+":
      return GSMTC35.__ePhoneNumberType.INTERNATIONAL

    # Is it a valid local phone number?
    try:
      int(phone_number)
      return GSMTC35.__ePhoneNumberType.LOCAL
    except ValueError:
      pass

    logging.error("Phone number "+str(phone_number)+" is not valid")
    return GSMTC35.__ePhoneNumberType.ERROR


  def __selectPhonebook(self, phonebook_type):
    """Select phonebook in order to use it for future operations on phonebooks

    Note: If {phonebook_type} specifies "Current phonebook", no action will be
    made and the function will return True

    Keyword arguments:
      phonebook_type -- (GSMTC35.ePhonebookType) Phonebook type

    return: (bool) Phonebook selected
    """
    if phonebook_type == GSMTC35.ePhonebookType.CURRENT:
      return True

    return self.__sendCmdAndCheckResult(GSMTC35.__NORMAL_AT+"CPBS=\""
                                        +str(phonebook_type)+"\"")


  def __getCurrentPhonebookRange(self):
    """Get information about current phonebook restrictions (min and max entry
       indexes, max phone number length and max contact name length)

    return: (int, int, int, int) First entry index, Last entry index, max phone
      number length, max contact name length (for all elements: -1 if data is invalid)
    """
    # Send the command to get all info
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CPBR=?",
                                              content="+CPBR: ")

    index_min = -1
    index_max = -1
    index_max_phone_length = -1
    max_contact_name_length = -1

    if result == "" or len(result) <= 8 or result[:7] != "+CPBR: ":
      logging.error("Phonebook information request failed")
      return index_min, index_max, index_max_phone_length, max_contact_name_length

    # Get result without "+CPBR: "
    result = result[7:]

    # Delete potential "(" and ")" from the result
    result = result.replace("(","")
    result = result.replace(")","")

    # Split index_min and the other part of the result
    split_result = result.split("-")
    if len(split_result) < 2:
      logging.error("Impossible to split phonebook information")
      return index_min, index_max, index_max_phone_length, max_contact_name_length

    try:
      index_min = int(split_result[0])
    except ValueError:
      # Index min is not correct, let's try to get other elements
      logging.warning("Impossible to get the phonebook min index")

    # Split last elements
    split_result = split_result[1].split(",")

    # Get the index_max
    if len(split_result) >= 1:
      try:
        index_max = int(split_result[0])
      except ValueError:
        # Index max is not correct, let's try to get other elements
        logging.warning("Impossible to get the phonebook max index (value error)")
    else:
      logging.warning("Impossible to get the phonebook max index (length error)")

    # Get max phone length
    if len(split_result) >= 2:
      try:
        index_max_phone_length = int(split_result[1])
      except ValueError:
        # Max phone length is not correct, let's try to get other elements
        logging.warning("Impossible to get the phonebook max phone length (value error)")
    else:
      logging.warning("Impossible to get the phonebook max phone length (length error)")

    # Get contact name length
    if len(split_result) >= 3:
      try:
        max_contact_name_length = int(split_result[2])
      except ValueError:
        # Max phone length is not correct, let's try to get other elements
        logging.warning("Impossible to get the phonebook max contact name length (value error)")
    else:
      logging.warning("Impossible to get the phonebook max contact name length (length error)")

    # Delete last "OK" from buffer
    self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    # Return final result
    return index_min, index_max, index_max_phone_length, max_contact_name_length


  def __selectBaudrateCommunicationType(self, baudrate):
    """Select baudrate communication type with the module (fixed baudrate of auto-baudrate)

    Keyword arguments:
      baudrate -- (int) 0 for auto-baudrate or baudrate value for fixed baudrate

    return: (bool) Baudrate selected
    """
    return self.__sendCmdAndCheckResult(GSMTC35.__NORMAL_AT+"IPR="+str(baudrate))


  def __setInternalClockToSpecificDate(self, date):
    """Set the GSM module internal clock to specific date

    Keyword arguments:
      date -- (datetime.datetime) Date to set in the internal clock

    return: (bool) Date successfully modified
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CCLK=\""
                                        +date.strftime(GSMTC35.__DATE_FORMAT)+"\"")


  def __addAlarm(self, date, message=""):
    """Add an alarm to show a message at the exact specified time

    Note: The reference date is the  one from the internal clock
          (see {getDateFromInternalClock()} to get the reference clock)

    Keyword arguments:
      date -- (datetime.datetime) Date

    return: (bool) Alarm successfully set
    """
    message_in_cmd = ""
    if len(message) > 0:
      message_in_cmd = ",\""+str(message)+"\""

    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CALA=\""
                                        +date.strftime(GSMTC35.__DATE_FORMAT)
                                        +"\",0,0"+message_in_cmd)


  def __addAlarmAsAChrono(self, time_in_sec, message=""):
    """Add an alarm to show a message in {time_in_sec} seconds

    Note: The reference date is the  one from the internal clock
          (see {getDateFromInternalClock()} to get the reference clock)

    Keyword arguments:
      time_in_sec -- (int) Time to wait before the alarm will happen

    return: (bool) Alarm successfully set
    """
    date = self.getDateFromInternalClock()
    if date == -1:
      return False

    date = date + datetime.timedelta(seconds=time_in_sec)

    return self.__addAlarm(date, message)


  def __disableAsynchronousTriggers(self):
    """Disable asynchronous triggers (SMS, calls, temperature)

    return: (bool) All triggers disabled
    """
    all_disable = True
    # Don't show received call in buffer without query
    if not self.__sendCmdAndCheckResult(GSMTC35.__NORMAL_AT+"CLIP=0"):
      logging.warning("Can't disable mode showing phone number when calling (CLIP command)")
      all_disable = False
    # Don't show received SMS in buffer without query
    if not self.__sendCmdAndCheckResult(GSMTC35.__NORMAL_AT+"CNMI=0,0"):
      logging.warning("Can't disable mode showing received SMS (CNMI command)")
      all_disable = False
    # Don't show temperature issue without query
    if not self.__sendCmdAndCheckResult(GSMTC35.__BASE_AT+"^SCTM=0"):
      logging.warning("Can't disable mode showing critical temperature (SCTM command)")
      all_disable = False

    return all_disable

  __gsm0338_base_table = u"@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
  __gsm0338_extra_table = u"````````````````````^```````````````````{}`````\\````````````[~]`|````````````````````````````````````€``````````````````````````"

  @staticmethod
  def __gsm0338Encode(plaintext):
    res = ""
    for c in plaintext:
      idx = GSMTC35.__gsm0338_base_table.find(c)
      if idx != -1:
        res += chr(int(idx))
        continue
      idx = GSMTC35.__gsm0338_extra_table.find(c)
      if idx != -1:
        res += chr(27) + chr(int(idx))
    return res

  @staticmethod
  def __gsm0338Decode(text):
    result = []
    normal_table = True
    for i in text:
      if int(i) == 27:
        normal_table = False
      else:
        if normal_table:
          result += GSMTC35.__gsm0338_base_table[int(i)]
        else:
          result += GSMTC35.__gsm0338_extra_table[int(i)]
        normal_table = True

    return "".join(result)

  @staticmethod
  def __is7BitCompatible(plaintext):
    """Check that the data can be encoded in GSM03.38 (extra table included)

    Keyword arguments:
      plaintext -- (bytes) Content to check if can be encoded into 7bit

    return: (bool) Data can be encoded into 7Bit
    """
    try:
      # Do not encode data if not 7bit compatible
      for c in str(plaintext):
        if (c == '`') or ((not (c in GSMTC35.__gsm0338_base_table)) and (not (c in GSMTC35.__gsm0338_extra_table))):
          return False
    except (UnicodeEncodeError, UnicodeDecodeError):
      logging.debug("Unicode detected so data not 7bit compatible")
      return False

    return True

  @staticmethod
  def __unpack7bit(content, header_length=0, message_length=0):
    """Decode byte with Default Alphabet encoding ('7bit')

    Function logic inspired from https://github.com/pmarti/python-messaging/blob/master/messaging/utils.py#L173

    Keyword arguments:
      content -- (bytes) Content to decode as hexa

    return: (bytes) Decoded content
    """
    try:
      unichr
    except NameError:
      unichr = chr

    count = last = 0
    result = []
    try:
      for i in range(0, len(content), 2):
        byte = int(content[i:i + 2], 16)
        mask = 0x7F >> count
        out = ((byte & mask) << count) + last
        last = byte >> (7 - count)
        result.append(out)

        if len(result) >= 0xa0:
          break

        if count == 6:
          result.append(last)
          last = 0

        count = (count + 1) % 7

      result = ''.join(map(unichr, result))

      # Convert GSM 7bit encodage (GSM03.38) into normal string
      return GSMTC35.__gsm0338Decode(result[:message_length].encode())
    except ValueError:
      return ''

  @staticmethod
  def __unpack8bit(encoded_data):
    """Decode hexa byte encoded with 8bit encoding

    Keyword arguments:
      encoded_data -- (bytes) Content to decode

    return: (bytes) Decoded content
    """
    encoded_data = [ord(x) for x in encoded_data]
    return ''.join([chr(x) for x in encoded_data])

  @staticmethod
  def __unpackUCS2(encoded_data):
    """Decode hexa byte encoded with extended encoding (UTF-16 / UCS2)

    Keyword arguments:
      encoded_data -- (bytes) Content to decode

    return: (bytes) Decoded content
    """
    return encoded_data.decode('utf-16be')

  @staticmethod
  def __packUCS2(content, user_data_id=0):
    """Encode bytes into hexadecimal representation of extended encoded User Data with User Data Length (UTF-16 / UCS2)

    Keyword arguments:
      content -- (bytes) Content to encode
      user_data_id -- (int[1:255] or 0 for random, optional, default: random) ID of the potential multipart message

    return: ([bytes]) List of Hexadecimal representation of extended encoded User Data with User Data Length (UTF-16 / UCS2)
    """
    # Check if message can be sent in one part or is multipart
    if (len(content) > 70):
      logging.debug("Encoding multipart message in UCS-2 (Utf-16)")
      # Get all parts
      n = 67 # Max number of unicode char in multipart message (excepting header)
      all_msg_to_encode = [content[i:i+n] for i in range(0, len(content), n)]
      logging.debug("Messages to encode:\n - "+'\n - '.join(all_msg_to_encode))
      all_encoded_msg = []
      nb_of_parts = len(all_msg_to_encode)
      # Have same user data ID for all message parts
      if user_data_id == 0:
        user_data_id = randint(0, 255)
      # Encode data as multipart messages
      for current_id in range(nb_of_parts):
        encoded_message = binascii.hexlify(all_msg_to_encode[current_id].encode('utf-16be')).decode()
        if len(encoded_message) % 4 != 0:
          encoded_message = str("00") + str(encoded_message)

        encoded_message = GSMTC35.__generateMultipartUDH(user_data_id, current_id+1, nb_of_parts, True) + encoded_message

        encoded_message_length = format(int(ceil(len(encoded_message)/2)), 'x')
        if len(encoded_message_length) % 2 != 0:
          encoded_message_length = "0" + encoded_message_length

        encoded_message = str(str(encoded_message_length) + str(encoded_message)).upper().replace("'", "")

        all_encoded_msg.append(encoded_message)

      return all_encoded_msg
    else:
      encoded_message = binascii.hexlify(content.encode('utf-16be')).decode()
      if len(encoded_message) % 4 != 0:
        encoded_message = str("00") + str(encoded_message)

      encoded_message_length = format(int(2*((len(content)))), 'x')
      if len(encoded_message_length) % 2 != 0:
        encoded_message_length = "0" + encoded_message_length

      return [str(str(encoded_message_length) + str(encoded_message)).upper().replace("'", "")]

  @staticmethod
  def __generateMultipartUDH(user_data_id, current_part, nb_of_parts, string_mode=False):
    """Generate User Data Header for multipart message purpose

    Keyword arguments:
      user_data_id -- (int[0:255]) ID of the multipart message
      current_part -- (int) Current part of the multipart message
      nb_of_parts -- (int) Number of parts of the full multipart message
      string_mode -- (bool) Returning the UDH as string or as unicode?

    return: (string) User Data Header
    """
    if string_mode:
      # UDHL (User Data Header Length, not including UDHL byte)
      result = "05"
      # Information element identifier (not used)
      result += "00"
      # Header Length, not including this byte
      result += "03"
      # User Data ID (reference)
      result += '{:02X}'.format(user_data_id)
      # Number of parts
      result += '{:02X}'.format(nb_of_parts)
      # Current part
      result += '{:02X}'.format(current_part)
    else:
      # UDHL (User Data Header Length, not including UDHL byte)
      result = "\x05"
      # Information element identifier (not used)
      result += "\x00"
      # Header Length, not including this byte
      result += "\x03"
      # User Data ID (reference)
      result += chr(user_data_id)
      # Number of parts
      result += chr(nb_of_parts)
      # Current part
      result += chr(current_part)

    return result

  @staticmethod
  def __pack7Bit(plaintext, user_data_id=0):
    """Encode bytes into hexadecimal representation of 7bit GSM encoding with length (very basic UTF-8)

    Function logic inspired from https://github.com/pmarti/python-messaging/blob/master/messaging/utils.py#L98

    Keyword arguments:
      plaintext -- (bytes) Content to encode
      user_data_id -- (int[1:255] or 0 for random, optional, default: random) ID of the potential multipart message

    return: (bool, [bytes]) (Successfully encoded, List of Hexadecimal representation of 7bit GSM encoded User Data with User Data Length (very basic UTF-8))
    """
    # Do not encode data if not 7bit compatible
    if not GSMTC35.__is7BitCompatible(plaintext):
      return False, []

    encoded_message = ""

    # Be sure that message is a string
    if sys.version_info >= (3,):
      txt = plaintext.encode().decode('latin1')
    else:
      txt = plaintext

    # Encode string in GSM 03.38 encoding
    txt = GSMTC35.__gsm0338Encode(plaintext)

    # Check if message can be sent in one part or is multipart
    if (len(txt) > 140):
      logging.debug("Encoding multipart message in 7bit")
      # Get all parts that needs to be encoded
      n = 138 # Max number of 7 bit chars in multipart message (excepting header)
      all_msg_to_encode = [txt[i:i+n] for i in range(0, len(txt), n)]
      logging.debug("Messages to encode:\n - "+'\n - '.join(all_msg_to_encode))
      all_encoded_msg = []
      nb_of_parts = len(all_msg_to_encode)
      # Have same user data ID for all message parts
      if user_data_id == 0:
        user_data_id = randint(0, 255)
      # Encode data as multipart messages
      for current_id in range(nb_of_parts):
        txt = "\x00\x00\x00\x00\x00\x00" + "\x00"+ all_msg_to_encode[current_id]
        tl = len(txt)
        txt += '\x00'
        msgl = int(len(txt) * 7 / 8)
        op = [-1] * msgl
        c = shift = 0

        for n in range(msgl):
          if shift == 6:
            c += 1

          shift = n % 7
          lb = ord(txt[c]) >> shift
          hb = (ord(txt[c + 1]) << (7 - shift) & 255)
          op[n] = lb + hb
          c += 1

        for i, char in enumerate(GSMTC35.__generateMultipartUDH(user_data_id, current_id+1, nb_of_parts)):
          op[i] = ord(char)

        encoded_message = chr(tl) + ''.join(map(chr, op))

        all_encoded_msg.append(str(''.join(["%02x" % ord(n) for n in encoded_message])).upper().replace("'", ""))

      return True, all_encoded_msg
    else:
      # Encode data as normal message
      logging.debug("Encoding one SMS in 7bit")
      tl = len(txt)
      txt += '\x00'
      msgl = int(len(txt) * 7 / 8)
      op = [-1] * msgl
      c = shift = 0

      for n in range(msgl):
        if shift == 6:
          c += 1

        shift = n % 7
        lb = ord(txt[c]) >> shift
        hb = (ord(txt[c + 1]) << (7 - shift) & 255)
        op[n] = lb + hb
        c += 1

      encoded_message = chr(tl) + ''.join(map(chr, op))

      return True, [str(''.join(["%02x" % ord(n) for n in encoded_message])).upper().replace("'", "")]

  @staticmethod
  def __decodePduSms(msg, decode_sms):
    """Decode PDU SMS content

    Keyword arguments:
      msg -- (string) PDU hexa string to decoded
      decode_sms -- (bool) Is it needed to decode SMS content ?

    return: (list) List of decoded content containing potentially 'phone_number', 'date', 'time', 'sms',
                   'sms_encoded', 'service_center_type', 'service_center_phone_number', 'phone_number_type',
                   'charset'
                   if message has an header: 'header_iei', 'header_ie_data'
                   if message is a multipart message (MMS): 'header_multipart_ref_id',
                     'header_multipart_current_part_nb', 'header_multipart_nb_of_part'
    """
    result = {}

    # Be sure message is of hexa type
    try:
      int(str(msg), 16)
    except ValueError:
      logging.error("Can't decode PDU SMS because is not hexadecimal content: \""+str(msg)+"\"")
      return result

    # Service center data (type and phone number)
    lengthServiceCenter = int(msg[:2], 16)
    msg = msg[2:]

    serviceCenterType = int(msg[:2], 16)
    result["service_center_type"] = serviceCenterType
    msg = msg[2:]

    serviceCenterEncodedPhone = msg[:lengthServiceCenter*2-2]
    if (lengthServiceCenter%2 != 0):
      serviceCenterEncodedPhone = serviceCenterEncodedPhone[0:len(serviceCenterEncodedPhone)-2] + serviceCenterEncodedPhone[len(serviceCenterEncodedPhone)-1:]
    msg = msg[lengthServiceCenter*2-2:]

    serviceCenterDecodedPhone = ""
    for number in range(0,lengthServiceCenter*2-3):
      if number %2 == 0:
        serviceCenterDecodedPhone = serviceCenterDecodedPhone + serviceCenterEncodedPhone[number]
      else:
        serviceCenterDecodedPhone = serviceCenterDecodedPhone[:len(serviceCenterDecodedPhone) - 1] + str(serviceCenterEncodedPhone[number]) + serviceCenterDecodedPhone[len(serviceCenterDecodedPhone) - 1:]
    result["service_center_phone_number"] = str(serviceCenterDecodedPhone)

    # First byte
    firstByte = int(msg[:2], 16)
    if firstByte & 0b1000000:
      contentContainsHeader = True
    else:
      contentContainsHeader = False
    msg = msg[2:]

    # Sender Phone data (type and number)
    lengthSenderPhoneNumber = int(msg[:2], 16)
    msg = msg[2:]

    senderType = int(msg[:2], 16)
    msg = msg[2:]
    result["phone_number_type"] = senderType

    phoneNumberEncoded = msg[:lengthSenderPhoneNumber+1]
    if (lengthSenderPhoneNumber%2 != 0):
      phoneNumberEncoded = phoneNumberEncoded[0:len(phoneNumberEncoded)-2] + phoneNumberEncoded[len(phoneNumberEncoded)-1:]
    msg = msg[lengthSenderPhoneNumber+1:]

    phoneNumberDecoded = ""
    if senderType == GSMTC35.__ePhoneNumberType.INTERNATIONAL:
      phoneNumberDecoded = "+" + phoneNumberDecoded

    for number in range(0,lengthSenderPhoneNumber):
      if number %2 == 0:
        phoneNumberDecoded = phoneNumberDecoded + phoneNumberEncoded[number]
      else:
        phoneNumberDecoded = phoneNumberDecoded[:len(phoneNumberDecoded) - 1] + str(phoneNumberEncoded[number]) + phoneNumberDecoded[len(phoneNumberDecoded) - 1:]

    result["phone_number"] = str(phoneNumberDecoded)

    # Protocol ID / TP-PID
    # protocolId = int(msg[:2], 16)
    msg = msg[2:]

    # Data coding scheme / TP-DCS
    dataCodingScheme = int(msg[:2], 16)
    msg = msg[2:]

    # Timestamp
    timestampEncoded = msg[:14]
    msg = msg[14:]
    dateDecoded = timestampEncoded[1] + timestampEncoded[0] + "/" \
                       + timestampEncoded[3] + timestampEncoded[2] + "/" \
                       + timestampEncoded[5] + timestampEncoded[4]
    timeDecoded = timestampEncoded[7] + timestampEncoded[6] + ":" \
                       + timestampEncoded[9] + timestampEncoded[8] + ":" \
                       + timestampEncoded[11] + timestampEncoded[10] + ""
    gmt = timestampEncoded[13] + timestampEncoded[12]
    gmtDecoded = ""
    if (int(gmt[1], 16) >= 8):
      gmtDecoded = "GMT-"
      gmt = gmt[0] + str(int(gmt[1], 16) - 8)
    else:
      gmtDecoded += "GMT+"
    gmtDecoded += str(int(gmt, 10)/4)
    result["date"] = str(dateDecoded)
    result["time"] = str(str(timeDecoded)+" "+str(gmtDecoded))

    # Message content
    messageLength = int(msg[:2], 16)
    msg = msg[2:]

    # Charset
    if (dataCodingScheme & 0xc0) == 0:
      if dataCodingScheme & 0x20:
        logging.error("Not possible to find correct encoding")
        if decode_sms:
          return result
        else:
          charset = "unknown"
      try:
        charset = {0x00: '7bit', 0x04: '8bit', 0x08: 'utf16-be'}[dataCodingScheme & 0x0c]
      except KeyError:
        logging.error("Not possible to find correct encoding")
        if decode_sms:
          return result
        else:
          charset = "unknown"
    elif (dataCodingScheme & 0xf0) in (0xc0, 0xd0):
      charset = '7bit'
    elif (dataCodingScheme & 0xf0) == 0xe0:
      charset = 'utf16-be'
    elif (dataCodingScheme & 0xf0) == 0xf0:
      charset = {0x00: '7bit', 0x04: '8bit'}[dataCodingScheme & 0x04]
    else:
      logging.error("Not possible to find correct encoding")
      if decode_sms:
        return result
      else:
        charset = "unknown"

    result["charset"] = str(charset)

    # SMS content header
    headerLength = 0
    if contentContainsHeader:
      headerLength = int(msg[:2], 16)
      if headerLength > 0:
        if charset == '7bit':
          headerLength = int(ceil(headerLength * 7.0 / 8.0))
          if ((headerLength % 2) != 0):
            headerLength = headerLength + 1
        result["header_iei"] = int(msg[2:4], 16)
        headerIeLength = int(msg[4:6], 16)
        result["header_ie_data"] = msg[6:6+headerIeLength*2]
        # Add multipart information if IEI is of type 'Concatenated short message' (0x00 or 0x08)
        if result["header_iei"] == 0 or result["header_iei"] == 8:
          result["header_multipart_ref_id"] = int(result["header_ie_data"][:2], 16)
          result["header_multipart_nb_of_part"] = int(result["header_ie_data"][2:4], 16)
          result["header_multipart_current_part_nb"] = int(result["header_ie_data"][4:6], 16)

    # SMS Content
    user_data = ""
    logging.debug("Encoded "+str(charset)+" SMS content: "+str(msg))
    if charset == '7bit':  # Default Alphabet aka basic 7 bit coding - 03.38 S6.2.1
      user_data = GSMTC35.__unpack7bit(msg, headerLength, messageLength)
      # Remove header (+ header size byte) from the message
      if contentContainsHeader:
        user_data = user_data[headerLength+1:]
      user_data_encoded = binascii.hexlify(user_data.encode()).decode()
    elif charset == '8bit':  # 8 bit coding is "user defined". S6.2.2
      # TODO: Handle header message (please provide me an example full --debug log to help me)
      user_data = GSMTC35.__unpack8bit(binascii.unhexlify(msg))
      user_data_encoded = msg
    elif charset == 'utf16-be':  # UTF-16 aka UCS2, S6.2.3
      user_data = GSMTC35.__unpackUCS2(binascii.unhexlify(msg))
      if contentContainsHeader:
        user_data = user_data[int(ceil((headerLength+1)/2)):]
      user_data_encoded = msg[int((headerLength+1)*2):]

    else:
      logging.error("Not possible to find correct encoding")
      if decode_sms:
        return result
      else:
        user_data_encoded = msg

    result["sms"] = user_data
    logging.debug("Decoded SMS content: "+user_data)
    user_data_encoded = user_data_encoded.upper()
    result["sms_encoded"] = user_data_encoded
    logging.debug("Re-encoded SMS content: "+user_data_encoded)

    return result

  ######################## INFO AND UTILITY FUNCTIONS ##########################
  def isAlive(self):
    """Check if the GSM module is alive (answers to AT commands)

    return: (bool) Is GSM module alive
    """
    return self.__sendCmdAndCheckResult(GSMTC35.__BASE_AT)


  def getManufacturerId(self):
    """Get the GSM module manufacturer identification

    return: (string) Manufacturer identification
    """
    # Send request and get data
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CGMI")
    # Delete the "OK" of the request from the buffer
    if result != "":
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)
    return result


  def getModelId(self):
    """Get the GSM module model identification

    return: (string) Model identification
    """
    # Send request and get data
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CGMM")
    # Delete the "OK" of the request from the buffer
    if result != "":
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)
    return result


  def getRevisionId(self):
    """Get the GSM module revision identification of software status

    return: (string) Revision identification
    """
    # Send request and get data
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CGMR")
    # Delete the "OK" of the request from the buffer
    if result != "":
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)
    return result


  def getIMEI(self):
    """Get the product serial number ID (IMEI)

    return: (string) Product serial number ID (IMEI)
    """
    # Send request and get data
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CGSN")
    # Delete the "OK" of the request from the buffer
    if result != "":
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)
    return result


  def getIMSI(self):
    """Get the International Mobile Subscriber Identity (IMSI)

    return: (string) International Mobile Subscriber Identity (IMSI)
    """
    # Send request and get data
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CIMI")
    # Delete the "OK" of the request from the buffer
    if result != "":
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)
    return result


  def setModuleToManufacturerState(self):
    """Set the module parameters to manufacturer state

    return: (bool) Reset successful
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__BASE_AT+"&F0")


  def switchOff(self):
    """Switch off the module (module will not respond after this request)

    Connection to serial port is also terminated, an init will be needed
    to use this class again.

    return: (bool) Switch off successful
    """
    # Send request and get data
    result = self.__sendCmdAndCheckResult(cmd=GSMTC35.__BASE_AT+"^SMSO",
                                          result="MS OFF")
    # Delete the "OK" of the request from the buffer
    self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    if result:
      self.close()

    return result


  def getOperatorName(self):
    """Get current used operator name

    return: (string) Operator name
    """
    operator = ""

    # Set the COPS command correctly
    if not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"COPS=3,0"):
      logging.error("Impossible to set the COPS command")
      return operator

    # Send the command to get the operator name
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"COPS?",
                                              content="+COPS: ")
    if result == "" or len(result) <= 8 or result[0:7] != "+COPS: ":
      logging.error("Command to get the operator name failed")
      return operator

    # Get result without "+COPS: "
    result = result[7:]

    # Split remaining data from the line
    split_list = result.split(",")
    if len(split_list) < 3:
      logging.error("Impossible to split operator information")
      return operator

    # Get the operator name without quote (3th element from the list)
    operator = GSMTC35.__deleteQuote(split_list[2])

    # Delete last "OK" from buffer
    self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return operator


  def getSignalStrength(self):
    """Get current signal strength in dBm
    Range: -113 to -51 dBm (other values are incorrect)

    return: (int) -1 if not valid, else signal strength in dBm
    """
    sig_strength = -1

    # Send the command to get the signal power
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CSQ",
                                              content="+CSQ: ")
    #Check result:
    if result == "" or len(result) <= 7 or result[:6] != "+CSQ: ":
      logging.error("Command to get signal strength failed")
      return sig_strength

    # Get result without "+CSQ: "
    result = result[6:]

    # Split remaining data from the line
    split_list = result.split(",")
    if len(split_list) < 1:
      logging.error("Impossible to split signal strength")
      return sig_strength

    # Get the received signal strength (1st element)
    try:
      sig_strength = int(split_list[0])
    except ValueError:
      logging.error("Impossible to convert \""+str(split_list[0])+"\" into integer")
      return sig_strength

    # Delete last "OK" from buffer
    if sig_strength != -1:
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    # 99 means the GSM couldn't get the information, negative values are invalid
    if sig_strength >= 99 or sig_strength < 0:
      sig_strength = -1

    # Convert received data to dBm
    if sig_strength != -1:
      #(0, <=-113dBm), (1, -111dBm), (2, -109dBm), (30, -53dBm), (31, >=-51dBm)
      # --> strength (dBm) = 2* received data from module - 113
      sig_strength = 2*sig_strength - 113

    return sig_strength


  def getOperatorNames(self):
    """Get list of operator names stored in the GSM module

    return: ([string,]) List of operator names or empty list if an error occured
    """
    operators = self.__sendCmdAndGetFullResult(cmd=GSMTC35.__NORMAL_AT+"COPN")
    result = []

    if len(operators) <= 0:
      logging.error("Command to get operator names failed")
      return result

    for operator in operators:
      operator_name = ""
      if len(operator) > 8 or operator[:7] == "+COPN: ":
        operator = operator[7:]
        # Split remaining data from the line
        split_list = operator.split(",")
        if len(split_list) >= 2:
          # Get the operator name without quote (2nd element)
          operator_name = GSMTC35.__deleteQuote(split_list[1])
        else:
          logging.warning("Impossible to parse operator information \""+operator+"\"")
      else:
        loggging.warning("Impossible to get operator from \""+operator+"\" line")
      if operator_name != "":
        result.append(operator_name)

    return result


  def getNeighbourCells(self, waiting_time_sec=5):
    """Get neighbour cells

    Keyword arguments:
      waiting_time_sec -- (int, optional) Time to wait query to execute

    return: ([{'chann':(int), 'rs':(int), 'dbm':(int), 'plmn':(int), 'bcc':(int), 'c1':(int), 'c2':(int)}, ...]) List of neighbour cells
      chann (int): ARFCN (Absolute Frequency Channel Number) of the BCCH carrier
      rs (int): RSSI (Received signal strength) of the BCCH carrier, decimal value from
          0 to 63. The indicated value is composed of the measured value in dBm
          plus an offset. This is in accordance with a formula specified in 3GPP TS 05.08.
      dbm (int): Receiving level in dBm
      plmn (int): Public land mobile network (PLMN) ID code
      bcc (int): Base station colour code
      c1 (int): Coefficient for base station selection
      c2 (int): Coefficient for base station reselection
    """
    neighbour_cells = []

    lines = self.__sendCmdAndGetFullResult(cmd=GSMTC35.__BASE_AT+"^MONP",
                                           additional_timeout=waiting_time_sec)

    for line in lines:
      if len(line) <= 0:
        continue

      split_line = line.split()
      if len(split_line) >= 7:
        try:
          neighbour_cell = {}
          neighbour_cell['chann'] = int(split_line[0])
          neighbour_cell['rs'] = int(split_line[1])
          neighbour_cell['dbm'] = int(split_line[2])
          neighbour_cell['plmn'] = int(split_line[3])
          neighbour_cell['bcc'] = int(split_line[4])
          neighbour_cell['c1'] = int(split_line[5])
          neighbour_cell['c2'] = int(split_line[6])
          neighbour_cells.append(neighbour_cell)
        except ValueError:
          if split_line[0] == "chann":
            # We don't need to get first line returned by the GSM module
            pass
          else:
            logging.warning("Invalid numbers for neighbour cell \""+str(line)+"\"")
      else:
        logging.warning("Invalid number of element to parse for neighbour cell \""+str(line)+"\"")

    return neighbour_cells


  def getAccumulatedCallMeter(self):
    """Get the accumulated call meter in home units

    return: (int or long) Accumulated call meter value in home units (-1 if an error occurred)
    """
    int_result = -1

    # Send request and get data
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CACM?")

    if result == "" or len(result) <= 8 or result[0:7] != "+CACM: ":
      logging.error("Command to get the accumulated call meter failed")
      return int_result

    # Get result without "+CACM: " and without '"'
    result = GSMTC35.__deleteQuote(result[7:])

    try:
      int_result = int(result, 16)
    except ValueError:
      logging.error("Impossible to convert hexadecimal value \""+str(result)+"\" into integer")
      return int_result

    # Delete the "OK" of the request from the buffer
    if result != -1:
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return int_result


  def getAccumulatedCallMeterMaximum(self):
    """Get the accumulated call meter maximum in home units

    return: (int or long) Accumulated call meter maximum value in home units (-1 if an error occurred)
    """
    int_result = -1

    # Send request and get data
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CAMM?")

    if result == "" or len(result) <= 8 or result[0:7] != "+CAMM: ":
      logging.error("Command to get the accumulated call meter failed")
      return int_result

    # Get result without "+CAMM: " and without '"'
    result = GSMTC35.__deleteQuote(result[7:])

    try:
      int_result = int(result, 16)
    except ValueError:
      logging.error("Impossible to convert hexadecimal value \""+str(result)+"\" into integer")
      return int_result

    # Delete the "OK" of the request from the buffer
    if result != -1:
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return int_result


  def isTemperatureCritical(self):
    """Check if the temperature of the module is inside or outside the
       warning limits.

    return: (bool) Temperature is critical (warning sent by the module)
    """
    is_critical = False

    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__BASE_AT+"^SCTM?")

    if result == "" or len(result) <= 8 or result[0:7] != "^SCTM: ":
      logging.error("Command to get the temperature status failed")
      return is_critical

    # Get result without "^SCTM:"
    result = result[7:]

    # Split data
    split_list = result.split(",")
    if len(split_list) < 2:
      logging.error("Impossible to split temperature status")
      return is_critical

    # Get the received temperature status (2nd element)
    try:
      if int(split_list[1]) != 0:
        is_critical = True
      else:
        is_critical = False
    except ValueError:
      logging.error("Impossible to convert \""+str(split_list[1])+"\" into integer")
      return is_critical

    # Delete the "OK" of the request from the buffer
    self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return is_critical


  ############################### TIME FUNCTIONS ###############################
  def setInternalClockToCurrentDate(self):
    """Set the GSM module internal clock to current date

    return: (bool) Date successfully modified
    """
    return self.__setInternalClockToSpecificDate(datetime.datetime.now())


  def getDateFromInternalClock(self):
    """Get the date from the GSM module internal clock

    return: (datetime.datetime) Date stored in the GSM module or -1 if an error occured
    """
    # Send the command to get the date
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CCLK?",
                                              content="+CCLK: ")
    if result == "" or len(result) <= 8 or result[:7] != "+CCLK: ":
      logging.error("Command to get internal clock failed")
      return -1

    # Get date result without "+CCLK: " and delete quote
    date = GSMTC35.__deleteQuote(result[7:])

    # Delete last "OK" from buffer
    self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    # Get the date from string format to date type
    try:
      return datetime.datetime.strptime(date, GSMTC35.__DATE_FORMAT)
    except ValueError:
      return -1

    return -1


  ############################ PHONEBOOK FUNCTIONS #############################
  def getPhonebookEntries(self, phonebook_type = ePhonebookType.CURRENT, waiting_time_sec=60):
    """Get a list of phonebook entries (contact name, phone number and index)

    Keyword arguments:
      phonebook_type -- (GSMTC35.ePhonebookType, optional) Phonebook type
      waiting_time_sec -- (int, optional) Time to wait phonebook entries to be sent by GSM module

    return: ([{index:(int), phone_number:(string), contact_name:(string)}, ...])
      List of dictionary (each dictionary is a phonebook entry containing the
      entry index, the phone number and the contact name)
    """
    phonebook_entries = []

    # Select the correct phonebook
    if not self.__selectPhonebook(phonebook_type):
      logging.error("Impossible to select the phonebook")
      return phonebook_entries

    # Get information about phonebook range
    index_min, index_max, max_length_phone, max_length_name = self.__getCurrentPhonebookRange()
    if index_min < 0 or index_max < 0 or index_min > index_max:
      logging.error("Phonebook min or max indexes are not valid")
      return phonebook_entries

    # Get the phonebook data
    lines = self.__sendCmdAndGetFullResult(cmd=GSMTC35.__NORMAL_AT+"CPBR="+str(index_min)+","+str(index_max),
                                           additional_timeout=waiting_time_sec)

    if len(lines) <= 0:
      logging.warning("Impossible to get phonebook entries (error or no entries)")
      return phonebook_entries

    for line in lines:
      if line[:7] == "+CPBR: ":
        # Get result without "+CMGL: "
        line = line[7:]
        # Split remaining data from the line
        split_list = line.split(",")
        if len(split_list) >= 4:
          try:
            entry = {}
            entry["index"] = int(split_list[0])
            entry["phone_number"] = str(split_list[1])
            entry["contact_name"] = str(split_list[3])
            phonebook_entries.append(entry)
          except ValueError:
            logging.warning("Impossible to add this phonebook entry \""+str(line)+"\"")
        else:
          logging.warning("Impossible to split phonebook entry options \""+str(line)+"\"")
      else:
        logging.warning("Invalid phonebook entry line \""+str(line)+"\"")

    return phonebook_entries


  def addEntryToPhonebook(self, phone_number, contact_name, phonebook_type = ePhonebookType.CURRENT):
    """Add an entry to the phonebook (contact name and phone number)

    Keyword arguments:
      phone_number -- (string) Phone number to add in the entry
      contact_name -- (string) Name of contact associated with {phone_number}
      phonebook_type -- (GSMTC35.ePhonebookType, optional) Phonebook type

    return: (bool) Entry added
    """
    # Get phone number type (local, international, ...)
    phone_number_type = GSMTC35.__guessPhoneNumberType(phone_number)
    if phone_number_type == GSMTC35.__ePhoneNumberType.ERROR:
      logging.error("Impossible to guess the phone number type from the phone number")
      return False

    # Select the correct phonebook
    if not self.__selectPhonebook(phonebook_type):
      logging.error("Impossible to select the phonebook")
      return False

    # Check size of contact name and phone number
    index_min, index_max, max_length_phone, max_length_name = self.__getCurrentPhonebookRange()
    if max_length_phone < 0 or max_length_name < 0 or len(phone_number) > max_length_phone or len(contact_name) > max_length_name:
      logging.error("Phonebook max phone number and contact name length are not valid")
      return False

    # Add the entry
    return self.__sendCmdAndCheckResult(GSMTC35.__NORMAL_AT+"CPBW=,\""
                                        +str(phone_number)+"\","+str(phone_number_type)
                                        +",\""+str(contact_name)+"\"")


  def deleteEntryFromPhonebook(self, index, phonebook_type = ePhonebookType.CURRENT):
    """Delete a phonebook entry

    Keyword arguments:
      index -- (int) Index of the entry to delete
      phonebook_type -- (GSMTC35.ePhonebookType, optional) Phonebook type

    return: (bool) Entry deleted
    """
    # Select the correct phonebook
    if not self.__selectPhonebook(phonebook_type):
      logging.error("Impossible to select the phonebook")
      return False

    return self.__sendCmdAndCheckResult(GSMTC35.__NORMAL_AT+"CPBW="+str(index))


  def deleteAllEntriesFromPhonebook(self, phonebook_type = ePhonebookType.CURRENT):
    """Delete all phonebook entries

    Keyword arguments:
      phonebook_type -- (GSMTC35.ePhonebookType, optional) Phonebook type

    return: (bool) All entries deleted
    """
    # Select the correct phonebook
    if not self.__selectPhonebook(phonebook_type):
      logging.error("Impossible to select the phonebook")
      return False

    # Get entries to delete
    entries = self.getPhonebookEntries(GSMTC35.ePhonebookType.CURRENT)

    # Delete all phonebook entries
    all_deleted = True
    for entry in entries:
      if not self.deleteEntryFromPhonebook(entry['index'], GSMTC35.ePhonebookType.CURRENT):
        logging.warning("Impossible to delete entry "+str(entry['index'])+" ("+str(entry['contact_name'])+")")
        all_deleted = False

    return all_deleted


  ############################### SMS FUNCTIONS ################################
  def sendSMS(self, phone_number, msg, force_text_mode=False, network_delay_sec=5):
    """Send SMS/MMS to specific phone number

    Must be max 140 normal char or max 70 special char if you want to send it as a SMS
    Else it will be sent as MMS

    Keyword arguments:
      phone_number -- (string) Phone number (can be local or international)
      msg -- (unicode) Message to send (max 140 normal char or max 70 special char)
      force_text_mode -- (bool, default: PDU mode used) Force to use Text Mode instead of PDU mode (NOT RECOMMENDED)
      network_delay_sec -- (int, default: 5sec) Network delay to add when waiting SMS to be sent

    return: (bool) SMS sent
    """
    result = False

    using_text_mode = force_text_mode
    if not using_text_mode:
      using_text_mode = not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CMGF=0")

    if not using_text_mode:
      use_7bit, all_encoded_user_data_and_length = GSMTC35.__pack7Bit(msg)
      if use_7bit:
        logging.debug("Message will be sent in 7bit mode (default GSM alphabet)")
      else:
        # Encode message into UCS-2 (UTF16)
        logging.debug("Message will be sent in UCS-2 mode (Utf16)")
        all_encoded_user_data_and_length = GSMTC35.__packUCS2(msg)

      if len(all_encoded_user_data_and_length) <= 0:
        logging.error("Failed to encode SMS content")
        return False

      logging.debug("all_encoded_user_data_and_length:\n - "+str('\n - '.join(all_encoded_user_data_and_length)))

      # Encode phone number
      encoded_phone_number = ""
      phone_number = phone_number.replace("+","")
      previous_char_phone = ""
      current_pos = 0
      for c in phone_number:
        current_pos = current_pos + 1
        if current_pos % 2 == 0:
          encoded_phone_number = str(encoded_phone_number) + str(c) + str(previous_char_phone)
        previous_char_phone = c
      encoded_phone_number = str(encoded_phone_number) + str("F") + str(previous_char_phone)
      logging.debug("encoded_phone_number="+encoded_phone_number)

      # Get phone number length
      encoded_phone_number_length = format((len(encoded_phone_number) - 1), 'x')
      if len(encoded_phone_number_length) != 2:
        encoded_phone_number_length = "0" + encoded_phone_number_length
      logging.debug("encoded_phone_number_length="+str(encoded_phone_number_length))

      # Create fully encoded message
      # SCA (service center length (1 byte) + service center address information)
      base_encoded_message = "00"
      # PDU Type
      # - Bit 7: Reply Path (not used, should be 0)
      # - Bit 6: UDHI (1 <=> UD contains header in addition to message)
      # - Bit 5: SRR (Status report requested ?, should be 0)
      # - Bit 4: VP field present? (should be 0)
      # - Bit 3: VP field (0 <=> relative, 1 <=> absolute, should be 0)
      # - Bit 2: RD (0 <=> Accept SMS-Submit with same SMSC, 1 <=> Reject, should be 0)
      # - Bit 1&0: Message Type (should be "SMS-Submit" <=> "01")
      if len(all_encoded_user_data_and_length) > 1:
        base_encoded_message += "41"
      else:
        base_encoded_message += "01"
      # MR (Message reference, must be random between 0 and 255)
      base_encoded_message += '{:02X}'.format(randint(0, 255))
      # Destination Address
      base_encoded_message += encoded_phone_number_length
      base_encoded_message += "91" # Type of number (International)
      base_encoded_message += encoded_phone_number
      # Protocol identifier
      base_encoded_message += "00" # Protocol Identifier (PID, Short Message <=> "00")
      # Data Coding Scheme (DCS, "08" <=> UCS2, "00" <=> GSM 7 bit)
      if use_7bit:
        base_encoded_message += "00"
      else:
        base_encoded_message += "08"

      # User data length (UDL, 1 byte) + User data (UD)
      result = True
      count = 0
      for encoded_user_data_and_length in all_encoded_user_data_and_length:
        fully_encoded_message = base_encoded_message + encoded_user_data_and_length
        fully_encoded_message = fully_encoded_message.upper()
        logging.debug("fully encoded message="+str(fully_encoded_message))

        # Wait a bit every time a part of the message is sent
        if (len(all_encoded_user_data_and_length) > 1) and (count > 0):
          logging.debug("Wait a bit before send next message part")
          time.sleep(network_delay_sec)
        count += 1

        # Send the SMS or all multipart messages (MMS)
        # AT+CMGS=SIZE with SIZE = message size - service center length and content (1 byte)
        if not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CMGS=" \
                                            +str(int((len(fully_encoded_message)-2)/2)), \
                                            after=fully_encoded_message+GSMTC35.__CTRL_Z, \
                                            additional_timeout=network_delay_sec):
          result = False

      if not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CMGF=1"):
        logging.warning("Could not go back to text mode")
    else:
      if using_text_mode and (not force_text_mode):
        logging.warning("Could not go to PDU mode, trying to send message in normal mode, some character may be missing")

      msg_length = len(msg)
      # Check if must be sent in multiple SMS or not (separate SMS since Text mode can't handle multipart SMS)
      n = 140
      if msg_length > 70:
        if GSMTC35.__is7BitCompatible(msg):
          if msg_length > 140:
            logging.warning("Message must be sent in multiple <=140 char SMS (not multipart SMS because Text Mode is used)")
          else:
            logging.debug("SMS can be sent in one basic part")
        else:
          logging.warning("Message must be sent in multiple <=70 char SMS (not multipart SMS because Text Mode is used)")
          n = 70
      else:
        logging.debug("SMS can be sent in one unicode part")

      # Sending all SMS
      all_sms_to_send = [msg[i:i+n] for i in range(0, len(msg), n)]
      result = True
      for sms_to_send in all_sms_to_send:
        if not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CMGS=\"" \
                                            +phone_number+"\"", \
                                            after=sms_to_send+GSMTC35.__CTRL_Z, \
                                            additional_timeout=network_delay_sec):
          result = False

    return result


  def getSMS(self, sms_type=eSMS.ALL_SMS, decode_sms=True, force_text_mode=False, waiting_time_sec=10):
    """Get SMS (using PDU mode, fallback with Text mode if failed)

    Keyword arguments:
      sms_type -- (string) Type of SMS to get (possible values: GSMTC35.eSMS.ALL_SMS,
                           GSMTC35.eSMS.UNREAD_SMS or GSMTC35.eSMS.READ_SMS)
      decode_sms -- (bool, optional, default: True) Decode SMS content or keep it in encoded format (+ charset)
      force_text_mode -- (bool, optional, default: False) Force to use 'text mode' instead of 'pdu mode' to get sms (may lead to inconsistent sms content)
      waiting_time_sec -- (int, optional) Time to wait SMS to be displayed by GSM module

    return: ([{"index":, "status":, "phone_number":, "date":, "time":, "sms", "sms_encoded":},]) List of requested SMS (list of dictionaries)
            Explanation of dictionaries content:
              - index (int) Index of the SMS from the GSM module point of view
              - status (GSMTC35.eSMS) SMS type
              - phone_number (string) Phone number which send the SMS
              - date (string) Date SMS was received
              - time (string) Time SMS was received
              - sms (string) Content of the SMS (decoded, if PDU mode is not used or did not work then content may vary depending on device)
              - sms_encoded (string) Content of the SMS (encoded in hexadecimal readable format. Data not given if PDU mode did not worked or is not used)
              If PDU mode worked, additional 'bonus' fields will be available:
              - phone_number_type (int) Phone number type using GSM 04.08 specification (145 <=> international, 129 <=> national)
              - service_center_type (int) Service center phone number type using GSM 04.08 specification (145 <=> international, 129 <=> national)
              - service_center_phone_number (string) Service center phone number
              - charset (string) Charset used by the sender to encode the SMS
              If PDU mode worked and that the SMS has an header:
              - header_iei (int) Header IEI of the SMS
              - header_ie_data (string) Header IE data of the SMS (encoded in hexadecimal readable format)
              If PDU mode worked and that the SMS has an header and is multipart (MMS):
              - header_multipart_ref_id (int) ID of the MMS
              - header_multipart_current_part_nb (int) Current part of the MMS
              - header_multipart_nb_of_part (int) Total number of part of the MMS
    """
    all_sms = []

    using_text_mode = force_text_mode
    if not force_text_mode:
      # Trying to go in PDU mode (if fails, use text mode)
      using_text_mode = not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CMGF=0")

    if not using_text_mode:
      # Getting SMS using PDU mode
      all_lines_retrieved = False
      lines = self.__sendCmdAndGetFullResult(cmd=GSMTC35.__NORMAL_AT+"CMGL="+GSMTC35.__smsTypeTextToPdu(str(sms_type)), error_result="",
                                             additional_timeout=waiting_time_sec)
      sms = {}
      for line in lines:
        if line[:7] == "+CMGL: ":
          # A new SMS is found
          line = line[7:]
          split_list = line.split(",")
          if len(split_list) >= 4:
            try:
              sms["index"] = int(split_list[0])
              sms["status"] = GSMTC35.__smsTypePduToText(split_list[1])
            except ValueError:
              logging.error("One of the SMS is not valid, command options: \""+str(line)+"\"")
              sms = {}
        elif "index" in sms:
          # Content of the previously detected SMS should be there
          # Do not throw if SMS is not decoded successfully (for reliability)
          is_decoded = False
          try:
            decoded_data = GSMTC35.__decodePduSms(line, decode_sms)
            is_decoded = True
          except ValueError:
            logging.error("One of the SMS is not valid, sms hexa content: \""+str(line)+"\"")

          if is_decoded and ("sms" in decoded_data) and ("phone_number" in decoded_data) \
             and ("date" in decoded_data) and ("time" in decoded_data) and ("charset" in decoded_data):
            # SMS is valid (merge sms data and add sms to all sms)
            sms.update(decoded_data)
            all_sms.append(sms)

          # Let's check if there is other sms !
          sms = {}
        else:
          # Inconsistent data, continue
          logging.warning("One of the SMS is not valid, command options (2): \""+str(line)+"\"")
          sms = {}
      # Go back to text mode
      if not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CMGF=1"):
        logging.warning("Could not go back to text mode")
    else:
      # Getting SMS using text mode
      if using_text_mode and (not force_text_mode):
        logging.warning("Could not go to PDU mode, trying to get sms with normal mode, some character may not be displayed")
      all_lines_retrieved = False
      lines = self.__sendCmdAndGetFullResult(cmd=GSMTC35.__NORMAL_AT+"CMGL=\""+str(sms_type)+"\"", error_result="",
                                             additional_timeout=waiting_time_sec)
      while not all_lines_retrieved:
        # Make sure the "OK" sent by the module is not part of an SMS
        if len(lines) > 0:
          additional_line = self.__getNotEmptyLine("", "", 0)
          if len(additional_line) > 0:
            lines.append(self.__RETURN_OK) # Lost SMS part
            lines.append(additional_line)
          else:
            all_lines_retrieved = True
        else:
          all_lines_retrieved = True
      # Parse SMS from lines
      sms = {}
      for line in lines:
        if line[:7] == "+CMGL: ":
          if bool(sms):
            all_sms.append(sms)
          sms = {}
          # Get result without "+CMGL: "
          line = line[7:]
          # Split remaining data from the line
          split_list = line.split(",")
          if len(split_list) >= 6:
            try:
              sms["index"] = int(split_list[0])
              sms["status"] = GSMTC35.__deleteQuote(split_list[1])
              sms["phone_number"] = GSMTC35.__deleteQuote(split_list[2])
              sms["date"] = GSMTC35.__deleteQuote(split_list[4])
              sms["time"] = GSMTC35.__deleteQuote(split_list[5])
              sms["sms"] = ""
              sms["charset"] = "TC35TextModeInconsistentCharset"
            except ValueError:
              logging.error("One of the SMS is not valid, command options: \""+str(line)+"\"")
              sms = {}
        elif bool(sms):
          if ("sms" in sms) and (sms["sms"] != ""):
            sms["sms"] = sms["sms"] + "\n" + line
          else:
            sms["sms"] = line
        else:
          logging.error("\""+line+"\" not usable")

      # Last SMS must also be stored
      if ("index" in sms) and ("sms" in sms) and not (sms in all_sms):
        # An empty line may appear in last SMS due to GSM module communication
        if (len(sms["sms"]) >= 1) and (sms["sms"][len(sms["sms"])-1:len(sms["sms"])] == "\n"):
          sms["sms"] = sms["sms"][:len(sms["sms"])-1]
        all_sms.append(sms)

    return all_sms


  def deleteSMS(self, sms_type = eSMS.ALL_SMS):
    """Delete multiple or one SMS

    Keyword arguments:
      sms_type -- (string or int, optional) Type or index of SMS to delete (possible values:
                    index of the SMS to delete (integer), GSMTC35.eSMS.ALL_SMS,
                    GSMTC35.eSMS.UNREAD_SMS or GSMTC35.eSMS.READ_SMS)

    return: (bool) All SMS of {sms_type} type are deleted
    """
    # Case sms_type is an index:
    try:
      return self.__deleteSpecificSMS(int(sms_type))
    except ValueError:
      pass

    # Case SMS index must be found to delete them
    all_delete_ok = True

    all_sms_to_delete = self.getSMS(sms_type)
    for sms in all_sms_to_delete:
      sms_delete_ok = self.__deleteSpecificSMS(sms["index"])
      all_delete_ok = all_delete_ok and sms_delete_ok

    return all_delete_ok


  ############################### CALL FUNCTIONS ###############################
  def hangUpCall(self):
    """Stop current call (hang up)

    return: (bool) Hang up is a success
    """
    result = self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CHUP")
    if not result:
      # Try to hang up with an other method if the previous one didn't work
      logging.warning("First method to hang up call failed...\r\nTrying an other...")
      result = self.__sendCmdAndCheckResult(cmd=GSMTC35.__BASE_AT+"H")

    return result


  def isSomeoneCalling(self, wait_time_sec=0):
    """Check if there is an incoming call (blocking for {wait_time_sec} seconds)

    Keyword arguments:
      wait_time_sec -- (int, optional) Additional time to wait someone to call

    return: (bool) There is an incoming call waiting to be picked up
    """
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CPAS",
                                              additional_timeout=wait_time_sec,
                                              content="+CPAS:")
    return ("3" in result)


  def isCallInProgress(self):
    """Check if there is a call in progress

    return: (bool) There is a call in progress
    """
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CPAS",
                                              content="+CPAS:")
    return ("4" in result)


  def pickUpCall(self):
    """Answer incoming call (pick up)

    return: (bool) An incoming call has been picked up
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__BASE_AT+"A;")


  def call(self, phone_number, hide_phone_number=False, waiting_time_sec=20):
    """Call {phone_number} and wait {waiting_time_sec} it's picked up (previous call will be terminated)

    WARNING: This function does not end the call:
      - If picked up: Call will finished once the other phone stops the call
      - If not picked up: Will leave a voice messaging of undefined time (depending on the other phone)

    Keyword arguments:
      phone_number -- (string) Phone number to call
      hide_phone_number -- (bool, optional) Enable/Disable phone number presentation to called phone
      waiting_time_sec -- (int, optional) Blocking time in sec to wait a call to be picked up

    return: (bool) Call in progress
    """
    # Hang up is necessary in order to not have false positive
    #(sending an ATD command while a call is already in progress would return an "OK" from the GSM module)
    self.hangUpCall()

    if not hide_phone_number:
      return self.__sendCmdAndCheckResult(cmd=GSMTC35.__BASE_AT+"D"
                                          +phone_number+";",
                                          additional_timeout=waiting_time_sec)
    else:
      return self.__sendCmdAndCheckResult(cmd=GSMTC35.__BASE_AT+"D#31#"
                                          +phone_number+";",
                                          additional_timeout=waiting_time_sec)


  def reCall(self, waiting_time_sec=20):
    """Call last called {phone_number} and wait {waiting_time_sec} it's picked up (previous call will be terminated)

    WARNING: This function does not end the call:
      - If picked up: Call will finished once the other phone stops the call
      - If not picked up: Will leave a voice messaging of undefined time (depending on the other phone)

    Keyword arguments:
      waiting_time_sec -- (int, optional) Blocking time in sec to wait a call to be picked up

    return: (bool) Call in progress or in voice messaging
    """
    # Hang up is necessary in order to not have false positive
    self.hangUpCall()
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__BASE_AT+"DL;",
                                        additional_timeout=waiting_time_sec)


  def getLastCallDuration(self):
    """Get duration of last call

    return: (int or long) Last call duration in seconds (-1 if error)
    """
    call_duration = -1

    # Send the command to get the last call duration
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__BASE_AT+"^SLCD",
                                              content="^SLCD: ")

    # Get the call duration from the received line
    if result == "" or len(result) <= 7 or result[:7] != "^SLCD: ":
      logging.error("Command to get last call duration failed")
      return call_duration

    # Get the call duration
    call_duration = result[7:]

    # Convert to seconds
    try:
      h, m, s = call_duration.split(':')
      call_duration = int(h) * 3600 + int(m) * 60 + int(s)
    except ValueError:
      pass

    # Delete last "OK" from buffer
    self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return call_duration


  def getCurrentCallState(self):
    """Check the current call state and get potential phone number

    return: (GSMTC35.eCall, string) Return the call state (NOCALL = -1, ACTIVE = 0,
                                    HELD = 1, DIALING = 2, ALERTING = 3, INCOMING = 4,
                                    WAITING = 5) followed by the potential phone
                                    number (empty if not found)
    """
    data = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CLCC",
                                            content="+CLCC:", error_result=self.__RETURN_OK)
    call_state = GSMTC35.eCall.NOCALL
    phone = ""

    if len(data) <= 8 or data[:7] != "+CLCC: ":
      # No call
      return call_state, phone

    data = data[7:]
    split_list = data.split(",")
    if len(split_list) < 3:
      logging.error("Impossible to split current call data")
      return call_state, phone

    # Get call state (3th element from the list)
    try:
      call_state = int(split_list[2])
    except ValueError:
      logging.warning("Impossible to get call state")

    # Get the phone number if it exists
    if len(split_list) >= 6:
      phone = GSMTC35.__deleteQuote(split_list[5])
    else:
      logging.warning("Impossible to get phone number")

    # Delete last "OK" from buffer
    self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return call_state, phone

  ############################# FORWARD FUNCTIONS ##############################
  def setForwardStatus(self, forward_reason, forward_class, enable, phone_number=None):
    """Enable/disable call/sms/data/fax forwarding

    Keyword arguments:
      forward_reason -- (eForwardReason) Reason to forward (unconditional, phone busy, ...)
      forward_class -- (eForwardClass) Type of information to forward (SMS, call, fax, data, ...)
      enable -- (bool) Enable (True) or disable (False) forwarding ?
      phone_number -- (str, optional) Phone number to use if enabling forwarding (mandatory) or phone number to disable (optional)

    return: (bool) Request success?
    """
    # Guess phone number type which is needed for enabling forwarding
    phone_number_type = ""
    if phone_number:
      phone_number_type = str(GSMTC35.__guessPhoneNumberType(phone_number))
    else:
      phone_number = ""

    # Forwarding mode
    if enable:
      # Register and activate call forwarding
      mode = "3"
    else:
      # Erase and deactivate call forwarding
      mode = "4"

    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CCFC="\
                                        +str(forward_reason)+","+str(mode)+","+str(phone_number)+","\
                                        +str(phone_number_type)+","+str(forward_class),\
                                        additional_timeout=15)

  def getForwardStatus(self):
    """Get forward status (is call/data/fax/sms forwarded to an other phone number?)

    return: ([{'enabled':bool, 'class':str, 'phone_number':str, 'is_international':bool}]) List of forwarded status
    """
    forwards = self.__sendCmdAndGetFullResult(cmd=GSMTC35.__NORMAL_AT+"CCFC=0,2", additional_timeout=15)
    result = []

    if len(forwards) <= 0:
      logging.error("Command to get forward status failed")
      return result

    for forward in forwards:
      enabled_status = ""
      _class = ""
      if len(forward) > 8 or forward[:7] == "+CCFC: ":
        forward = forward[7:]
        # Split remaining data from the line
        split_list = forward.split(",")
        if len(split_list) >= 2:
          # Get all data
          enabled_status = bool(split_list[0] == "1")
          _class = GSMTC35.eForwardClassToString(int(split_list[1]))
          forward_res = {"enabled": enabled_status, "class": _class}
          if len(split_list) >= 3:
            forward_res["phone_number"] = str(split_list[2])
          if len(split_list) >= 4:
            forward_res["is_international"] = bool(int(split_list[3]) == GSMTC35.__ePhoneNumberType.INTERNATIONAL)
          result.append(forward_res)
        else:
          logging.warning("Impossible to parse forward information \""+forward+"\"")
      else:
        loggging.warning("Impossible to get forward from \""+forward+"\" line")

    return result


  ################################ PIN FUNCTIONS ###############################
  def getPinStatus(self):
    """Check if the SIM card PIN is ready (PUK may also be needed)

    return: (bool, GSMTC35.eRequiredPin) (Did request worked?, Required PIN ("READY" if none needed)
    """
    res = self.__sendCmdAndGetFullResult(cmd=GSMTC35.__NORMAL_AT+"CPIN?")

    if len(res) <= 0:
      return False, ""

    base_cpin="+CPIN: "
    res = ','.join(res)
    if str(base_cpin+GSMTC35.eRequiredPin.READY) in res:
      required_pin = GSMTC35.eRequiredPin.READY
    elif str(base_cpin+GSMTC35.eRequiredPin.PIN2) in res:
      required_pin = GSMTC35.eRequiredPin.PIN2
    elif str(base_cpin+GSMTC35.eRequiredPin.PUK2) in res:
      required_pin = GSMTC35.eRequiredPin.PUK2
    elif str(base_cpin+GSMTC35.eRequiredPin.PIN) in res:
      required_pin = GSMTC35.eRequiredPin.PIN
    elif str(base_cpin+GSMTC35.eRequiredPin.PUK) in res:
      required_pin = GSMTC35.eRequiredPin.PUK
    else:
      logging.warning("Failed to understand if PIN(2)/PUK(2) are needed.")
      return False, ""

    logging.debug("Found PIN status: "+str(required_pin))
    return True, required_pin


  def enterPin(self, pin):
    """Enter the SIM card PIN to be able to call/receive call and send/receive SMS

    WARNING: This function may lock your SIM card if you try to enter more than
    3 wrong PIN numbers.

    Keyword arguments:
      pin -- (string) SIM card PIN

    return: (bool) PIN is correct
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CPIN="+str(pin),
                                        additional_timeout=10)


  def lockSimPin(self, current_pin):
    """Lock the use of the SIM card with PIN (the PIN will be asked after a reboot)

    Keyword arguments:
      current_pin -- (int or string) Current PIN number linked to the SIM card

    return: (bool) SIM PIN lock enabled
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CLCK=\"SC\",1,"
                                        +str(current_pin))


  def unlockSimPin(self, current_pin):
    """Unlock the use of the SIM card with PIN (the PIN will be asked after a reboot)

    Keyword arguments:
      current_pin -- (int or string) Current PIN number linked to the SIM card

    return: (bool) SIM PIN unlock enabled
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CLCK=\"SC\",0,"
                                        +str(current_pin))


  def changePin(self, old_pin, new_pin):
    """Edit PIN number stored in the SIM card

    Note: A call to this function will lock SIM Pin
          You need to call {unlockSimPin()} to unlock it.

    Keyword arguments:
      old_pin -- (int or string) Current PIN
      new_pin -- (int or string) PIN to use for future PIN login

    return: (bool) SIM PIN edited
    """
    if not self.lockSimPin(old_pin):
      logging.error("Impossible to lock SIM card with PIN before changing PIN")
      return False

    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CPWD=\"SC\",\""
                                        +str(old_pin)+"\",\""+str(new_pin)+"\"")


  ################################# SLEEP MODE #################################
  def isInSleepMode(self):
    """Check if the GSM module is in sleep mode (if yes, nothing can be done
       until it wakes up).

    return: (bool) GSM module is in sleep mode
    """
    # Send the command to get sleep mode state
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CFUN?",
                                              content="+CFUN: ")
    if result == "":
      # Module is in sleep mode
      return True

    # At this point, we are sure the module is not sleeping since at least
    # one char was received from the GSM module.
    # (Checking the returned value is here only to send warning
    # if something is not logical in the result or to handle impossible case)

    if len(result) < 8 or result[:7] != "+CFUN: ":
      logging.warning("Impossible to get valid result from sleep query")
      # Since some char were in the buffer, there is no sleep mode
      return False

    # Get result without "+CFUN: "
    result = result[7:]

    try:
      if int(result) == 0:
        # The module answers that it is in sleep mode
        # (this case is impossible... but who knows)
        return True
    except ValueError:
      logging.warning("Impossible to convert \""+str(result)+"\" into integer")

    # Delete last "OK" from buffer
    self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return False


  def sleep(self, wake_up_with_timer_in_sec=-1, wake_up_with_call=False,
            wake_up_with_sms=False, wake_up_with_temperature_warning=False):
    """Blocking sleep until a specific action occurs (enter low power mode)

    Keyword arguments:
      wake_up_with_timer_in_sec -- (int) Time before waking-up the module (in sec), -1 to not use timer
      wake_up_with_call -- (bool) Wake-up the module if a call is received
      wake_up_with_sms -- (bool) Wake-up the module if a SMS is received
      wake_up_with_temperature_warning -- (bool) Wake-up the module too high or too low

    return: (bool, bool, bool, bool, bool) Sleep was entered and is now finished, Waked-up by timer,
                                           Waked-up by call, Waked-up by SMS, Waked-up by temperature
    """
    min_alarm_sec = 10
    gsm_waked_up_by_alarm = False
    gsm_waked_up_by_call = False
    gsm_waked_up_by_sms = False
    gsm_waked_up_by_temperature = False

    # Do not allow infinite sleep (better stop the device with {switchOff()})
    if (not wake_up_with_call) and (not wake_up_with_sms) \
       and (not wake_up_with_temperature_warning) \
       and (wake_up_with_timer_in_sec < min_alarm_sec):
      logging.error("Sleep can't be used without any possibility to wake up")
      logging.error("Be sure at least one trigger is used (and timer >= 10sec)")
      return False, gsm_waked_up_by_alarm, gsm_waked_up_by_call, gsm_waked_up_by_sms, gsm_waked_up_by_temperature

    # Enable all requested wake up
    if wake_up_with_call:
      if not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CLIP=1"):
        logging.error("Impossible to enable the wake up with call")
        self.__disableAsynchronousTriggers()
        return False, gsm_waked_up_by_alarm, gsm_waked_up_by_call, gsm_waked_up_by_sms, gsm_waked_up_by_temperature

    if wake_up_with_sms:
      if not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CNMI=1,1"):
        logging.error("Impossible to enable the wake up with SMS")
        self.__disableAsynchronousTriggers()
        return False, gsm_waked_up_by_alarm, gsm_waked_up_by_call, gsm_waked_up_by_sms, gsm_waked_up_by_temperature

    if wake_up_with_temperature_warning:
      if not self.__sendCmdAndCheckResult(cmd=GSMTC35.__BASE_AT+"^SCTM=1"):
        logging.error("Impossible to enable the wake up with temperature report")
        self.__disableAsynchronousTriggers()
        return False, gsm_waked_up_by_alarm, gsm_waked_up_by_call, gsm_waked_up_by_sms, gsm_waked_up_by_temperature

    if wake_up_with_timer_in_sec >= min_alarm_sec:
      if not self.__addAlarmAsAChrono(wake_up_with_timer_in_sec + 1): # Add one sec (due to query time)
        logging.error("Impossible to enable the wake up with alarm")
        self.__disableAsynchronousTriggers()
        return False, gsm_waked_up_by_alarm, gsm_waked_up_by_call, gsm_waked_up_by_sms, gsm_waked_up_by_temperature

    # Sleep
    if not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CFUN=0"):
      logging.error("Impossible to enable sleep mode")
      self.__disableAsynchronousTriggers()
      return False, gsm_waked_up_by_alarm, gsm_waked_up_by_call, gsm_waked_up_by_sms, gsm_waked_up_by_temperature

    # Wait until a trigger stops the sleep mode
    while True:
      # Wait any element to arrive from buffer (means sleep mode not
      data = self.__getNotEmptyLine(additional_timeout=3600)

      # At least one character was received (it means sleep mode is not active anymore)
      if len(data) > 0:
        if len(data) >= 5:
          wakeup_type = data[:5]
          if wakeup_type == "+CMTI":
            gsm_waked_up_by_sms = True
          elif wakeup_type == "+CLIP" or wakeup_type == "RING":
            gsm_waked_up_by_call = True
          elif wakeup_type == "^SCTM":
            gsm_waked_up_by_temperature = True
          elif wakeup_type == "+CALA":
            gsm_waked_up_by_alarm = True

      # Set to asynchronous element to default state
      self.__disableAsynchronousTriggers()

      return True, gsm_waked_up_by_alarm, gsm_waked_up_by_call, gsm_waked_up_by_sms, gsm_waked_up_by_temperature


################################# HELP FUNCTION ################################
def __help(func="", filename=__file__):
  """Show help on how to use command line GSM module functions

  Keyword arguments:
    func -- (string, optional) Command line function requiring help, none will show all function
    filename -- (string, optional) File name of the python script implementing the commands
  """
  func = func.lower()
  filename = "python " + str(filename)

  # Help
  if func in ("h", "help"):
    print("Give information to use all or specific GSM class commands\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -h [command (default: none)]\r\n"
          +filename+" --help [command (default: none)]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -h \r\n"
          +filename+" -h baudrate \r\n"
          +filename+" --help \r\n"
          +filename+" --help baudrate")
    return
  elif func == "":
    print("HELP (-h, --help): Give information to use all or specific GSM class commands")

  # Baudrate
  if func in ("b", "baudrate"):
    print("Specifiy serial baudrate for GSM module <-> master communication\r\n"
          +"Default value (if not called): 115200\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -b [baudrate]\r\n"
          +filename+" --baudrate [baudrate]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -b 9600\r\n"
          +filename+" --baudrate 115200 \r\n")
    return
  elif func == "":
    print("BAUDRATE (-b, --baudrate): Specify serial baudrate for GSM module <-> master communication (Optional)")

  # Serial Port
  if func in ("u", "serialport"):
    print("Specify serial port for GSM module <-> master communication\r\n"
          +"Default value (if not called): COM1\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -u [port]\r\n"
          +filename+" --serialPort [port]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -u COM4\r\n"
          +filename+" --serialPort /dev/ttyS3 \r\n")
    return
  elif func == "":
    print("SERIAL PORT (-u, --serialPort): Specify serial port for GSM module <-> master communication (Optional)")

  # PIN
  if func in ("p", "pin"):
    print("Specify SIM card PIN\r\n"
          +"Default value (if not called): No PIN for SIM card\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -p [pin number]\r\n"
          +filename+" --pin [pin number]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -p 1234\r\n"
          +filename+" --pin 0000 \r\n")
    return
  elif func == "":
    print("PIN (-p, --pin): Specify SIM card PIN (Optional)")

  # PUK
  if func in ("y", "puk"):
    print("Specify SIM card PUK\r\n"
          +"Default value (if not called): No PUK for SIM card\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -y [puk number]\r\n"
          +filename+" --puk [puk number]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -y 12345678\r\n"
          +filename+" --puk 12345678 \r\n")
    return
  elif func == "":
    print("PUK (-y, --puk): Specify SIM card PUK (Optional)")

  # PIN2
  if func in ("x", "pin2"):
    print("Specify SIM card PIN2\r\n"
          +"Default value (if not called): No PIN2 for SIM card\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -x [pin2 number]\r\n"
          +filename+" --pin2 [pin2 number]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -x 1234\r\n"
          +filename+" --pin2 0000 \r\n")
    return
  elif func == "":
    print("PIN2 (-x, --pin2): Specify SIM card PIN2 (Optional)")

  # PUK2
  if func in ("v", "puk2"):
    print("Specify SIM card PUK2\r\n"
          +"Default value (if not called): No PUK2 for SIM card\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -v [puk2 number]\r\n"
          +filename+" --puk2 [puk2 number]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -v 1234\r\n"
          +filename+" --puk2 0000 \r\n")
    return
  elif func == "":
    print("PUK2 (-v, --puk2): Specify SIM card PUK2 (Optional)")

  # Is alive
  if func in ("a", "isalive"):
    print("Check if the GSM module is alive (answers ping)\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -a\r\n"
          +filename+" --isAlive\r\n")
    return
  elif func == "":
    print("IS ALIVE (-a, --isAlive): Check if the GSM module answers ping")

  # Call
  if func in ("c", "call"):
    print("Call a phone number\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -c [phone number] [Hide phone number? True/False (default: False)] [pick-up wait in sec (default: 20sec)]\r\n"
          +filename+" --call [phone number] [Hide phone number? True/False (default: False)] [pick-up wait in sec (default: 20sec)]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -c +33601234567\r\n"
          +filename+" --call 0601234567 True\r\n"
          +filename+" --call 0601234567 False 30\r\n"
          +"\r\n"
          +"Note:\r\n"
          +" - The call may still be active after this call\r\n"
          +" - Local or international phone numbers may not work depending on your GSM module\r\n")
    return
  elif func == "":
    print("CALL (-c, --call): Call a phone number")

  # Stop call
  if func in ("t", "hangupcall"):
    print("Stop current phone call\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -t\r\n"
          +filename+" --hangUpCall\r\n")
    return
  elif func == "":
    print("STOP CALL (-t, --hangUpCall): Stop current phone call")

  # Is someone calling
  if func in ("i", "issomeonecalling"):
    print("Check if someone is trying to call the GSM module\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -i\r\n"
          +filename+" --isSomeoneCalling\r\n")
    return
  elif func == "":
    print("IS SOMEONE CALLING (-i, --isSomeoneCalling): Check if someone is trying to call the GSM module")

  # Pick-up call
  if func in ("n", "pickupcall"):
    print("Pick up call (if someone is calling the GSM module)\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -n\r\n"
          +filename+" --pickUpCall\r\n")
    return
  elif func == "":
    print("PICK UP CALL (-n, --pickUpCall): Pick up (answer) call")

  # Send normal/special SMS/MMS
  if func in ("s", "sendsms"):
    print("Send SMS or MMS\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -s [phone number] [message]\r\n"
          +filename+" --sendSMS [phone number] [message]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -s +33601234567 \"Hello!\r\nNew line!\"\r\n"
          +filename+" --sendSMS 0601234567 \"Hello!\r\nNew line!\"\r\n")
    return
  elif func == "":
    print("SEND SMS OR MMS (-s, --sendSMS): Send SMS or MMS")

  # Send encoded SMS/MMS
  if func in ("m", "sendencodedsms"):
    print("Send encoded SMS or MMS\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -m [phone number] [message in hexa]\r\n"
          +filename+" --sendEncodedSMS [phone number] [message in hexa]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -m +33601234567 48656C6C6F21\r\n"
          +filename+" --sendEncodedSMS 0601234567 48656C6C6F21\r\n")
    return
  elif func == "":
    print("SEND ENCODED SMS OR MMS (-m, --sendEncodedSMS): Send encoded SMS or MMS")

  # Send text mode SMS (dependant of GSM)
  if func in ("e", "sendtextmodesms"):
    print("Send SMS using Text Mode TC35 encoding (NOT RECOMMENDED)\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -e [phone number] [message]\r\n"
          +filename+" --sendTextModeSMS [phone number] [message]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -e +33601234567 \"Hello!\r\nNew line!\"\r\n"
          +filename+" --sendTextModeSMS 0601234567 \"Hello!\r\nNew line!\"\r\n")
    return
  elif func == "":
    print("SEND SMS WITH TEXT MODE (-e, --sendTextModeSMS): Send SMS using Text Mode TC35 encoding (NOT RECOMMENDED)")

  # Get SMS
  if func in ("g", "getsms"):
    print("Get SMS\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -g [sms type]\r\n"
          +filename+" --getSMS [sms type]\r\n"
          +"SMS Type: \""+str(GSMTC35.eSMS.ALL_SMS)+"\", \""
          +str(GSMTC35.eSMS.UNREAD_SMS)+"\" and \""
          +str(GSMTC35.eSMS.READ_SMS)+"\"\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -g \""+str(GSMTC35.eSMS.UNREAD_SMS)+"\"\r\n"
          +filename+" --getSMS \""+str(GSMTC35.eSMS.ALL_SMS)+"\"\r\n")
    return
  elif func == "":
    print("GET SMS (-g, --getSMS): Get SMS")

  # Get encoded SMS
  if func in ("f", "getencodedsms"):
    print("Get SMS\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -f [sms type]\r\n"
          +filename+" --getEncodedSMS [sms type]\r\n"
          +"SMS Type: \""+str(GSMTC35.eSMS.ALL_SMS)+"\", \""
          +str(GSMTC35.eSMS.UNREAD_SMS)+"\" and \""
          +str(GSMTC35.eSMS.READ_SMS)+"\"\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -f \""+str(GSMTC35.eSMS.UNREAD_SMS)+"\"\r\n"
          +filename+" --getEncodedSMS \""+str(GSMTC35.eSMS.ALL_SMS)+"\"\r\n")
    return
  elif func == "":
    print("GET ENCODED SMS (-f, --getEncodedSMS): Get SMS in Hexadecimal without decoding")

  # Get Text mode SMS
  if func in ("j", "gettextmodesms"):
    print("Get SMS\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -j [sms type]\r\n"
          +filename+" --getTextModeSMS [sms type]\r\n"
          +"SMS Type: \""+str(GSMTC35.eSMS.ALL_SMS)+"\", \""
          +str(GSMTC35.eSMS.UNREAD_SMS)+"\" and \""
          +str(GSMTC35.eSMS.READ_SMS)+"\"\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -j \""+str(GSMTC35.eSMS.UNREAD_SMS)+"\"\r\n"
          +filename+" --getTextModeSMS \""+str(GSMTC35.eSMS.ALL_SMS)+"\"\r\n")
    return
  elif func == "":
    print("GET TEXT MODE SMS (-j, --getTextModeSMS): Get SMS using Text Mode TC35 decoding (NOT RECOMMENDED)")

  # Delete SMS
  if func in ("d", "deletesms"):
    print("Delete SMS\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -d [sms type]\r\n"
          +filename+" --deleteSMS [sms type]\r\n"
          +"SMS Type: Index of the SMS (integer), \""+str(GSMTC35.eSMS.ALL_SMS)
          +"\", \""+str(GSMTC35.eSMS.UNREAD_SMS)+"\" and \""
          +str(GSMTC35.eSMS.READ_SMS)+"\"\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -d \""+str(GSMTC35.eSMS.UNREAD_SMS)+"\"\r\n"
          +filename+" --deleteSMS \""+str(GSMTC35.eSMS.ALL_SMS)+"\"\r\n")
    return
  elif func == "":
    print("DELETE SMS (-d, --deleteSMS): Delete SMS")

  # Get information
  if func in ("o", "information"):
    print("Get information from module and network (IMEI, clock, operator, ...)\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -o\r\n"
          +filename+" --information")
    return
  elif func == "":
    print("GET INFORMATION (-o, --information): Get information from module and network")

  # Use case examples:
  if func == "":
    example_port = "COMx"
    for p in list(serial.tools.list_ports.comports()):
      if p.device:
        example_port = str(p.device)
        break
    print("\r\n"
          +"Some examples (if serial port is '"+example_port+"' and sim card pin is '1234'):\r\n"
          +" - Call someone: "+filename+" --serialPort "+example_port+" --pin 1234 --call +33601234567\r\n"
          +" - Hang up call: "+filename+" --serialPort "+example_port+" --pin 1234 --hangUpCall\r\n"
          +" - Pick up call: "+filename+" --serialPort "+example_port+" --pin 1234 --pickUpCall\r\n"
          +" - Send SMS/MMS: "+filename+" --serialPort "+example_port+" --pin 1234 --sendSMS +33601234567 \"Hello you!\r\nNew line :)\"\r\n"
          +" - Send encoded SMS/MMS: "+filename+" --serialPort "+example_port+" --pin 1234 --sendEncodedSMS +33601234567 48656C6C6F21\r\n"
          +" - Get all SMS (decoded): "+filename+" --serialPort "+example_port+" --pin 1234 --getSMS \""+str(GSMTC35.eSMS.ALL_SMS)+"\"\r\n"
          +" - Get all SMS (encoded): "+filename+" --serialPort "+example_port+" --pin 1234 --getEncodedSMS \""+str(GSMTC35.eSMS.ALL_SMS)+"\"\r\n"
          +" - Delete all SMS: "+filename+" --serialPort "+example_port+" --pin 1234 --deleteSMS \""+str(GSMTC35.eSMS.ALL_SMS)+"\"\r\n"
          +" - Get information: "+filename+" --serialPort "+example_port+" --pin 1234 --information"+"\"\r\n"
          +" - You can have a lot more information on how commands are performed using '--debug' command"+"\"\r\n"
          +" - You can hide debug, warning and error information using '--nodebug' command")

    print("\r\nList of available serial ports:")
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
      print(p)


################################# MAIN FUNCTION ###############################
def main(parsed_args = sys.argv[1:]):
  """Shell GSM utility function"""

  baudrate = 115200
  serial_port = ""
  pin = ""
  puk = ""
  pin2 = ""
  puk2 = ""

  # Get options
  try:
    opts, args = getopt.getopt(parsed_args, "hlactsdemniogfjzb:u:p:y:x:v:",
                               ["baudrate=", "serialPort=", "pin=", "puk=", "pin2=", "puk2=", "debug", "nodebug", "help",
                                "isAlive", "call", "hangUpCall", "isSomeoneCalling",
                                "pickUpCall", "sendSMS", "sendEncodedSMS", "sendTextModeSMS", "deleteSMS", "getSMS",
                                "information", "getEncodedSMS", "getTextModeSMS"])
  except getopt.GetoptError as err:
    print("[ERROR] "+str(err))
    __help()
    sys.exit(1)

  # Show help or add debug information (if requested)
  for o, a in opts:
    if o in ("-h", "--help"):
      if len(args) >= 1:
        __help(args[0])
      else:
        __help()
      sys.exit(0)
    elif o in ("-l", "--debug"):
      print("Debugging...")
      logger = logging.getLogger()
      logger.setLevel(logging.DEBUG)
    elif o in ("-z", "--nodebug"):
      logger = logging.getLogger()
      logger.setLevel(logging.CRITICAL)

  # Get parameters
  for o, a in opts:
    if o in ("-b", "--baudrate"):
      print("Baudrate: "+str(a))
      baudrate = a
      continue
    if o in ("-u", "--serialPort"):
      print("Serial port: "+a)
      serial_port = a
      continue
    if o in ("-p", "--pin"):
      print("PIN: "+a)
      pin = a
      continue
    if o in ("-y", "--puk"):
      print("PUK: "+a)
      puk = a
      continue
    if o in ("-x", "--pin2"):
      print("PIN2: "+a)
      pin2 = a
      continue
    if o in ("-v", "--puk2"):
      print("PUK2: "+a)
      puk2 = a
      continue

  if serial_port == "":
    for p in list(serial.tools.list_ports.comports()):
      if p.device:
        serial_port = str(p.device)
        logging.warning("Using first found serial port ("+serial_port+"), specify serial port if this one is not working...")
        break
    if serial_port == "":
      print("No specified serial port (and none found)...\r\n")
      __help()
      sys.exit(1)

  # Initialize GSM
  gsm = GSMTC35()
  is_init = gsm.setup(_port=serial_port, _baudrate=baudrate, _pin=pin, _puk=puk, _pin2=pin2, _puk2=puk2)
  print("GSM init with serial port {} and baudrate {}: {}".format(serial_port, baudrate, is_init))
  if (not is_init):
    print("[ERROR] You must configure the serial port (and the baudrate), use '-h' to get more information.")
    print("[HELP] List of available serial ports:")
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
      print("[HELP] "+str(p))
    sys.exit(2)

  # Be sure PIN(2)/PUK(2) are not needed
  req_pin_status, required_pin = gsm.getPinStatus()
  if not(req_pin_status) or (required_pin != GSMTC35.eRequiredPin.READY):
    if len(required_pin) > 0:
      print("[ERROR] "+str(required_pin)+" is needed")
    else:
      print("[ERROR] Failed to check PIN status")
    sys.exit(2)
  else:
    print("PIN and PUK not needed")

  # Launch requested command
  for o, a in opts:
    if o in ("-a", "--isAlive"):
      is_alive = gsm.isAlive()
      print("Is alive: {}".format(is_alive))
      if is_alive:
        sys.exit(0)
      sys.exit(2)

    elif o in ("-c", "--call"):
      if len(args) > 0:
        if args[0] != "":
          hidden = False
          if len(args) > 1:
            if (args[1].lower() == "true") or args[1] == "1":
              hidden = True
          if hidden:
            print("Calling "+args[0]+" in invisible mode...")
          else:
            print("Calling "+args[0]+" in normal mode...")

          if len(args) > 2:
            result = gsm.call(args[0], hidden, int(args[2]))
          else:
            result = gsm.call(args[0], hidden)
          print("Call picked up: "+str(result))
          if result:
            sys.exit(0)
          sys.exit(2)
        else:
          print("[ERROR] You must specify a valid phone number")
      else:
        print("[ERROR] You must specify a phone number to call")
        sys.exit(2)

    elif o in ("-t", "--hangUpCall"):
      print("Hanging up call...")
      result = gsm.hangUpCall()
      print("Hang up call: "+str(result))
      if result:
        sys.exit(0)
      sys.exit(2)

    elif o in ("-s", "--sendSMS"):
      if len(args) < 2:
        print("[ERROR] You need to specify the phone number and the message")
        sys.exit(1)
      msg = args[1]
      # Python2.7-3 compatibility:
      try:
        msg = args[1].encode().decode('utf-8')
      except (AttributeError, UnicodeEncodeError, UnicodeDecodeError):
        pass
      print("SMS sent: "+str(gsm.sendSMS(str(args[0]), msg)))
      sys.exit(0)

    elif o in ("-m", "--sendEncodedSMS"):
      if len(args) < 2:
        print("[ERROR] You need to specify the phone number and the message")
        sys.exit(1)
      try:
        decoded_content = bytearray.fromhex(args[1]).decode('utf-8')
      except (AttributeError, UnicodeEncodeError, UnicodeDecodeError):
        print("[ERROR] Failed to decode (in UTF-8) your hexadecimal encoded message")
        sys.exit(1)
      print("SMS encoded sent: "+str(gsm.sendSMS(str(args[0]), decoded_content)))
      sys.exit(0)

    elif o in ("-e", "--sendTextModeSMS"):
      if len(args) < 2:
        print("[ERROR] You need to specify the phone number and the message")
        sys.exit(1)
      msg = args[1]
      # Python2.7-3 compatibility:
      try:
        msg = args[1].encode().decode('utf-8')
      except AttributeError:
        pass
      print("SMS sent using Text Mode: "+str(gsm.sendSMS(str(args[0]), msg, True)))
      sys.exit(0)

    elif o in ("-d", "--deleteSMS"):
      if len(args) < 1:
        print("[ERROR] You need to specify the type of SMS to delete")
        print("[ERROR] Possible values: index of the SMS, \""+str(GSMTC35.eSMS.ALL_SMS)+"\", \""
              +str(GSMTC35.eSMS.UNREAD_SMS)+"\" and \""+str(GSMTC35.eSMS.READ_SMS)+"\"")
        sys.exit(1)
      print("SMS deleted: "+str(gsm.deleteSMS(str(args[0]))))
      sys.exit(0)

    elif o in ("-g", "--getSMS"):
      if len(args) < 1:
        print("[ERROR] You need to specify the type of SMS to get")
        print("[ERROR] Possible values: \""+str(GSMTC35.eSMS.ALL_SMS)+"\", \""
              +str(GSMTC35.eSMS.UNREAD_SMS)+"\" and \""+str(GSMTC35.eSMS.READ_SMS)+"\"")
        sys.exit(1)
      received_sms = gsm.getSMS(str(args[0]))
      print("List of SMS:")
      for sms in received_sms:
        multipart = ""
        if "header_multipart_ref_id" in sms and "header_multipart_nb_of_part" in sms and "header_multipart_current_part_nb" in sms:
          multipart = ", multipart '" + str(sms["header_multipart_ref_id"]) + "' (" + str(sms["header_multipart_current_part_nb"]) + "/" + str(sms["header_multipart_nb_of_part"]) + ")"
        try:
          print(str(sms["phone_number"])+" (id " +str(sms["index"])+", "
                +str(sms["status"])+", "+str(sms["date"])+" "+str(sms["time"])+str(multipart)
                +"): "+str(sms["sms"]))
        except UnicodeEncodeError:
          logging.warning("Can't display SMS content as unicode, displaying it as utf-8")
          print(str(sms["phone_number"])+" (id " +str(sms["index"])+", "
                +str(sms["status"])+", "+str(sms["date"])+" "+str(sms["time"])+str(multipart)
                +"): "+str(sms["sms"].encode("utf-8")))
      sys.exit(0)

    elif o in ("-f", "--getEncodedSMS"):
      if len(args) < 1:
        print("[ERROR] You need to specify the type of SMS to get")
        print("[ERROR] Possible values: \""+str(GSMTC35.eSMS.ALL_SMS)+"\", \""
              +str(GSMTC35.eSMS.UNREAD_SMS)+"\" and \""+str(GSMTC35.eSMS.READ_SMS)+"\"")
        sys.exit(1)
      received_sms = gsm.getSMS(str(args[0]), False)
      print("List of encoded SMS:")
      for sms in received_sms:
        if "charset" in sms:
          charset = sms["charset"]
        else:
          charset = "unknown"
        res = str(sms["phone_number"])+" (id " +str(sms["index"])+", " \
              +str(sms["status"])+", "+str(charset)+", "+str(sms["date"])+" "+str(sms["time"])
        if "header_iei" in sms and "header_ie_data" in sms:
          res = res + ", header '" + str(sms["header_iei"]) + "' with data: '" + str(sms["header_ie_data"])+"'"
        if "header_multipart_ref_id" in sms and "header_multipart_nb_of_part" in sms and "header_multipart_current_part_nb" in sms:
          res = res + ", multipart '" + str(sms["header_multipart_ref_id"]) + "' (" + str(sms["header_multipart_current_part_nb"]) + "/" + str(sms["header_multipart_nb_of_part"]) + ")"
        print(res+"): "+str(sms["sms_encoded"]))
      sys.exit(0)

    elif o in ("-j", "--getTextModeSMS"):
      if len(args) < 1:
        print("[ERROR] You need to specify the type of SMS to get")
        print("[ERROR] Possible values: \""+str(GSMTC35.eSMS.ALL_SMS)+"\", \""
              +str(GSMTC35.eSMS.UNREAD_SMS)+"\" and \""+str(GSMTC35.eSMS.READ_SMS)+"\"")
        sys.exit(1)
      received_sms = gsm.getSMS(str(args[0]), False, True)
      print("List of text mode SMS:")
      for sms in received_sms:
        print(str(sms["phone_number"])+" (id " +str(sms["index"])+", "
              +str(sms["status"])+", "+str(sms["date"])+" "+str(sms["time"])
              +"): "+str(sms["sms"]))
      sys.exit(0)

    elif o in ("-n", "--pickUpCall"):
      print("Picking up call...")
      print("Pick up call: "+str(gsm.pickUpCall()))
      sys.exit(0)

    elif o in ("-i", "--isSomeoneCalling"):
      result = gsm.isSomeoneCalling()
      print("Is someone calling: "+str(result))
      sys.exit(0)

    elif o in ("-o", "--information"):
      if not gsm.isAlive():
        print("GSM module is not alive, can't get information")
        sys.exit(2)
      print("Is module alive: True")
      print("GSM module Manufacturer ID: "+str(gsm.getManufacturerId()))
      print("GSM module Model ID: "+str(gsm.getModelId()))
      print("GSM module Revision ID: "+str(gsm.getRevisionId()))
      print("Product serial number ID (IMEI): "+str(gsm.getIMEI()))
      print("International Mobile Subscriber Identity (IMSI): "+str(gsm.getIMSI()))
      print("Current operator: "+str(gsm.getOperatorName()))
      sig_strength = gsm.getSignalStrength()
      if sig_strength != -1:
        print("Signal strength: "+str(sig_strength)+"dBm")
      else:
        print("Signal strength: Wrong value")
      print("Date from internal clock: "+str(gsm.getDateFromInternalClock()))
      print("Last call duration: "+str(gsm.getLastCallDuration())+"sec")

      list_operators = gsm.getOperatorNames()
      operators = ""
      for operator in list_operators:
        if operators != "":
          operators = operators + ", "
        operators = operators + operator
      print("List of stored operators: "+operators)

      call_state, phone_number = gsm.getCurrentCallState()
      str_call_state = ""
      if call_state == GSMTC35.eCall.NOCALL:
        str_call_state = "No call"
      elif call_state == GSMTC35.eCall.ACTIVE:
        str_call_state = "Call in progress"
      elif call_state == GSMTC35.eCall.HELD:
        str_call_state = "Held call"
      elif call_state == GSMTC35.eCall.DIALING:
        str_call_state = "Dialing in progress"
      elif call_state == GSMTC35.eCall.ALERTING:
        str_call_state = "Alerting"
      elif call_state == GSMTC35.eCall.INCOMING:
        str_call_state = "Incoming call (waiting you to pick it up)"
      elif call_state == GSMTC35.eCall.WAITING:
        str_call_state = "Waiting other phone to pick-up"
      else:
        str_call_state = "Can't get the state"

      if phone_number != "":
        print("Call status: "+str(str_call_state)+" (phone number: "+str(phone_number)+")")
      else:
        print("Call status: "+str(str_call_state))
      print("Neighbour cells: "+str(gsm.getNeighbourCells()))
      print("Accumulated call meter: "+str(gsm.getAccumulatedCallMeter())+" home units")
      print("Accumulated call meter max: "+str(gsm.getAccumulatedCallMeterMaximum())+" home units")
      print("Is GSM module temperature critical: "+str(gsm.isTemperatureCritical()))
      print("Is GSM module in sleep mode: "+str(gsm.isInSleepMode()))

      sys.exit(0)
  print("[ERROR] You must call one action, use '-h' to get more information.")
  sys.exit(1)

if __name__ == '__main__':
  main()
