#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  REST API to use the GSM module (in progress):
   - Are GSM module and PIN ready to work? (GET http://127.0.0.1:8080/api/ping)
   - Check call status (GET http://127.0.0.1:8080/api/call)
   - Call (POST http://127.0.0.1:8080/api/call with header data 'phone_number' and 'hide_phone_number')
   - Hang up call (DELETE http://127.0.0.1:8080/api/call)
   - Pick up call (PUT http://127.0.0.1:8080/api/call)
   - More to come soon...

  Requirement:
   - Install (pip install) 'flask', 'flask_restful' and 'flask-httpauth'

  TODO:
   - Add more API: SMS/MMS/Phonebook/Info/Reboot/...
   - Use HTTPS: https://blog.miguelgrinberg.com/post/running-your-flask-application-over-https
   - Use better authentification (basic-auth is not optimized, token based auth would be more secured): https://blog.miguelgrinberg.com/post/restful-authentication-with-flask
   - Have possibility to chose between authentification type (no auth, basic auth, token-based auth)
   - Use sleep mode ?
"""
__author__ = 'Quentin Comte-Gaz'
__email__ = "quentin@comte-gaz.com"
__license__ = "MIT License"
__copyright__ = "Copyright Quentin Comte-Gaz (2019)"
__python_version__ = "3.+"
__version__ = "0.1 (2019/10/06)"
__status__ = "Example in progress (not secured and not fully implemented)"


from flask import Flask, request
from flask_restful import Resource, Api
from flask_httpauth import HTTPBasicAuth

import logging

# Relative path to import GSMTC35 (not needed if GSMTC35 installed from pip)
import sys
sys.path.append("..")

from GSMTC35 import GSMTC35
import serial


# ---- Config ----
pin = "1234"
puk = "12345678"
port = "COM8"
http_port = 8080
http_prefix = "/api"
BASIC_AUTH_DATA = {
  "basic_user": "test"
}
use_debug = True

# ---- App base ----
app = Flask(__name__)
api = Api(app, prefix=http_prefix)

if use_debug:
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)

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

# ---- Base GSM getter function ----
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
    _hide_phone_number = request.headers.get('hide_phone_number', default = "false", type = str)
    if _hide_phone_number == None:
      return {"result": False, "error": "Please specify your phone number (phone_number)"}
    _hide_phone_number = _hide_phone_number.lower() == "true" or _hide_phone_number == "1"
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

api.add_resource(Call, '/call')
api.add_resource(Ping, '/ping')


# ---- Launch application ----
if __name__ == '__main__':
  app.run(port=http_port, debug=use_debug)
