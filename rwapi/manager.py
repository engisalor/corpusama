import ast
import numpy as np
import time
import requests
import json
import pandas as pd
import yaml
import sqlite3 as sql
import pathlib
import logging
from logging.handlers import TimedRotatingFileHandler


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")

log_file = ".rwapi.log"
file_handler = TimedRotatingFileHandler(log_file,'midnight')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


class Manager: 
  """Manages ReliefWeb API calls and SQLite database.

  Options
  - db = "data/reliefweb.db" session SQLite database
  - log_level = "info" (logs found in .rwapi.log)
  
  Usage:
  ```
  # make a Manager object, then execute desired actions
  rw = rwapi.Manager(db="data/reliefweb.db") 
  
  # make an API call
  rw.call("rwapi/calls/<call_parameters>.yml", "<appname>")

  # open/close the database
  rw.open_db()
  rw.close_db()
  ```"""


  def open_db(self):
    """Opens SQL database connection."""
    
    self.conn = sql.connect(self.db)
    self.c = self.conn.cursor()
    logger.debug(f"SQL {self.db} open")


  def close_db(self):
    """Closes SQL database connection."""

    self.c.execute("pragma optimize")
    self.c.close()
    self.conn.close()
    logger.debug(f"SQL close {self.db}")


  def _get_parameters(self):
    """Loads parameters from an input file or dict."""

    if isinstance(self.input, str):
      self.input = pathlib.Path(self.input)
      if not self.input.exists():
        raise FileNotFoundError(f"No such file: {self.input}")
      else:
        if self.input.suffix in [".yml", ".yaml"]:
          with open(self.input, "r") as stream:
            self.parameters = yaml.safe_load(stream)
        elif self.input.suffix == ".json":
          with open(self.input, "r") as f:
            self.parameters = json.load(f)
        else:
          raise ValueError(
              "Unknown format (use dict or str w/ extension .json .yml .yaml)."
          )
    elif isinstance(self.input, dict):
      self.parameters = self.input
      self.input = "dict"
    else:
      raise TypeError("Input must be a filepath (str) or dict.")


  def _call(self):
    """Makes a single ReliefWeb API call (returns response_json)"""
    
    # adjust offset when making multiple calls
    if self.pages > 1:
      self.parameters["offset"] = self.parameters["limit"] * self.page

    # make call
    self.now = pd.Timestamp.now().round("S").isoformat()
    logger.debug(f"PARAMS {self.parameters}")
    self.response = requests.post(self.url, json.dumps(self.parameters))

    # check response
    self.response.raise_for_status()
    self.response_json = self.response.json()
    if "error" in self.response_json:
      raise ValueError(self.response_json)

    summary = {k:v for k,v in self.response_json.items() if k != "data"}
    logger.info(f"CALL {summary}")


  def _get_field_names(self):
    """Makes a set of field names from response data."""

    self.field_names = set()
    for x in self.response_json["data"]:
      self.field_names.update(list(x["fields"].keys()))

    logger.debug(f"FIELDS {len(self.field_names)} {sorted(self.field_names)}")


  def _get_records_columns(self):
    """Gets a list of columns from the records table."""

    self.c.execute(f"select * from {self.records_table}")
    self.records_table_columns = [x[0] for x in self.c.description]


  def _update_columns(self):
    """Updates records table columns when new fields are detected."""

    self._get_field_names()
    self._get_records_columns()
    self.columns_old = [x.strip() for x in self.records_table_columns if x]
    self.columns_new = [x for x in self.field_names if x not in self.columns_old]
    self.columns_all = self.columns_old + self.columns_new

    for x in self.columns_all:
      try:
        self.c.execute(f"ALTER TABLE {self.records_table} ADD COLUMN '%s' " % x)
        logger.debug(f"SQL {x} added to {self.records_table}")
      except:
        pass


  def _prepare_records(self):
    """Reshapes and prepares response data for adding to the records table."""

    # normalize data, prepare 
    self.df = pd.json_normalize(self.response_json["data"], sep="_", max_level=1)
    self.df.drop(["id"], axis=1, inplace=True, errors=False)
    self.df.columns = [x.replace("fields_", "") for x in self.df.columns]
 
    # add rwapi metadata columns
    self.df["rwapi_input"] = self.input.name
    self.df["rwapi_date"] = self.now

    # add empty columns & reorder
    added_columns = []
    for x in [x for x in self.columns_all if x not in self.df.columns]:
      self.df[x] = ""
      added_columns.append(x)    
    logger.debug(f"DF added {len(added_columns)} {added_columns} columns")
  
    # convert everything to str
    self.df = self.df[self.columns_all]
    self.df = self.df.applymap(str)
    logger.debug(f"DF prepared {len(self.df.columns.tolist())} {sorted(self.df.columns.tolist())} columns")


  def _insert_records(self):
    """Inserts API data into records table, with report id as primary key."""

    records = self.df.to_records(index=False)
    self.c.executemany(
      f"INSERT OR REPLACE INTO {self.records_table} VALUES ({','.join(list('?' * len(self.columns_all)))})",
      records
    )

    self.conn.commit()
    logger.debug(f"SQL insert to {self.records_table}")


  def _quota_handler(self):
    """Tracks daily API usage against quota and limits excess calls."""

    self.quota = 0

    # count calls in log
    if pathlib.Path(log_file).exists():
      with open(pathlib.Path(log_file), "r") as f:
        daily_log = f.readlines()
      for x in daily_log:
        if "- CALL" in x:
          self.quota += 1

    # compute remaining calls in quota
    if self.quota >= self.quota_limit:
      raise UserWarning(f"Reached daily usage quota: {self.quota}/{self.quota_limit} calls made.")
    self.quota_remaining = self.quota_limit - self.quota

    # control API usage
    if self.pages > (self.quota_remaining):
      logger.info(f"QUOTA pages exceeds quota: will make {self.quota_remaining} instead of {self.pages}")
      self.pages = self.quota_remaining

    logger.debug(f"QUOTA {self.quota}/{self.quota_limit}")


  def _set_wait(self, wait_dict={0: 1, 5: 49, 10: 99, 20:499, 30:None}):
    """Sets wait time between pages (seconds to wait / for n pages).

    Defaults:
    (0/1)
    (5/2-49)
    (10/50-99)
    (20/100-499)
    (30/500+)

    Set a custom wait_dict before running calls:
    ```    
    job = rwapi.Manager()
    job.wait_dict = {0: 1, 1: 49, 4:None}
    ```"""

    # check for custom wait dict
    try:
      logger.debug(f"WAIT custom dict {self.wait_dict}")
    except:
      self.wait_dict = wait_dict

    waits = []
    for k, v in self.wait_dict.items():
      if v:
          if self.pages <= v:
            waits.append(k)
    if not waits:
      waits.append(max([k for k in self.wait_dict.keys()]))
    
    self.wait = min(waits)
    logger.debug(f"WAIT set to {self.wait} second(s)")


  def _insert_log(self):
    """Updates the log table with calls and parameters.
    
    - new calls replace log entries if the parameters are identical."""

    self.log_table = "call_log"
    self.c.execute(f"CREATE TABLE IF NOT EXISTS {self.log_table} (parameters PRIMARY KEY, rwapi_input, rwapi_date)")
    self.c.execute(
      f"INSERT OR REPLACE INTO {self.log_table} VALUES (?,?,?)", (json.dumps(self.parameters), self.input.name, str(self.now))
    )

    self.conn.commit()
    logger.debug(f"SQL insert to {self.log_table}")


  def call(self,
    input,
    appname,
    pages=1,
    url="https://api.reliefweb.int/v1/reports?appname=",
    quota_limit=1000,
    records_table="records",
  ):
    """Manages API calls made to ReliefWeb and saves results to database.
    
    Options
    - input = a JSON/YML filepath or dict with parameters
    - url = base url for making POST calls
    - pages = number of calls to make, incrementing 'offset' parameter
    - quota_limit = daily usage limit (see RW API documentation)
    - records_table = table where records are saved

    Extra
    - waits between calls (see _set_wait docstring)
    - adds call parameters and metadata to log table"""

    # parameters
    self.input = input
    self.url = "".join([url, appname])
    self.pages = pages
    self.quota_limit = quota_limit
    self.records_table = records_table
    self._set_wait()
    self._get_parameters()

    # run job
    for page in range(self.pages):
      self.page = page
      
      # make call
      logger.debug(f"MANAGER start page {self.page}")
      self._quota_handler()
      self._call()

      # abort
      if self.response_json["count"] == 0:
        raise UserWarning("API manager aborted: query returned no results.")

      # continue
      self.open_db()
      self.c.execute(f"CREATE TABLE IF NOT EXISTS {self.records_table} (id PRIMARY KEY, rwapi_input, rwapi_date) WITHOUT ROWID")
      self._update_columns()
      self._prepare_records()
      self._insert_records()
      self._insert_log()
      self.close_db()
      logger.debug(f"MANAGER done page {self.page}")

      # wait if needed
      if page < (self.pages - 1):
        logger.debug(f"WAIT {self.wait} seconds")
        time.sleep(self.wait)


  def _make_pdf_table(self):
    """Makes 'pdfs' table in database."""

    self.c.execute(f"CREATE TABLE IF NOT EXISTS pdfs (id PRIMARY KEY, qty, description, exclude, download, size_mb, words, lemma_test, sha256, orphan, verify, url)")
    self.pdfs_columns = [
      'id',
      'qty',
      'description',
      'exclude',
      'download',
      'size_mb',
      'words',
      'lemma_test',
      'sha256',
      'orphan',
      'verify',
      'url'
    ]


  def _empty_list_to_None(self, item):
    """Converts an empty list to None, otherwise returns item."""

    if isinstance(item, list):
      if [x for x in item if x]:
        return item
      else:
        return None
    else:
      return item


  def update_pdf_table(self):
    """Updates PDF table when new records exist."""

    self.open_db()
    self._make_pdf_table()

    # get records with PDFs
    df_records = pd.read_sql("SELECT file, id FROM records", self.conn)
    df = df_records[df_records["file"].str.contains(".pdf")].copy()
    df.reset_index(inplace=True,drop=True)

    # make columns
    df["file"] = df["file"].apply(ast.literal_eval)
    df["description"] = df["file"].apply(lambda item: [x.get("description", "") for x in item])
    df["url"] = df["file"].apply(lambda item: [x.get("url", "") for x in item])
    df["qty"] = df["file"].apply(len)
    new_columns = ["download", "size_mb", "sha256", "words", "lemma_test", "exclude", "orphan", "verify"]
    for x in new_columns:
      df[x] = None
    df.loc[df["qty"] > 1,"exclude"] = np.array([[0] * x for x in df.loc[df["qty"] > 1,"qty"]], dtype=object)

    # set datatypes
    df = df.applymap(self._empty_list_to_None)
    json_columns = [x for x in self.pdfs_columns if x not in ["id", "qty", "file"]]
    df[json_columns] = df[json_columns].applymap(json.dumps)
    df[['id', 'qty']] = df[['id', 'qty']].astype(str)

    # insert into SQL
    records = df[self.pdfs_columns].to_records(index=False)
    self.c.executemany(
      f"INSERT OR IGNORE INTO pdfs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
      records
    )
    self.conn.commit()

    qty_summary = {x: len(df[df["qty"] == x]) for x in sorted(df["qty"].unique())}
    logger.debug(f"{len(df)}/{len(df_records)} records with PDFs")
    logger.debug(f"pdf distribution {qty_summary}")


  def __repr__(self):
      return ""

  def __init__(
      self,
      db="data/reliefweb.db",
      log_level="info",
  ):
      # variables
      self.db = db
      self.log_file = log_file
 
      # logging
      numeric_level = getattr(logging, log_level.upper(), None)
      if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % log_level)
      logger.setLevel(numeric_level)