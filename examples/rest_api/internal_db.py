#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  Helper to create/use SQLite database (insert/delete/get received/sent SMS)
"""

__author__ = 'Quentin Comte-Gaz'
__email__ = "quentin@comte-gaz.com"
__license__ = "MIT License"
__copyright__ = "Copyright Quentin Comte-Gaz (2019)"
__python_version__ = "3.+"
__version__ = "0.1 (2019/10/08)"
__status__ = "In progress"

import os
import sqlite3
import logging

class InternalDB():
  def __init__(self, db_filename):
    """Initialize the internal database class"""
    self.db_filename = db_filename
    self.createDatabaseIfNeeded()

  def createDatabaseIfNeeded(self):
    """Create the database needed for the class to work (created at init but can be called again if failed)

    return: (bool) Database created
    """
    # Create database only if not already exist
    if not os.path.exists(self.db_filename):
      # Create the database
      try:
        with sqlite3.connect(self.db_filename) as conn:
          logging.debug("Creating database at "+str(self.db_filename))
          schema = """CREATE TABLE sms (
                        id                INTEGER       PRIMARY KEY AUTOINCREMENT NOT NULL,
                        timestamp         INTEGER       NOT NULL,
                        received          BOOLEAN       NOT NULL,
                        phone_number      VARCHAR(30)   NOT NULL,
                        content           TEXT          NOT NULL
                      );
                   """
          conn.execute(schema)
      except sqlite3.OperationalError as e:
        logging.error("Failed to create database: "+str(e))
        return False

    self.initialized = True
    return True


  def insertSMS(self, timestamp, received, phone_number, content):
    """Insert SMS in the database

    Keyword arguments:
      timestamp -- (int) Timestamp of the SMS (when it was sent or received)
      received -- (bool) Was it a received SMS (True) or a sent SMS (False) ?
      phone_number -- (string) Phone number of the interlocutor
      content -- (string) SMS content

    return: (bool) SMS inserted in the database
    """
    if not self.initialized:
      logging.error("Class not initialized")
      return False

    try:
      with sqlite3.connect(self.db_filename) as conn:
        conn.execute("""
          INSERT INTO sms
            (timestamp, received, phone_number, content)
          VALUES (?, ?, ?, ?)""",
          (int(timestamp), bool(received), str(phone_number), str(content)))
    except ValueError as e:
      logging.error("Failed to prepare request: "+str(e))
      return False
    except sqlite3.OperationalError as e:
      logging.error("Failed to execute request: "+str(e))
      return False

    return True

  def deleteSMS(self, id=None, phone_number=None, before_timestamp=None):
    """Delete SMS from the database

    WARNING: If no parameters are specified, all SMS will be deleted from the database

    Keyword arguments:
      id -- (int, optional) ID of the SMS to delete
      phone_number -- (string, optional) Only phone number to delete
      before_timestamp -- (int, optional) Maximum timestamp

    return: (bool, int) Success, Number of deleted SMS
    """
    if not self.initialized:
      logging.error("Class not initialized")
      return False, 0

    try:
      with sqlite3.connect(self.db_filename) as conn:
        # Base request
        request = "DELETE FROM sms"
        params = []
        # Potential conditions
        if (id != None) or (phone_number != None) or (before_timestamp != None):
          request += " WHERE "
          if (id != None):
            request += " id = ?"
            params.append(int(id))
          if (phone_number != None):
            if len(params) > 0:
              request += " AND"
            request += " phone_number = ?"
            params.append(str(phone_number))
          if (before_timestamp != None):
            if len(params) > 0:
              request += " AND"
            request += " timestamp <= ?"
            params.append(int(before_timestamp))

        # Do the request
        return True, conn.execute(request, params).rowcount

    except ValueError as e:
      logging.error("Failed to prepare request: "+str(e))
      return False, []
    except sqlite3.OperationalError as e:
      logging.error("Failed to execute request: "+str(e))
      return False, []

    logging.error("Unknown error")
    return False, []

  def getSMS(self, phone_number=None, after_timestamp=None, limit=None):
    """Get SMS from the database

    Keyword arguments:
      phone_number -- (string, optional) Only phone number to get
      after_timestamp -- (int, optional) Minimum timestamp
      limit -- (int, optional) Max number of SMS to get (note: Not optimized since "ORDER BY" is not usable)

    return: (bool, [{},]) Success, all SMS (with 'id', 'timestamp', 'received', 'phone_number', 'content')
    """
    if not self.initialized:
      logging.error("Class not initialized")
      return False, []

    try:
      with sqlite3.connect(self.db_filename) as conn:
        # Base request
        request = "SELECT id, timestamp, received, phone_number, content FROM sms"
        params = []
        # Potential conditions
        if (phone_number != None) or (after_timestamp != None):
          request += " WHERE"
          if (phone_number != None):
            request += " phone_number = ?"
            params.append(str(phone_number))
          if (after_timestamp != None):
            if (phone_number != None):
              request += " AND"
            request += " timestamp >= ?"
            params.append(int(after_timestamp))
        # Potential limit
        if limit != None:
          request += " LIMIT ?"
          params.append(int(limit))
        # Order
        # Note: Order is not handled by default with sqlite3 package...
        #request += " ORDER BY timestamp"

        # Do the SQLite request
        cursor = conn.cursor()
        cursor.execute(request, params)

        # Fetch all SMS
        res = []
        for row in cursor.fetchall():
          id, timestamp, received, phone_number, content = row
          sms_data = {}
          sms_data["id"] = int(id)
          sms_data["timestamp"] = int(timestamp)
          sms_data["received"] = bool(received)
          sms_data["phone_number"] = str(phone_number)
          sms_data["content"] = str(content)
          res.append(sms_data)
        return True, res
    except ValueError as e:
      logging.error("Failed to prepare request: "+str(e))
      return False, []
    except sqlite3.OperationalError as e:
      logging.error("Failed to execute request: "+str(e))
      return False, []

    logging.error("Unknown error")
    return False, []

# ---- Launch example of use if script executed directly ----
if __name__ == '__main__':
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)

  logging.debug("This is an example of use of the internal DB class:")

  logging.debug("---Creating the database (if doesn't already exist)---")
  internal_db = InternalDB("test.db")

  logging.debug("---Inserting dummy SMS in the database---")
  res = internal_db.insertSMS(timestamp=5, received=True, phone_number="+33601020304", content="48657920796F752021")\
        and internal_db.insertSMS(timestamp=6, received=True, phone_number="+33601020304", content="48657920796F752021")
  if not res:
    logging.warning("Failed to insert SMS")

  logging.debug("---Reading all SMS from the database---")
  res, data = internal_db.getSMS()#phone_number="+33601020304", after_timestamp=5, limit=1)
  if not res:
    logging.warning("Failed to read all SMS from the database, we will not try to delete SMS then...")
  else:
    logging.debug("All SMS:\n"+str(data))

    logging.debug("---Deleting first found SMS from the database---")
    res, number_of_deleted_sms = internal_db.deleteSMS(id=int(data[0]["id"]))#phone_number="+33601020304", before_timestamp=5)
    if not res:
      logging.warning("Failed to delete SMS")
    else:
      logging.debug("Deleted "+str(number_of_deleted_sms)+" SMS")
