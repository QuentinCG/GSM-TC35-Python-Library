#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  REST API to use the GSM module (in progress):
   - Are GSM module and PIN ready to work? (GET http://127.0.0.1:8080/api/ping)
   - Check call status (GET http://127.0.0.1:8080/api/call)
   - Call (POST http://127.0.0.1:8080/api/call with header data 'phone_number' and optional 'hide_phone_number')
   - Hang up call (DELETE http://127.0.0.1:8080/api/call)
   - Pick up call (PUT http://127.0.0.1:8080/api/call)
   - Get SMS/MMS (GET http://127.0.0.1:8080/api/sms with optional header data 'phone_number', 'after_timestamp' and 'limit')
   - Send SMS/MMS (POST http://127.0.0.1:8080/api/sms with header data 'phone_number', 'content' and optional 'is_content_in_hexa_format')
   - Delete SMS/MMS (DELETE http://127.0.0.1:8080/api/sms with optional header data 'id', 'phone_number', 'before_timestamp')
   - Get module date (GET http://127.0.0.1:8080/api/date)
   - Set module date to current date (POST http://127.0.0.1:8080/api/date)
   - Get module or SIM information (GET http://127.0.0.1:8080/api/info with header data 'request')

  Requirement:
   - Install (pip install) 'flask', 'flask_restful' and 'flask-httpauth', ['pyopenssl']
     (or `pip install -e ".[restapi]"` from root folder)

  TODO:
   - Get config as file parameters (using 'getopt') instead of hardcoded in file
   - Use better authentification (basic-auth is not optimized, token based auth would be more secured): https://blog.miguelgrinberg.com/post/restful-authentication-with-flask
   - Have possibility to chose between authentification type (no auth, basic auth, token-based auth)
"""
__author__ = 'Quentin Comte-Gaz'
__email__ = "quentin@comte-gaz.com"
__license__ = "MIT License"
__copyright__ = "Copyright Quentin Comte-Gaz (2019)"
__python_version__ = "3.+"
__version__ = "0.2 (2019/10/08)"
__status__ = "Can be used for test but not for production (not fully secured)"


from flask import Flask, request
from flask_restful import Resource, Api
from flask_httpauth import HTTPBasicAuth

from datetime import datetime
import time
import logging
import binascii
import serial

# Import our internal database helper
from internal_db import InternalDB

# Relative path to import GSMTC35 (not needed if GSMTC35 installed from pip)
import sys
sys.path.append("../..")

from GSMTC35 import GSMTC35


# ---- Config ----
pin = "1234"
puk = "12345678"
port = "COM8"
api_database_filename = "sms.db"
http_port = 8080
http_prefix = "/api"
BASIC_AUTH_DATA = {
  "basic_user": "test"
}
use_debug = True

# SSL
# - No certificate: None
# - Self signed certificate: 'adhoc'
# - Your own certificate: ('cert.pem', 'key.pem')
# WARNING: Use a certificate for production !
api_ssl_context = None


# ---- App base ----
if use_debug:
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)

app = Flask(__name__)
api = Api(app, prefix=http_prefix)

api_database = InternalDB(api_database_filename)

# ---- Authentification (basic-auth) ----
auth = HTTPBasicAuth()

@auth.verify_password
def verify(username, password):
  """Verify basic authentification credentials (confront to BASIC_AUTH_DATA)

  Keyword arguments:
    username -- (str) Username
    username -- (str) Password

  return: (bool) Access granted?
  """
  if not (username and password):
    return False

  return BASIC_AUTH_DATA.get(username) == password

# ---- Base functions ----
def getGSM():
  """Base function to get initialized GSM class

  return (bool, GSMTC35, string): success, GSM class, error explanation
  """
  gsm = GSMTC35.GSMTC35()

  try:
    if not gsm.isInitialized():
      if not gsm.setup(_port="COM8", _pin=pin, _puk=puk):
        return False, gsm, str("Failed to initialize GSM/SIM")

  except serial.serialutil.SerialException:
    return False, gsm, str("Failed to connect to GSM module")

  return True, gsm, str("")

def checkBoolean(value):
  """Return a bool from a string (or bool)"""
  if isinstance(value, bool):
    return value
  return str(value).lower() == "true" or str(value) == "1"

# ---- API class ----
class Ping(Resource):
  """Are GSM module and PIN ready to work?"""
  @auth.login_required
  def get(self):
    """Are GSM module and PIN ready to work? (GET)

    return (json):
      - (bool) 'result': Request worked?
      - (str) 'status': Are GSM module and PIN ready to work?
      - (str, optional) 'error': Error explanation if request failed
    """
    valid_gsm, gsm, error = getGSM()
    if valid_gsm:
      return {"result": True, "status": gsm.isAlive()}
    else:
      return {"result": False, "error": error}

class Date(Resource):
  """Get module internal date/Set module internal date to current date"""
  @auth.login_required
  def get(self):
    """Get module date as '%m/%d/%Y %H:%M:%S format' (GET)

    return (json):
      - (bool) 'result': Request worked?
      - (str) 'date': Module date
      - (str, optional) 'error': Error explanation if request failed
    """
    valid_gsm, gsm, error = getGSM()
    if valid_gsm:
      gsm_date = gsm.getDateFromInternalClock()
      if gsm_date != -1:
        return {"result": True, "date": gsm_date.strftime("%m/%d/%Y %H:%M:%S")}
      else:
        return {"result": False, "error": "Module failed to send date in time."}
    else:
      return {"result": False, "error": error}
  @auth.login_required
  def post(self):
    """Set module date to current computer date (POST)

    return (json):
      - (bool) 'result': Request sent?
      - (bool) 'status': Module date updated?
      - (str, optional) 'error': Error explanation if request failed
    """
    valid_gsm, gsm, error = getGSM()
    if valid_gsm:
      return {"result": True, "status": gsm.setInternalClockToCurrentDate()}
    else:
      return {"result": False, "error": error}

class Call(Resource):
  """Call/Get call status/Pick up call/Hang up call"""
  @auth.login_required
  def get(self):
    """Get current call state (GET)

    return (json):
      - (bool) 'result': Request worked?
      - (str) 'status': Current call state
      - (str, optional) 'error': Error explanation if request failed
    """
    valid_gsm, gsm, error = getGSM()
    if valid_gsm:
      phone_status, phone = gsm.getCurrentCallState()
      res = {"result": True, "status": GSMTC35.GSMTC35.eCallToString(phone_status)}
      if len(phone) > 0:
        res["phone"] = phone
      return res
    else:
      return {"result": False, "error": error}
  @auth.login_required
  def post(self):
    """Call specific phone number, possible to hide your phone (POST)

    Header should contain:
      - (str) 'phone_number': Phone number to call
      - (bool, optional, default: false) 'hide_phone_number': Hide phone number

    return (json):
      - (bool) 'result': Request worked?
      - (bool) 'status': Call in progress?
      - (str, optional) 'error': Error explanation if request failed
    """
    _phone_number = request.headers.get('phone_number', default = None, type = str)
    if _phone_number == None:
      return {"result": False, "error": "Please specify a phone number (phone_number)"}
    _hide_phone_number = request.headers.get('hide_phone_number', default = "false", type = str)
    _hide_phone_number = checkBoolean(_hide_phone_number)
    valid_gsm, gsm, error = getGSM()
    if valid_gsm:
      return {"result": True, "status": gsm.call(phone_number=_phone_number, hide_phone_number=_hide_phone_number)}
    else:
      return {"result": False, "error": error}
  @auth.login_required
  def put(self):
    """Pick-up call (PUT)

    return (json):
      - (bool) 'result': Request worked?
      - (bool) 'status': Pick-up worked?
      - (str, optional) 'error': Error explanation if request failed
    """
    valid_gsm, gsm, error = getGSM()
    if valid_gsm:
      return {"result": True, "status": gsm.pickUpCall()}
    else:
      return {"result": False, "error": error}
  @auth.login_required
  def delete(self):
    """Hang-up call (DELETE)

    return (json):
      - (bool) 'result': Request worked?
      - (bool) 'status': Hang-up worked?
      - (str, optional) 'error': Error explanation if request failed
    """
    valid_gsm, gsm, error = getGSM()
    if valid_gsm:
      return {"result": True, "status": gsm.hangUpCall()}
    else:
      return {"result": False, "error": error}

class Sms(Resource):
  """Send SMS/Get SMS/Delete SMS"""
  @auth.login_required
  def get(self):
    """Get SMS (GET)

    Header should contain:
      - (str, optional, default: All phone number) 'phone_number': Specific phone number to get SMS from
      - (int, optional, default: All timestamp) 'after_timestamp': Minimum timestamp (UTC) to get SMS from
      - (int, optional, default: No limit) 'limit': Maximum number of SMS to get

    return (json):
      - (bool) 'result': Request worked?
      - (list of sms) 'sms': List of all found SMS
      - (str, optional) 'error': Error explanation if request failed
    """
    _phone_number = request.headers.get('phone_number', default = None, type = str)
    _after_timestamp = request.headers.get('after_timestamp', default = None, type = int)
    _limit = request.headers.get('limit', default = None, type = int)
    valid_gsm, gsm, error = getGSM()
    if valid_gsm:
      # Get all SMS from GSM module
      all_gsm_sms = gsm.getSMS()
      if all_gsm_sms:
        # Insert all GSM module SMS into the database
        all_mms = []
        for gsm_sms in all_gsm_sms:
          _timestamp = int(time.mktime(datetime.strptime(str(str(gsm_sms['date']) + " " + str(gsm_sms['time'].split(' ')[0])), "%y/%m/%d %H:%M:%S").timetuple()))
          if ('header_multipart_ref_id' in gsm_sms) and ('header_multipart_current_part_nb' in gsm_sms) and ('header_multipart_nb_of_part' in gsm_sms):
            all_mms.append(gsm_sms)
          else:
            if not api_database.insertSMS(timestamp=_timestamp, received=True, phone_number=gsm_sms['phone_number'], content=gsm_sms['sms_encoded']):
              logging.warning("Failed to insert SMS into database")

        # Try to merge multipart SMS into MMS before storing them into the database
        while len(all_mms) > 0:
          ref_id = all_mms[0]['header_multipart_ref_id']
          nb_of_part = all_mms[0]['header_multipart_nb_of_part']
          _timestamp = int(time.mktime(datetime.strptime(str(str(all_mms[0]['date']) + " " + str(all_mms[0]['time'].split(' ')[0])), "%y/%m/%d %H:%M:%S").timetuple()))
          _phone_number = all_mms[0]['phone_number']
          parts = {}
          parts[int(all_mms[0]['header_multipart_current_part_nb'])] = all_mms[0]['sms_encoded']
          all_mms.remove(all_mms[0])
          all_sms_to_remove = []

          for sms in all_mms:
            if sms['header_multipart_ref_id'] == ref_id:
              parts[int(sms['header_multipart_current_part_nb'])] = sms['sms_encoded']
              all_sms_to_remove.append(sms)

          for sms_to_remove in all_sms_to_remove:
            all_mms.remove(sms_to_remove)

          full_msg = ""
          for current_part in range(nb_of_part):
            try:
              full_msg += parts[current_part+1]
            except KeyError:
              logging.warning("Missing part of the MMS... Missing part may be received later and will be stored as an other SMS!")

          if not api_database.insertSMS(timestamp=_timestamp, received=True, phone_number=_phone_number, content=full_msg):
            logging.warning("Failed to insert SMS into database")

        # Delete all SMS from the module (because they are stored in the database)
        gsm.deleteSMS()
      # Return all SMS following the right pattern
      res, all_db_sms = api_database.getSMS(phone_number=_phone_number, after_timestamp=_after_timestamp, limit=_limit)
      if res:
        return {"result": True, "sms": all_db_sms}
      else:
        return {"result": False, "error": "Failed to get SMS from database"}
    else:
      return {"result": False, "error": error}
  @auth.login_required
  def post(self):
    """Send SMS (POST)

    Header should contain:
      - (str) 'phone_number': Phone number to send the SMS
      - (str) 'content': Content of the SMS (in utf-8 or hexa depending on other parameters)
      - (bool, optional, default: False) 'is_content_in_hexa_format': Is content in hexadecimal format?

    return (json):
      - (bool) 'result': Request worked?
      - (bool) 'status': SMS sent?
      - (str, optional) 'error': Error explanation if request failed
    """
    _phone_number = request.headers.get('phone_number', default = None, type = str)
    if _phone_number == None:
      return {"result": False, "error": "Please specify a phone number (phone_number)"}
    _content = request.headers.get('content', default = None, type = str)
    if _content == None:
      return {"result": False, "error": "Please specify a SMS content (content)"}
    _is_in_hexa_format = request.headers.get('is_content_in_hexa_format', default = "false", type = str)
    _is_in_hexa_format = checkBoolean(_is_in_hexa_format)
    valid_gsm, gsm, error = getGSM()
    if valid_gsm:
      if _is_in_hexa_format:
        try:
          _content = bytearray.fromhex(_content).decode('utf-8')
        except (AttributeError, UnicodeEncodeError, UnicodeDecodeError):
          return {"result": False, "error": "Failed to decode content"}
      status_send_sms = gsm.sendSMS(_phone_number, _content)
      if status_send_sms:
        if not api_database.insertSMS(timestamp=int(time.time()), received=False, phone_number=str(_phone_number), content=str(binascii.hexlify(_content.encode()).decode())):
          logging.warning("Failed to insert sent SMS into the database")
      return {"result": True, "status": status_send_sms}
    else:
      return {"result": False, "error": error}
  @auth.login_required
  def delete(self):
    """Delete SMS (DELETE)

    Header should contain:
      - (int, optional, default: All ID) 'id': ID to delete
      - (str, optional, default: All phone numbers) 'phone_number': Phone number to delete
      - (int, optional, default: All timestamp) 'before_timestamp': Timestamp (UTC) before it should be deleted

    return (json):
      - (bool) 'result': Request worked?
      - (int) 'count': Number of deleted SMS
      - (str, optional) 'error': Error explanation if request failed
    """
    _id = request.headers.get('id', default = None, type = int)
    _phone_number = request.headers.get('phone_number', default = None, type = str)
    _before_timestamp = request.headers.get('before_timestamp', default = None, type = int)
    result, count_deleted = api_database.deleteSMS(sms_id=_id, phone_number=_phone_number, before_timestamp=_before_timestamp)
    if result:
      return {"result": True, "count": int(count_deleted)}
    else:
      return {"result": False, "error": "Failed to delete all SMS from database"}

class Info(Resource):
  """Get information on module or SIM"""
  @auth.login_required
  def get(self):
    """Get Information (GET)

    Header should contain:
      - (str) 'request': Request specific data:
                          - 'last_call_duration': Get last call duration (in sec)
                          - 'manufacturer': Get manufacturer ID
                          - 'model': Get model ID
                          - 'revision': Get revision ID
                          - 'IMEI': Get IMEI
                          - 'IMSI': Get IMSI
                          - 'sleep_mode_status': Check if module in sleep mode (True=sleeping, False=Not sleeping)
                          - 'current_used_operator': Get currently used operator
                          - 'signal_strength': Get the signal strength (in dBm)
                          - 'operators_list': Get list of operators
                          - 'neighbour_cells_list': Get list of neighbour cells
                          - 'accumulated_call_meter': Get accumulated call meter (in home units)
                          - 'max_accumulated_call_meter': Get max accumulated call meter (in home units)
                          - 'temperature_status': Get module temperature status (True=critical, False=OK)

    return (json):
      - (bool) 'result': Request worked?
      - (int, str, list) 'result': Result of the request (type depends on the request)
      - (str, optional) 'error': Error explanation if request failed
    """
    _request = request.headers.get('request', default = None, type = str)
    if _request == None:
      return {"result": False, "error": "'request' not specified"}

    valid_gsm, gsm, error = getGSM()
    if valid_gsm:
      # Execute the correct request
      _request = _request.lower()
      if _request == 'last_call_duration':
        call_duration = gsm.getLastCallDuration()
        if call_duration != -1:
          response = call_duration
        else:
          return {"result": False, "error": "Failed to get last call duration"}
      elif _request == 'manufacturer':
        response = str(gsm.getManufacturerId())
      elif _request == 'model':
        response = str(gsm.getModelId())
      elif _request == 'revision':
        response = str(gsm.getRevisionId())
      elif _request == 'imei':
        response = str(gsm.getIMEI())
      elif _request == 'imsi':
        response = str(gsm.getIMSI())
      elif _request == 'sleep_mode_status':
        response = gsm.isInSleepMode()
      elif _request == 'current_used_operator':
        response = str(gsm.getOperatorName())
      elif _request == 'signal_strength':
        sig_strength = gsm.getSignalStrength()
        if sig_strength != -1:
          response = sig_strength
        else:
          return {"result": False, "error": "Failed to get signal strength"}
      elif _request == 'operators_list':
        response = gsm.getOperatorNames()
      elif _request == 'neighbour_cells_list':
        response = gsm.getNeighbourCells()
      elif _request == 'accumulated_call_meter':
        acc = gsm.getAccumulatedCallMeter()
        if acc != -1:
          response = acc
        else:
          return {"result": False, "error": "Failed to get accumulated call meter"}
      elif _request == 'max_accumulated_call_meter':
        acc = gsm.getAccumulatedCallMeterMaximum()
        if acc != -1:
          response = acc
        else:
          return {"result": False, "error": "Failed to get max accumulated call meter"}
      elif _request == 'temperature_status':
        response = gsm.isTemperatureCritical()
      else:
        return {"result": False, "error": "Invalid request parameter"}

      return {"result": True, "response": response}
    else:
      return {"result": False, "error": error}

api.add_resource(Call, '/call')
api.add_resource(Ping, '/ping')
api.add_resource(Sms, '/sms')
api.add_resource(Date, '/date')
api.add_resource(Info, '/info')


# ---- Launch application ----
if __name__ == '__main__':
  app.run(port=http_port, ssl_context=api_ssl_context, debug=use_debug)
