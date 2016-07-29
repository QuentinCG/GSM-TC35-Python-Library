# GSM TC35 Python library

## What is it?

This python library is designed to be integrated in python or shell projects using TC35 module.
It is multi-platform and compatible with python 2.7+ and 3+.

Most functionalities should work with other GSM module using AT commands.


<img src="device.png" width="400">


## Functionalities

Non-exhaustive list of GSMTC35 class functionalities:
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

Non-exhaustive list of shell commands:
  - Send SMS
  - Call
  - Hang up call
  - Pick up call
  - Show information (PIN status, operator, signal strength, last call duration, manufacturer/model/revision ID, IMEI, IMSI, date from internal clock)


## How to install (python script and shell)

  - Install Pyserial:
    * Solution 1: "pip install pyserial"
    * Solution 2: Download package at https://pypi.python.org/pypi/pyserial and use "python setup.py install" command)
  - Connect your GSM module to a serial port
  - Get the port name (you can find it out by calling GSMTC35.py without arguments)
  - Load your shell or python script


## How to use in shell

```shell
# Get help
GSMTC35.py -h

# Send SMS
GSMTC35.py --serialPort COM4 --pin 1234 --sendSMS +33601234567 "Hello from shell!"

# Call
GSMTC35.py --serialPort COM4 --pin 1234 --call +33601234567

# Hang up call
GSMTC35.py --serialPort COM4 --pin 1234 --hangUpCall

# Pick up call
GSMTC35.py --serialPort COM4 --pin 1234 --pickUpCall

# Show GSM module and network information
GSMTC35.py --serialPort COM4 --pin 1234 --information
```


## How to use in python script

Example of python script using this library:

```python
import sys
from GSMTC35 import GSMTC35

gsm = GSMTC35()

# Mandatory step
if not gsm.setup("COM3"):
  print("Setup error")
  sys.exit(2)

if not gsm.isAlive():
  print("The GSM module is not responding...")
  sys.exit(2)

# Enter PIN
if gsm.isPinRequired():
  if not gsm.enterPin("1234"):
    print("Wrong PIN")
    sys.exit(2)

# Send SMS
print("SMS sent: "+str(gsm.sendSMS("+33601234567", "Hello from python script!!!")))

# Call
print("Called: "+str(gsm.call("0601234567")))

# Re-call same number
print("Re-called: "+str(gsm.reCall()))

# Last call duration
print("Last call duration: "+str(gsm.getLastCallDuration()))

# Pick up call
print("Picked up: "+str(gsm.pickUpCall()))

# Hang up call
print("Hanged up: "+str(gsm.hangUpCall()))

# Check if someone is calling
print("Incoming call: "+str(gsm.isSomeoneCalling()))

# Check if there is a call in progress
print("Call in progress: "+str(gsm.isCallInProgress()))

# Set module clock to current date
print("Clock set: "+gsm.setCurrentDateToInternalClock())

# Show additional information
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
```


##TODO list

  - Add functionalities (class + command line):
    * [CRITICAL] Get phone number of incoming call and current call (in progress, not optimized at all)
    * [CRITICAL] Get {all/not read/read} SMS
    * [NORMAL] Delete {all/not read/read} SMS
    * [ENHANCEMENT] Get list of stored operators in the module
    * [ENHANCEMENT] Integrate sleep mode
  - Add manifest and setup.py to install this library really fast
  - Improve error handling (minimize waiting time when GSM module answers error value)
