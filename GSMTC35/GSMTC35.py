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
__copyright__ = "Copyright Quentin Comte-Gaz (2016)"
__python_version__ = "2.7+ and 3.+"
__version__ = "1.0 (2016/08/18)"
__status__ = "Usable for any project"

import serial, serial.tools.list_ports
import time, sys, getopt
import logging
import datetime

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

  class eSMS:
    ALL_SMS = "ALL"
    UNREAD_SMS = "REC UNREAD"
    READ_SMS = "REC READ"

  class eCall:
    NOCALL = -1
    ACTIVE = 0
    HELD = 1
    DIALING = 2
    ALERTING = 3
    INCOMING = 4
    WAITING = 5

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


  ############################ STANDALONE FUNCTIONS ############################
  @staticmethod
  def changeBaudrateMode(old_baudrate, new_baudrate, port, pin=-1,
                         parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                         bytesize=serial.EIGHTBITS):
    """Change baudrate mode (can be done only if GSM module is not currently used)

    Keyword arguments:
      old_baudrate -- (int) Baudrate value usable to communicate with the GSM module
      new_baudrate -- (int) New baudrate value to communicate with the GSM module
                            /!\ Use "0" to let the GSM module use "auto-baudrate" mode
      port -- (string) Serial port name of the GSM serial connection
      pin -- (string, optional) PIN number if locked
      parity -- (pySerial parity, optional) Serial connection parity (PARITY_NONE, PARITY_EVEN, PARITY_ODD PARITY_MARK, PARITY_SPACE)
      stopbits -- (pySerial stop bits, optional) Serial connection stop bits (STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO)
      bytesize -- (pySerial byte size, optional) Serial connection byte size (FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS)

    return: (bool) Baudrate changed
    """
    gsm = GSMTC35()
    if not gsm.setup(_port=port, _pin=pin, _baudrate=old_baudrate, _parity=parity,
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


  ################################### SETUP ####################################
  def setup(self, _port, _pin=-1, _baudrate=115200, _parity=serial.PARITY_NONE,
            _stopbits=serial.STOPBITS_ONE, _bytesize=serial.EIGHTBITS,
            _timeout_sec=2):
    """Initialize the class (can be launched multiple time if setup changed or module crashed)

    Keyword arguments:
      _port -- (string) Serial port name of the GSM serial connection
      _baudrate -- (int, optional) Baudrate of the GSM serial connection
      _pin -- (string, optional) PIN number if locked (not needed to do it now but would improve reliability)
      _parity -- (pySerial parity, optional) Serial connection parity (PARITY_NONE, PARITY_EVEN, PARITY_ODD PARITY_MARK, PARITY_SPACE)
      _stopbits -- (pySerial stop bits, optional) Serial connection stop bits (STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO)
      _bytesize -- (pySerial byte size, optional) Serial connection byte size (FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS)
      _timeout_sec -- (int, optional) Default timeout in sec for GSM module to answer commands

    return: (bool) Module initialized
    """
    # Close potential previous GSM session
    self.close()

    # Create new GSM session
    self.__timeout_sec = _timeout_sec
    self.__serial = serial.Serial(
                      port=_port,
                      baudrate=_baudrate,
                      parity=_parity,
                      stopbits=_stopbits,
                      bytesize=_bytesize,
                      timeout=_timeout_sec
                    )

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

      # Try to enter PIN if needed (May be needed for next commands):
      if self.isPinRequired():
        if int(_pin) >= 0:
          if not self.enterPin(_pin):
            logging.error("Invalid PIN \""+str(_pin)+"\" (YOU HAVE A MAXIMUM OF 3 TRY)")
            is_init = False
        else:
          logging.warning("Some initialization may not work without PIN activated")

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


  def close(self):
    """Close GSM session (free the GSM serial port)"""
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
        if (content in line) and len(line) > 0:
          return line
        if len(error_result) > 0 and (error_result == line):
          logging.error("GSM module returned error \""+str(error_result)+"\"")
          return ""
      # Wait 100ms if no data in the serial buffer
      time.sleep(.100)
    logging.error("Impossible to get line containing \""+str(content)+"\" on time")
    return ""


  def __sendLine(self, before, after=""):
    """Send line to the serial port as followed: {before}\r\n{after}

    Keyword arguments:
      before -- (string) Data to send before the end of line
      after -- (string) Data to send after the end of line
    """
    self.__serial.write("{}\r\n".format(before).encode())
    logging.debug("[OUT] "+str(before))
    if after != "":
      time.sleep(0.100)
      self.__serial.write(after.encode())
      logging.debug("[OUT] "+str(after))


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
    self.__sendLine(cmd, after)
    return self.__getNotEmptyLine(content, error_result, additional_timeout)


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
    self.__deleteAllRxData()
    self.__sendLine(cmd, after)

    val_result = []

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
    self.__sendLine(cmd, after)
    return self.__waitDataContains(result, error_result, additional_timeout)


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
      pass

    # Split last elements
    split_result = split_result[1].split(",")

    # Get the index_max
    if len(split_result) >= 1:
      try:
        index_max = int(split_result[0])
      except ValueError:
        # Index max is not correct, let's try to get other elements
        logging.warning("Impossible to get the phonebook max index (value error)")
        pass
    else:
      logging.warning("Impossible to get the phonebook max index (length error)")

    # Get max phone length
    if len(split_result) >= 2:
      try:
        index_max_phone_length = int(split_result[1])
      except ValueError:
        # Max phone length is not correct, let's try to get other elements
        logging.warning("Impossible to get the phonebook max phone length (value error)")
        pass
    else:
      logging.warning("Impossible to get the phonebook max phone length (length error)")

    # Get contact name length
    if len(split_result) >= 3:
      try:
        max_contact_name_length = int(split_result[2])
      except ValueError:
        # Max phone length is not correct, let's try to get other elements
        logging.warning("Impossible to get the phonebook max contact name length (value error)")
        pass
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

    return: (bool) Switch off successful
    """
    # Send request and get data
    result = self.__sendCmdAndCheckResult(cmd=GSMTC35.__BASE_AT+"^SMSO",
                                          result="MS OFF")
    # Delete the "OK" of the request from the buffer
    self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)
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

    return: ([{index=(int), phone_number=(string), contact_name=(string)}, ...])
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
  def sendSMS(self, phone_number, msg, network_delay_sec=5):
    """Send SMS to specific phone number

    Keyword arguments:
      phone_number -- (string) Phone number (can be local or international)
      msg -- (string) Message to send
      network_delay_sec -- (int) Network delay to add when waiting SMS to be send

    return: (bool) SMS sent
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CMGS=\""
                                        +phone_number+"\"",
                                        after=msg+GSMTC35.__CTRL_Z,
                                        additional_timeout=network_delay_sec)


  def getSMS(self, sms_type=eSMS.ALL_SMS, waiting_time_sec=5):
    """Get SMS

    Keyword arguments:
      sms_type -- (string) Type of SMS to get (possible values: GSMTC35.eSMS.ALL_SMS,
                           GSMTC35.eSMS.UNREAD_SMS or GSMTC35.eSMS.READ_SMS)
      waiting_time_sec -- (int, optional) Time to wait SMS to be displayed by GSM module

    return: ([{"index":, "status":, "phone_number":, "date":, "time":, "sms":},]) List of requested SMS (list of dictionaries)
            Explanation of dictionaries content:
              - index (int) Index of the SMS from the GSM module point of view
              - status (GSMTC35.eSMS) SMS type
              - phone_number (string) Phone number which send the SMS
              - date (string) Date SMS was received
              - time (string) Time SMS was received
              - sms (string) Content of the SMS
    """
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
    all_sms = []
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
      sms_type -- (string or int, optional) Type of SMS to delete (possible values:
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

    return: (string) Last call duration (format: %H:%M:%S, max: 9999:59:59)
    """
    call_duration = ""

    # Send the command to get the last call duration
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__BASE_AT+"^SLCD",
                                              content="^SLCD: ")

    # Get the call duration from the received line
    if result == "" or len(result) <= 7 or result[:7] != "^SLCD: ":
      logging.error("Command to get last call duration failed")
      return call_duration

    # Get the call duration
    call_duration = result[7:]

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

    return call_state, phone


  ################################ PIN FUNCTIONS ###############################
  def isPinRequired(self):
    """Check if the SIM card PIN is ready (not waiting PIN, PUK, ...)

    return: (bool) is SIM card PIN still needed to access phone functions
    """
    pin_required = not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CPIN?",
                                                    result="READY")

    # Delete last "OK" from buffer
    self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return pin_required


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
    sleeping = True

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


################################# HELP FUNCTION ################################
def __help(func="", filename=__file__):
  """Show help on how to use command line GSM module functions

  Keyword arguments:
    func -- (string, optional) Command line function requiring help, none will show all function
    filename -- (string, optional) File name of the python script implementing the commands
  """
  func = func.lower()

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
    print("BAUDRATE (-b, --baudrate): Specify serial baudrate for GSM module <-> master communication")

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
    print("SERIAL PORT (-u, --serialPort): Specify serial port for GSM module <-> master communication")

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
    print("PIN (-p, --pin): Specify SIM card PIN")

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
          +filename+" -c [phone number] [pick-up wait in sec (default: no wait)]\r\n"
          +filename+" --call [phone number] [pick-up wait in sec (default: no wait)]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -c +33601234567\r\n"
          +filename+" --call 0601234567 20\r\n"
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

  # Send SMS
  if func in ("s", "sendsms"):
    print("Send SMS\r\n"
          +"\r\n"
          +"Usage:\r\n"
          +filename+" -s [phone number] [message]\r\n"
          +filename+" --sendSMS [phone number] [message]\r\n"
          +"\r\n"
          +"Example:\r\n"
          +filename+" -s +33601234567 \"Hello!\"\r\n"
          +filename+" --sendSMS 0601234567 \"Hello!\"\r\n")
    return
  elif func == "":
    print("SEND SMS (-s, --sendSMS): Send SMS")

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
  if func in ("-o", "--information"):
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
    print("\r\n"
          +"Some examples (if serial port is 'COM4' and sim card pin is '1234'):\r\n"
          +" - Call someone: "+filename+" --serialPort COM4 --pin 1234 --call +33601234567\r\n"
          +" - Hang up call: "+filename+" --serialPort COM4 --pin 1234 --hangUpCall\r\n"
          +" - Pick up call: "+filename+" --serialPort COM4 --pin 1234 --pickUpCall\r\n"
          +" - Send SMS: "+filename+" --serialPort COM4 --pin 1234 --sendSMS +33601234567 \"Hello you!\"\r\n"
          +" - Get all SMS: "+filename+" --serialPort COM4 --pin 1234 --getSMS \""+str(GSMTC35.eSMS.ALL_SMS)+"\"\r\n"
          +" - Delete all SMS: "+filename+" --serialPort COM4 --pin 1234 --deleteSMS \""+str(GSMTC35.eSMS.ALL_SMS)+"\"\r\n"
          +" - Get information: "+filename+" --serialPort COM4 --pin 1234 --information")

    print("\r\nList of available serial ports:")
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
      print(p)


################################# MAIN FUNCTION ###############################
def main():
  """Shell GSM utility function"""

  #logger = logging.getLogger()
  #logger.setLevel(logging.WARNING)

  baudrate = 115200
  serial_port = ""
  pin = -1

  # Get options
  try:
    opts, args = getopt.getopt(sys.argv[1:], "hactsdgniob:u:p:",
                               ["baudrate=", "serialPort=", "pin=", "help",
                                "isAlive", "call", "hangUpCall", "isSomeoneCalling",
                                "pickUpCall", "sendSMS", "deleteSMS", "getSMS",
                                "information"])
  except getopt.GetoptError as err:
    print("[ERROR] "+str(err))
    __help()
    sys.exit(1)

  # Show help (if requested)
  for o, a in opts:
    if o in ("-h", "--help"):
      if len(args) >= 1:
        __help(args[0])
      else:
        __help()
      sys.exit(0)

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

  if serial_port == "":
    print("You need to specify the serial port...\r\n")
    __help()
    sys.exit(1)

  # Initialize GSM
  gsm = GSMTC35()
  is_init = gsm.setup(_port=serial_port, _baudrate=baudrate, _pin=pin)
  print("GSM init with serial port {} and baudrate {}: {}".format(serial_port, baudrate, is_init))
  if (not is_init):
    print("[ERROR] You must configure the serial port (and the baudrate), use '-h' to get more information.")
    print("[HELP] List of available serial ports:")
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
      print("[HELP] "+str(p))
    sys.exit(2)

  # Be sure PIN is initialized
  if gsm.isPinRequired():
    print("[ERROR] PIN is needed")
    sys.exit(2)
  else:
    print("PIN is not needed")

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
          print("Calling "+args[0]+"...")
          result = gsm.call(args[0])
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
      print("SMS sent: "+str(gsm.sendSMS(str(args[0]), str(args[1]))))
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
      print("Last call duration: "+str(gsm.getLastCallDuration()))

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
