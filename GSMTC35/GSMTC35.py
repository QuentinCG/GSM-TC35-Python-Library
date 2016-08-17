#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  GSM TC35 library

  call, receive call, send SMS, receive SMS, enter the PIN,

  It is also possible to use command line to easily use this class from
  shell (launch this python file with '-h' parameter to get more information).

  Non-exhaustive class functionality list:
    - Check PIN state and enter PIN
    - Send SMS
    - Call
    - Re-call
    - Hang up call
    - Pick up call
    - Check if someone is calling
    - Check if there is a call in progress
    - Get last call duration
    - Check if module is alive
    - Get IDs (manufacturer, model, revision, IMEI, IMSI)
    - Set module to manufacturer state
    - Switch off
    - Get the current used operator
    - Get the signal strength (in dBm)
    - Set and get the date from the module internal clock
"""
__author__ = 'Quentin Comte-Gaz'
__email__ = "quentin@comte-gaz.com"
__license__ = "MIT License"
__copyright__ = "Copyright Quentin Comte-Gaz (2016)"
__python_version__ = "2.7+ and 3.+"
__version__ = "0.1 (2016/07/29)"
__status__ = "Usable but no SMS reception yet"

import serial, serial.tools.list_ports
import time, sys, getopt

class GSMTC35:
  """GSM TC35 class

  Calling setup() function is necessary in order to make this class work properly
  If you don't know the serial port to use, call this script to show all of them:
  '''
  import serial, serial.tools.list_ports
  print(str(list(serial.tools.list_ports.comports())))
  '''
  """
  __BASE_AT = "AT"
  __NORMAL_AT = "AT+"
  __RETURN_OK = "OK"
  __RETURN_ERROR = "ERROR"
  __CTRL_Z = "\x1a"

  class eSMS:
    ALL_SMS = "ALL"
    UNREAD_SMS = "REC UNREAD"
    READ_SMS = "REC READ"

  def __init__(self):
    """Initialize the GSM module class with undefined serial connection"""
    self.__initialized = False
    self.__serial = serial.Serial()


  ################################### SETUP ####################################
  def setup(self, _port, _baudrate=115200, _parity=serial.PARITY_NONE,
            _stopbits=serial.STOPBITS_ONE, _bytesize=serial.EIGHTBITS,
            _timeout_sec=2):
    """Initialize the class (can be launched multiple time if setup changed or module crashed)

    Keyword arguments:
      _port -- (string) Serial port name of the GSM serial connection
      _baudrate -- (int, optional) Baudrate of the GSM serial connection
      _parity -- (pySerial parity, optional) Serial connection parity (PARITY_NONE, PARITY_EVEN, PARITY_ODD PARITY_MARK, PARITY_SPACE)
      _stopbits -- (pySerial stop bits, optional) Serial connection stop bits (STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO)
      _bytesize -- (pySerial byte size, optional) Serial connection byte size (FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS)
      _timeout_sec -- (int, optional) Default timeout in sec for GSM module to answer commands

    return: (bool) Module initialized
    """
    # Close potential previous GSM session
    self.__serial.close()

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
        print("[WARNING] Can't disable echo mode (ATE0 command)")
      # Show calling phone number
      #TODO: To Delete when phone number check optimized (wait until be sure code is working fine)
      if not self.__sendCmdAndCheckResult(GSMTC35.__NORMAL_AT+"CLIP=1"):
        print("[WARNING] Can't enable mode to show phone number when calling (CLIP command)")
      # Set to text mode
      if not self.__sendCmdAndCheckResult(GSMTC35.__NORMAL_AT+"CMGF=1"):
        print("[ERROR] Can't set module to text mode (CMGF command)")
        is_init = False
    self.__initialized = is_init
    if not self.__initialized:
      self.__serial.close()

    return self.__initialized


  ######################### INTERNAL UTILITY FUNCTIONS #########################
  def __readLine(self):
    """Read one line from the serial port (not blocking)

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
        break
    return line


  def __deleteAllRxData(self):
    """Delete all received data from the serial port"""
    bytesToRead = self.__serial.inWaiting()
    if bytesToRead <= 0:
      return
    self.__serial.read(bytesToRead)


  def __waitDataContains(self, content, error_result, additional_timeout=0):
    """Wait to receive specific data from the serial port

    Keyword arguments:
      content -- (string) Data to wait from the serial port
      error_result -- (string) Line meaning an error occured (sent by the module)
      additional_timeout -- (int) Additional time to wait the match (added with base timeout)

    return: (bool) Is data received before timeout (if \s error_result is received, False is returned)
    """
    start_time = time.time()
    while time.time() - start_time < self.__timeout_sec + additional_timeout:
      while self.__serial.inWaiting() > 0:
        line = self.__readLine()
        if content in line:
          return True
        if error_result == line:
          return False
      time.sleep(.100) # Wait 100ms if no data in the serial buffer
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
        if error_result == line:
          return ""
      time.sleep(.100) # Wait 100ms if no data in the serial buffer
    return ""


  def __sendLine(self, before, after=""):
    """Send line to the serial port as followed: {before}\r\n{after}

    Keyword arguments:
      before -- (string) Data to send before the end of line
      after -- (string) Data to send after the end of line
    """
    self.__serial.write("{}\r\n".format(before).encode())
    if after != "":
      time.sleep(0.100)
      self.__serial.write(after.encode())


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
      result -- (string, optional) Data to wait from the GSM module (all lines will be returned BEFORE the line containing {result})
      error_result -- (string) Line meaning an error occured (sent by the module)

    return: ([string,]) All lines without the end of line (empty if nothing received or if an error occured)
    """
    self.__deleteAllRxData()
    self.__sendLine(cmd, after)

    val_result = []
    while 1:
      current_line = self.__getNotEmptyLine("", error_result, additional_timeout)
      if current_line == "":
        return val_result
      if (result in current_line):
        return val_result
      elif (current_line == error_result):
        return []
      else:
        val_result.append(current_line)

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
      return operator

    # Send the command to get the operator name
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"COPS?",
                                              content="+COPS: ")
    if result == "":
      return operator

    #Check result:
    if len(result) > 8:
      if result[0:7] == "+COPS: ":
        # Get result without "+COPS: "
        result = result[7:]
        # Split remaining data from the line
        splited_list = result.split(",")
        if len(splited_list) >= 3:
          # Get the operator name (3th element from the list)
          operator = splited_list[2]
          # Delete first and last '"' from the name (if exist)
          operator_lengh = len(operator)
          if operator_lengh > 1:
            if operator[0] == '"':
              operator = operator[1:]
            operator_lengh = len(operator)
            if operator_lengh >= 1:
              if operator[operator_lengh-1] == '"':
                operator = operator[:operator_lengh-1]

    # Delete last "OK" from buffer
    if operator != "":
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return operator


  def getSignalStrength(self):
    """Get current signal strength in dBm
    Range: -113 to -51 dBm (other values are incorrect)

    return: (int) -1 if not valid, else signal strength in dBm
    """
    ### in dBm OR -1 if can't get info
    sig_strength = -1

    # Send the command to get the signal power
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CSQ",
                                              content="+CSQ: ")
    #Check result:
    if result == "":
      return sig_strength

    if len(result) > 7:
      if result[:6] == "+CSQ: ":
        result = result[6:]
        # Split remaining data from the line
        splited_list = result.split(",")
        if len(splited_list) >= 1:
          # Get the received signal strength (1st element)
          try:
            sig_strength = int(splited_list[0])
          except ValueError:
            pass

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

    for operator in operators:
      operator_name = ""
      if len(operator) > 8:
        if operator[:7] == "+COPN: ":
          operator = operator[7:]
          # Split remaining data from the line
          split_list = operator.split(",")
          if len(split_list) >= 2:
            # Get the operator name (2nd element)
            operator_name = split_list[1]
            operator_lengh = len(operator_name)
            if operator_lengh > 1:
              if operator_name[0] == '"':
                operator_name = operator_name[1:]
              operator_lengh = len(operator_name)
              if operator_lengh >= 1:
                if operator_name[operator_lengh-1] == '"':
                  operator_name = operator_name[:operator_lengh-1]
      if operator_name != "":
        result.append(operator_name)

    return result

  ############################### TIME FUNCTIONS ###############################
  def setCurrentDateToInternalClock(self):
    """Set the GSM module internal clock to current date

    return: (bool) Date successfully modified
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CCLK=\""
                                        +time.strftime("%d/%m/%y,%H:%M:%S")+"\"")


  def getDateFromInternalClock(self):
    """Get the date from the GSM module internal clock

    return: (string) Date (format: %d/%m/%y,%H:%M:%S)
    """
    date = ""

    # Send the command to get the date
    result = self.__sendCmdAndGetNotEmptyLine(cmd=GSMTC35.__NORMAL_AT+"CCLK?",
                                              content="+CCLK: ")
    if result == "":
      return date

    #Check result:
    if len(result) > 8:
      if result[:7] == "+CCLK: ":
        # Get result without "+CCLK: "
        date = result[7:]
        # Delete first and last '"' from the date (if exist)
        date_lengh = len(date)
        if date_lengh > 1:
          if date[0] == '"':
            date = date[1:]
          date_lengh = len(date)
          if date_lengh >= 1:
            if date[date_lengh-1] == '"':
              date = date[:date_lengh-1]

    # Delete last "OK" from buffer
    if date != "":
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return date


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


  def deleteSpecificSMS(self, index):
    """Delete SMS with specific index

    Keyword arguments:
      index -- (int) Index of the SMS to delete from the GSM module (can be found by reading SMS)

   Note: Even if this function is not done for that: On some device, GSMTC35.eSMS.ALL_SMS,
     GSMTC35.eSMS.UNREAD_SMS and GSMTC35.eSMS.READ_SMS may be used instead of
     \s index to delete multiple SMS at once (not working for GSMTC35).

    return: (bool) Delete successful
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CMGD="+str(index))


  ############################### CALL FUNCTIONS ###############################
  def hangUpCall(self):
    """Stop current call (hang up)

    return: (bool) Hang up is a success
    """
    result = self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CHUP")
    if not result:
      # Try to hang up with an other method if the previous one didn't work
      print("First method to hang up call failed...\r\nTrying an other...")
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


  def call(self, phone_number, waiting_time_sec=20):
    """Call {phone_number} and wait {waiting_time_sec} it's picked up (previous call will be terminated)

    WARNING: This function does not end the call:
      - If picked up: Call will finished once the other phone stops the call
      - If not picked up: Will leave a voice messaging of undefined time (depending on the other phone)

    Keyword arguments:
      phone_number -- (string) Phone number to call
      waiting_time_sec -- (int, optional) Blocking time in sec to wait a call to be picked up

    return: (bool) Call in progress
    """
    # Hang up is necessary in order to not have false positive
    #(sending an ATD command while a call is already in progress would return an "OK" from the GSM module)
    self.hangUpCall()
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__BASE_AT+"D"
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
    if result == "":
      return call_duration

    if len(result) > 7:
      if result[:7] == "^SLCD: ":
        call_duration = result[7:]

    # Delete last "OK" from buffer
    if call_duration != "":
      self.__waitDataContains(self.__RETURN_OK, self.__RETURN_ERROR)

    return call_duration

  # Development in progress
  """
  def getFirstIncomingPhoneNumber(self):
    # ONLY WHEN RINGING FOR NOW
    # TODO: MUST CHANGE THIS USING AT+CLCC --> +CLCC: 1,1,4,0,0,"+33604028611",145 <-- (call ringing)
    data = self.__getNotEmptyLine(content="CLIP", additional_timeout=0)
    # Example of "data" value: +CLIP: "+33601234567",145,,,,0
    index_begin_phone_number = data.find("\"")
    if index_begin_phone_number >= 0 and len(data) > index_begin_phone_number + 1:
      data = data[index_begin_phone_number+1:]
      index_end_phone_number = data.find("\"")
      if index_end_phone_number > 0:
        data = data[:index_end_phone_number]

    return data
  """


  ################################ PIN FUNCTIONS ###############################
  def isPinRequired(self):
    """Check if the SIM card PIN is ready (not waiting PIN, PUK, ...)

    return: (bool) is SIM card PIN still needed to access phone functions
    """
    return not self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CPIN?",
                                            result="READY")


  def enterPin(self, pin):
    """Enter the SIM card PIN to be able to call/receive call and send/receive SMS

    WARNING: This function may lock your SIM card if you try to enter more than
    3 wrong PIN numbers.

    Keyword arguments:
      pin -- (string) SIM card PIN

    return: (bool) PIN is correct
    """
    return self.__sendCmdAndCheckResult(cmd=GSMTC35.__NORMAL_AT+"CPIN="+pin)


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
          +" - Get information: "+filename+" --serialPort COM4 --pin 1234 --information")

    print("\r\nList of available serial ports:")
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
      print(p)


################################# MAIN FUNCTION ###############################
def main():
  """Shell GSM utility function"""

  baudrate = 115200
  serial_port = ""
  pin = ""

  # Get options
  try:
     opts, args = getopt.getopt(sys.argv[1:], "hactsniob:u:p:",
                                ["baudrate=", "serialPort=", "pin=", "help", "isAlive", "call",
                                 "hangUpCall", "isSomeoneCalling", "pickUpCall", "sendSMS", "information"])
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
  is_init = gsm.setup(_port=serial_port, _baudrate=baudrate)
  print("GSM init with serial port {} and baudrate {}: {}".format(serial_port, baudrate, is_init))
  if (not is_init):
    print("[ERROR] You must configure the serial port (and the baudrate), use '-h' to get more information.")
    print("[HELP] List of available serial ports:")
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
      print("[HELP] "+p)
    sys.exit(2)

  # Be sure PIN is initialized
  if gsm.isPinRequired():
    if pin != "":
      if not gsm.enterPin(pin):
        print("[ERROR] Pin not valid, be careful to not enter wrong PIN 3 times!")
        sys.exit(2)
    else:
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
      sys.exit(0)
  print("[ERROR] You must call one action, use '-h' to get more information.")
  sys.exit(1)

if __name__ == '__main__':
  main()
