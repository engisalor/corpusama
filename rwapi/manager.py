import requests
import json
import pandas as pd
import yaml
import sqlite3 as sql
import pandas as pd
import pathlib
import logging
from logging.handlers import TimedRotatingFileHandler


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

file_handler = TimedRotatingFileHandler(".rwapi.log", backupCount=1)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


class Manager: 
  """Manage ReliefWeb API calls and SQLite database.
  
  Logs found in .rwapi.log.
  See method docstrings for details."""

  def call(self):
    """Make a ReliefWeb API call with parameters from a JSON or YML file or dict.
    
    Documentation at https://apidoc.rwlabs.org/parameters.
    See example.json and example.yml.
    Makes self.response_json if no errors detected."""
    
    # get parameters
    if isinstance(self.input, str):
      self.input = pathlib.Path(self.input)
      if not self.input.exists():
          raise FileNotFoundError
      else:
        if self.input.suffix in [".yml", ".yaml"]:
          with open(self.input, "r") as stream:
            self.parameters = yaml.safe_load(stream)
        elif self.input.suffix == ".json":
          with open(self.input, "r") as f:
            self.parameters = json.load(f)
        else:
          raise ValueError(
              "Unknown format (use dict or str w/ extension .json .yml .yaml)"
          )
    elif isinstance(self.input, dict):
      self.parameters = self.input
    else:
      raise TypeError("Input must be a filepath (str) or dict")

    # make call
    self.now = pd.Timestamp.now().round("S").isoformat()
    response = requests.post(self.url, json.dumps(self.parameters))

    try:
      response_json = response.json()
    except:
      response.raise_for_status()

    # display errors
    if "error" in response_json:
      raise ValueError(response_json)

    summary = {k:v for k,v in response_json.items() if k != "data"}
    logger.debug(f"CALL {summary}")
    self.response_json = response_json


  def get_field_names(self):
    """Make a set of field names from response data.
    
    Returns self.field_names."""

    field_names = set()
    for x in self.response_json["data"]:
      field_names.update(list(x["fields"].keys()))

    self.field_names = field_names
    logger.debug(f"FIELDS {len(self.field_names)} {sorted(self.field_names)}")


  def get_columns(self):
    """Compare columns for incoming API data and SQL table.
    
    Makes self.columns_all (list of all columns).
    Makes self.columns_str (a string w/ columns for a MAKE TABLE command.
    
    Uses report id as primary key for tables.
    Maintains order of columns when new fields are added."""

    if not self.fields_file.exists():
      with open(self.fields_file, "w") as f:
        f.write("")

    with open(self.fields_file, "r") as f:
      self.columns_old = f.readlines()

    self.columns_old = [x.strip() for x in self.columns_old if x]
    self.columns_old.extend([x for x in self.extra_columns if x not in self.columns_old])
    self.columns_new = [x for x in self.field_names if x not in self.columns_old]
    self.columns_all = self.columns_old + self.columns_new
    columns_str = ",".join(self.columns_all)
    self.columns_str = columns_str.replace(",id,",",id PRIMARY KEY,")

  def open_db(self):
    """Connects to SQL database and makes table if not exists."""
    
    self.conn = sql.connect(self.db)
    self.c = self.conn.cursor()
    self.c.execute( "".join(["CREATE TABLE IF NOT EXISTS ", self.table, " (", self.columns_str, ") WITHOUT ROWID"]))
    self.c.execute("pragma journal_mode = WAL")
    self.c.execute("pragma synchronous = normal")
    self.conn.commit()
    logger.debug(f"SQL {self.db}: {self.table} open")


  def update_columns(self):
    # update table columns
    for x in self.columns_all:
      try:
        self.c.execute("".join(["ALTER TABLE ", self.table, " ADD COLUMN '%s' "]) % x)
        logger.debug(f"SQL {x} added to {self.table}")
      except:
        pass
    
    # fields columns file
    with open(self.fields_file, "w") as f:
      f.writelines("\n".join(self.columns_all))
    logger.debug(f"FIELDS {self.fields_file} saved")


  def prepare_data(self):
    """Reshapes and prepares response data for adding to SQLite."""

    # normalize data, prepare 
    self.df = pd.json_normalize(self.response_json["data"], sep="_", max_level=1)
    self.df.drop(["id"], axis=1, inplace=True, errors=False)
    self.df.columns = [x.replace("fields_", "") for x in self.df.columns]
 
    # add extra columns & data # NOTE still requires manual intervention to add this data
    self.df["query_date"] = self.now
    logger.debug(f"DF query_date column added")

    # add empty columns & reorder
    added_columns = []
    for x in [x for x in self.columns_all if x not in self.df.columns]:
      self.df[x] = ""
      added_columns.append(x)    
    logger.debug(f"DF {len(added_columns)} {added_columns} added")
  
    # convert everything to str
    self.df = self.df[self.columns_all]
    self.df = self.df.applymap(str)
    logger.debug(f"DF {len(self.df.columns.tolist())} {sorted(self.df.columns.tolist())} columns")
    logger.debug(f"DF prepared")


  def insert_data(self):
    """Convert data in self.df to records, add to SQLite.
    
    Uses report id as as primary key: replaces existing records."""

    records = self.df.to_records(index=False)
    self.c.executemany(
      "".join(["INSERT OR REPLACE INTO reports VALUES (", ",".join(list("?" * len(self.columns_all))), ")"]),
      # "".join(["INSERT OR REPLACE INTO reports VALUES (", ",".join(columns_all), ")"]), # FIXME broken alternative to above
      records
    )

    self.conn.commit()
    logger.debug(f"SQL insert to {self.table}")


  def __repr__(self):
      return ""

  def __init__(
      self,
      input,
      appname,
      fields_file="data/fields.txt",
      extra_columns=["query_date"],
      url="https://api.reliefweb.int/v1/reports?appname=",
      db="data/reliefweb.db",
      table="reports",
      loglevel="debug",
  ):
      # variables
      self.input = input
      self.url = "".join([url, appname])
      self.fields_file = pathlib.Path(fields_file)
      self.extra_columns = extra_columns
      self.db = db
      self.table = table

      # logging
      numeric_level = getattr(logging, loglevel.upper(), None)
      if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % loglevel)
      logger.setLevel(numeric_level)

      # execute
      logger.debug(f"MANAGER start")
      self.call()
      self.get_field_names()
      self.get_columns()
      self.open_db()
      self.update_columns()
      self.prepare_data()
      self.insert_data()

      # wrap up
      self.c.execute("pragma optimize")
      self.c.close()
      self.conn.close()
      logger.debug(f"SQL close {self.db}")
      logger.debug(f"MANAGER done")
