# GSM TC35 Python library

## What is it?

This python library is designed to be integrated in python or shell projects using TC35 module.
It is multi-platform and compatible with python 2.7+ and 3+.

Most functionalities should work with other GSM module using AT commands.


<img src="TC35_module.jpg" width="800">


## Functionalities

Non-exhaustive list of GSMTC35 class functionalities:
  - Check PIN state
  - Enter/Lock/Unlock/Change PIN
  - Send/Receive/Delete SMS
  - Call/Re-call (possible to hide phone number)
  - Hang-up/Pick-up call
  - Get/Add/Delete phonebook entries (phone numbers + contact names)
  - Check if someone is calling
  - Check if there is a call in progress
  - Check call status (call/ringing/...) and get the associated phone number
  - Get last call duration
  - Check if module is alive
  - Switch off
  - Reboot
  - Check sleep mode status
  - Get IDs (manufacturer, model, revision, IMEI, IMSI)
  - Set module to manufacturer state
  - Get the current used operator
  - Get the signal strength (in dBm)
  - Set and get the date from the module internal clock
  - Get list of operators
  - Get list of neighbour cells
  - Get accumulated call meter and accumulated call meter max (in home units)
  - Get temperature status
  - Change the baudrate mode

Non-exhaustive list of shell commands:
  - Send/Receive/Delete SMS
  - Call
  - Hang-up/Pick-up call
  - Show information (PIN status, operator, signal strength, last call duration, manufacturer/model/revision ID, IMEI, IMSI, date from internal clock, call status and associated phone number, operator list, neighbour cells, accumulated call meter (max), temperature status, sleep mode status)


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

# Get SMS
GSMTC35.py --serialPort COM4 --pin 1234 --getSMS "ALL"

# Delete SMS
GSMTC35.py --serialPort COM4 --pin 1234 --deleteSMS "ALL"

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
pin = 1234

# Mandatory step
if not gsm.setup(_port="COM3", _pin=pin):
  print("Setup error")
  sys.exit(2)

if not gsm.isAlive():
  print("The GSM module is not responding...")
  sys.exit(2)

# Enter PIN (already specified in setup())
#if gsm.isPinRequired():
#  if not gsm.enterPin(pin):
#    print("Wrong PIN")
#    sys.exit(2)

# Send SMS
print("SMS sent: "+str(gsm.sendSMS("+33601234567", "Hello from python script!!!")))

# Show all received SMS
rx_sms = gsm.getSMS(GSMTC35.eSMS.ALL_SMS)
print("List of SMS:")
for sms in rx_sms:
  print(str(sms["phone_number"])+" (id " +str(sms["index"])+", "
        +str(sms["status"])+", "+str(sms["date"])+" "+str(sms["time"])
        +"): "+str(sms["sms"]))

# Delete all received SMS
print("Delete all SMS: "+str(gsm.deleteSMS(GSMTC35.eSMS.ALL_SMS)))

# Call
print("Called: "+str(gsm.call(phone_number="0601234567", hide_phone_number=False)))

# Re-call same number
print("Re-called: "+str(gsm.reCall()))

# Last call duration
print("Last call duration: "+str(gsm.getLastCallDuration()))

# Pick up call
print("Picked up: "+str(gsm.pickUpCall()))

# Hang up call
print("Hanged up: "+str(gsm.hangUpCall()))

# Add entry in GSM module phonebook
print("Added contact to GSM module phonebook: "
      +str(gsm.addEntryToPhonebook("0600000000", "Dummy contact",
                                   GSMTC35.ePhonebookType.GSM_MODULE)))

# Get entry list in GSM module phonebook:
entries = gsm.getPhonebookEntries(GSMTC35.ePhonebookType.GSM_MODULE)
print("List of stored contacts:")
for entry in entries:
  print(str(entry['index']+": "+str(entry['contact_name'])+" -> "+str(entry['phone_number'])))

# Delete all GSM phonebook entries:
print("Deleted all contact from GSM module phonebook: "
      +str(gsm.agsm.deleteAllEntriesFromPhonebook(GSMTC35.ePhonebookType.GSM_MODULE)))

# Check if someone is calling
print("Incoming call: "+str(gsm.isSomeoneCalling()))

# Check if there is a call in progress
print("Call in progress: "+str(gsm.isCallInProgress()))

# Check if someone is calling, if a call is in progress, dialing and the associated phone number
call_state, phone_number = gsm.getCurrentCallState()
print("Call status: "+str(call_state)+" (associated phone number: "+str(phone_number)+")")
print("(-1=No call, 0=Call active, 1=Held, 2=Dialing, 3=Alerting, 4=Incoming, 5=Waiting)")

# Edit SIM Pin
print("SIM Locked: "+str(gsm.lockSimPin(pin)))
print("SIM Unlocked: "+str(gsm.unlockSimPin(pin)))
new_pin = pin # (Just for test)
print("SIM Pin changed: "+str(gsm.changePin(pin, new_pin)))

# Set module clock to current date
print("Clock set: "+gsm.setInternalClockToCurrentDate())

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
print("List of operators: "+str(gsm.getOperatorNames()))
print("Neighbour cells: "+str(gsm.getNeighbourCells()))
print("Accumulated call meter: "+str(gsm.getAccumulatedCallMeter())+" home units")
print("Accumulated call meter max: "+str(gsm.getAccumulatedCallMeterMaximum())+" home units")
print("Is temperature critical: "+str(gsm.isTemperatureCritical()))
print("Is in sleep mode: "+str(gsm.isInSleepMode()))

# Reboot (an init is needed to use gsm functions after such a call)
print("Reboot: "+str(gsm.reboot()))

# At the end, close connection with GSM module
gsm.close()
```


##TODO list

  - Add functionalities (class + command line):
    * [ENHANCEMENT] Add sleep mode (sleep and wake up with alarm/SMS/call/temperature)
    * [ENHANCEMENT] Add PUK support
    * [ENHANCEMENT] Add call forwarding support
    * [ENHANCEMENT] Add loudspeaker/microphone volume/mute support
    * [ENHANCEMENT] Add operator selection and preferred operator list support
    * [ENHANCEMENT] Add fax support (... maybe in 100 years)
  - [ENHANCEMENT] Add python demo forwarding all incoming SMS to specific email or phone number
  - [ENHANCEMENT] Add manifest and setup.py to install this library really fast
  - [ENHANCEMENT] Update the __init__.py file


## License

This project is under MIT license. This means you can use it as you want (just don't delete the library header).


## Contribute

If you want to add more examples or improve the library, just create a pull request with proper commit message and right wrapping.
