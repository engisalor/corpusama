import string
import fasttext
import re
import sys
import hashlib
from pdfminer.high_level import extract_text
import io
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
file_handler = TimedRotatingFileHandler(log_file,'midnight',backupCount=0)
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
  rw.call("rwapi/calls/<call_parameters>.yml", "<appname>")
  rw.get_item_pdfs()
  rw.<other_methods>()
  ```"""


  def open_db(self):
    """Opens SQL database connection."""
    
    self.conn = sql.connect(self.db)
    self.c = self.conn.cursor()
    logger.debug(f"{self.db}")


  def close_db(self):
    """Closes SQL database connection."""

    self.c.execute("pragma optimize")
    self.c.close()
    self.conn.close()
    logger.debug(f"{self.db}")


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
    if self.page > 0:
      self.parameters["offset"] += self.response_json["count"]

    # make call
    self.now = pd.Timestamp.now().round("S").isoformat()
    logger.debug(f"params {self.parameters}")
    self.response = requests.post(self.url, json.dumps(self.parameters))

    # check response
    self.response.raise_for_status()
    self.response_json = self.response.json()
    if "error" in self.response_json:
      raise ValueError(self.response_json)

    summary = {k:v for k,v in self.response_json.items() if k != "data"}
    logger.info(f"{summary}")


  def _get_field_names(self):
    """Makes a set of field names from response data."""

    self.field_names = set()
    for x in self.response_json["data"]:
      self.field_names.update(list(x["fields"].keys()))

    logger.debug(f"{len(self.field_names)} {sorted(self.field_names)}")


  def _get_records_columns(self):
    """Gets a list of columns from the records table."""

    self.c.execute(f"select * from records")
    self.records_columns = [x[0] for x in self.c.description]


  def _update_columns(self):
    """Updates records table columns when new fields are detected."""

    self._get_field_names()
    self._get_records_columns()
    self.columns_old = [x.strip() for x in self.records_columns if x]
    self.columns_new = [x for x in self.field_names if x not in self.columns_old]
    self.columns_all = self.columns_old + self.columns_new

    for x in self.columns_all:
      try:
        self.c.execute(f"ALTER TABLE records ADD COLUMN '%s' " % x)
        logger.debug(f"{x} added to records")
      except:
        pass


  def try_literal(self, item):
    try:
      return ast.literal_eval(item)  
    except:
      return item

  def try_json(self, item):
    try:
      return json.loads(item)
    except:
      return item


  def _prepare_records(self):
    """Reshapes and prepares response data for adding to the records table."""

    # normalize data, prepare 
    self.df = pd.json_normalize(self.response_json["data"], sep="_", max_level=1)
    self.df.drop(["id"], axis=1, inplace=True, errors=False)
    self.df.columns = [x.replace("fields_", "") for x in self.df.columns]

    self.df = self.df.applymap(self.try_literal)
    self.df = self.df.replace({np.nan:None})

    # add rwapi metadata columns
    self.df["rwapi_input"] = self.input.name
    self.df["rwapi_date"] = self.now

    # add empty columns & reorder
    added_columns = []
    for x in [x for x in self.columns_all if x not in self.df.columns]:
      self.df[x] = None
      added_columns.append(x)    
    logger.debug(f"added {len(added_columns)} {added_columns} columns")
  
    # convert everything to str
    self.df = self.df[self.columns_all]
    self.df = self.df.applymap(json.dumps)
    logger.debug(f"prepared {len(self.df.columns.tolist())} {sorted(self.df.columns.tolist())} columns")


  def _insert_records(self):
    """Inserts API data into records table, with report id as primary key."""

    records = self.df.to_records(index=False)
    self.c.executemany(
      f"INSERT OR REPLACE INTO records VALUES ({','.join(list('?' * len(self.columns_all)))})",
      records
    )
    self.conn.commit()
    logger.debug(f"records")


  def _quota_handler(self):
    """Tracks daily API usage against quota and limits excess calls."""

    self.quota = 0

    # count calls in log
    if pathlib.Path(log_file).exists():
      with open(pathlib.Path(log_file), "r") as f:
        daily_log = f.readlines()
      for x in daily_log:
        if "- call -" in x:
          self.quota += 1

    # compute remaining calls in quota
    if self.quota >= self.quota_limit:
      raise UserWarning(f"Reached daily usage quota: {self.quota}/{self.quota_limit} calls made.")
    self.quota_remaining = self.quota_limit - self.quota

    # control API usage
    if self.pages > (self.quota_remaining):
      logger.info(f"pages exceeds quota: making {self.quota_remaining} instead of {self.pages}")
      self.pages = self.quota_remaining

    logger.debug(f"{self.quota}/{self.quota_limit}")


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
      logger.debug(f"custom dict {self.wait_dict}")
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
    logger.debug(f"{self.wait} second(s)")


  def _insert_log(self):
    """Updates history of calls (replaces identical old calls)."""

    self.c.execute(f"CREATE TABLE IF NOT EXISTS call_log (parameters PRIMARY KEY, rwapi_input, rwapi_date, count, total_count)")
    self.c.execute(
      f"INSERT OR REPLACE INTO call_log VALUES (?,?,?,?,?)", (json.dumps(self.parameters), self.input.name, str(self.now), self.response_json["count"], self.response_json["totalCount"])
    )
    self.conn.commit()
    logger.debug(f"call_log")


  def call(self,
    input,
    appname,
    pages=1,
    url="https://api.reliefweb.int/v1/reports?appname=",
    quota_limit=1000,
  ):
    """Manages API calls made to ReliefWeb and saves results to database.
    
    Options
    - input = a JSON/YML filepath or dict with parameters
    - appname = unique identifier for using RW API
    - pages = number of calls to make, incrementing 'offset' parameter
    - url = base url for making POST calls
    - quota_limit = daily usage limit (see RW API documentation)"""

    # parameters
    self.input = input
    self.url = "".join([url, appname])
    self.pages = pages
    self.quota_limit = quota_limit
    self._set_wait()
    self._get_parameters()

    # run job
    for page in range(self.pages):
      self.page = page
      
      # make call
      logger.debug(f"page {self.page}")
      self._quota_handler()
      self._call()

      # abort
      if self.response_json["count"] == 0:
        raise UserWarning("API manager aborted: query returned no results.")

      # continue
      self.c.execute(f"CREATE TABLE IF NOT EXISTS records (id PRIMARY KEY, rwapi_input, rwapi_date) WITHOUT ROWID")
      self._update_columns()
      self._prepare_records()
      self._insert_records()
      self._insert_log()
      self.update_pdf_table()

      # wait if needed
      if page < (self.pages - 1):
        logger.debug(f"waiting {self.wait} seconds")
        time.sleep(self.wait)


  def _make_pdf_table(self):
    """Makes 'pdfs' table in database."""

    self.c.execute(f"CREATE TABLE IF NOT EXISTS pdfs (id PRIMARY KEY, qty, description, exclude, download, size_mb, words_pdf, lang_pdf, lang_score_pdf, orphan, url)")
    self.pdfs_columns = [
      'id',
      'qty',
      'description',
      'exclude',
      'download',
      'size_mb',
      'words_pdf',
      'lang_pdf',
      'lang_score_pdf',
      'orphan',
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
    new_columns = ["download", "size_mb", "lang_score_pdf", "words_pdf", "lang_pdf", "exclude", "orphan"]
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
      f"INSERT OR IGNORE INTO pdfs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
      records
    )
    self.conn.commit()

    qty_summary = {x: len(df[df["qty"] == x]) for x in sorted(df["qty"].unique())}
    logger.debug(f"{len(df)}/{len(df_records)} records with PDFs")
    logger.debug(f"pdf distribution {qty_summary}")
    self.detect_orphans()


  def detect_orphans(self, dir=None):
    """Detects items in 'pdfs' missing from 'records'.
    
    Marks orphans as '1' in 'pdfs'.
    Optionally outputs files in 'dir' missing from 'pdfs' table."""

    df_records = pd.read_sql("SELECT id FROM records", self.conn)
    df = pd.read_sql("SELECT * FROM pdfs", self.conn)

    # find orphan records (in pdfs but not records)
    df_merged = pd.merge(left=df_records,right=df,on='id',how='outer', indicator=True)
    orphan = df_merged[df_merged["_merge"] == "right_only"]["id"].values
    not_orphan = df_merged[df_merged["_merge"] == "both"]["id"].values

    # update pdfs table
    self.c.executemany('''UPDATE pdfs SET orphan = 'true' WHERE id=?;''',
    [(x,) for x in orphan])
    self.c.executemany('''UPDATE pdfs SET orphan = 'null' WHERE id=?;''',
    [(x,) for x in not_orphan])
    logger.debug(f"{len(orphan)} orphan(s) detected in 'pdfs' table")
    self.conn.commit()

    # find orphan files (in directory but no record in db)
    if dir:
      dir = pathlib.Path(dir)
      stored_pdfs = [x.stem for x in dir.glob('**/*') if x.is_file()]
      df = df.applymap(self.try_literal)
      filenames = [pathlib.Path(x).stem for y in df.apply(lambda row: self.make_filenames(row), axis=1) for x in y]
      orphan_files = [x for x in stored_pdfs if x not in filenames]
      logger.debug(f"{len(orphan_files)} file(s) missing a record in 'pdfs'")
      return orphan_files


  def make_filenames(self, row):
    """Generates a list of filenames for a record in the 'pdfs' table."""

    descriptions = row["description"]
    names = []
    for x in range(len(row["url"])):
      desc, suffix = None, None
      if isinstance(descriptions, list):
        desc = row["description"][x]
      if desc:
        suffix = desc[:50] if len(desc) > 50 else desc
        suffix = suffix.replace(" ","_")
      if suffix:
        name = f'{row["id"]}_{x}_{suffix}.pdf'
      else:
        name =f'{row["id"]}_{x}.pdf'
      names.append(re.sub(r'[^.\w -]', '_', name))
    return names


  def check_ocr(self, text, model="lid.176.bin"):
    """Counts words in text and uses fasttext to predict language.

    - model = filename of fasttext model to load (must be in cwd dir/subdir)
    
    Uses a cleaned version of 'text' to improve accuracy.
    Returns a tuple of (words, language, confidence)."""
    
    # get fasttext model
    if not self.ft_model_path[0].exists():
      self.ft_model_path = [x for x in pathlib.Path().glob('**/lid.176.bin')]
      self.ft_model = fasttext.load_model(str(self.ft_model_path[0]))
      logger.debug(f"using ft model {self.ft_model_path[0]}")
      if len(self.ft_model_path) > 1:
        logger.warning(f"Multiple {model} files found in cwd")

    # clean text
    drops = "".join([string.punctuation, string.digits,"\n\t"])
    blanks = " "*len(drops)
    text = re.sub(r"\S*\\\S*|\S*@\S*|/*%20/S*|S*/S*/S*|http+\S+|www+\S+", " ", text)
    text = text.translate(str.maketrans(drops,blanks))
    text = text.translate(str.maketrans(string.ascii_uppercase,string.ascii_lowercase))

    # predict
    prediction = self.ft_model.predict(text)
    length = len(text.split())
    lang = prediction[0][0][-2:]
    score = round(prediction[1][0],2)
    logger.debug(f"{length} words, {lang}: {score}")
    
    return length, lang, score


  def _try_extract_text(self, response,filepath, maxpages=1000000):
    if filepath.exists():
      text = extract_text(filepath, maxpages=maxpages)
    else:
      try:
        text = extract_text(io.BytesIO(response.content, maxpages=maxpages))
        logger.debug("bytesIO")
      except:
        with open(filepath, 'wb') as f:
          f.write(response.content)
        text = extract_text(filepath, maxpages=maxpages)
        logger.debug("bytesIO failed: trying file")

    return text


  def get_item_pdfs(self, index: int, mode, dir="data/files"):
    """Downloads PDFs for a 'pdfs' table index to a given directory.
    
    Mode determines file format(s) to save: "pdf", "txt" or ["pdf", "txt"].
    Excludes PDFs where exclude = 1 in the 'pdfs' table."""

    if isinstance(mode, str):
      mode = [mode]
    for x in mode:
      if x not in ["pdf", "txt"]:
        raise ValueError(f"Valid modes are 'pdf', 'txt' or ['pdf','txt']")

    self.update_pdf_table()
    df = pd.read_sql("SELECT * FROM pdfs", self.conn)
    dates, sizes, lengths, langs, scores = [], [], [], [], []
    row = df.iloc[index].copy()
    row = row.apply(self.try_json)
    names = self.make_filenames(row)

    # for each url in a record
    for x in range(len(row["url"])):
      filepath = pathlib.Path(dir) / names[x]
      if not row["exclude"]:
        row["exclude"] = [0] * len(row["url"])

      # skip excluded files
      if row["exclude"][x] == 1:
        logger.debug(f"exclude {filepath.name}")
        for x in [dates, sizes, lengths, langs, scores]:
          x.append("")

      # process PDF
      else:
        response = requests.get(row["url"][x])
        size = round(sys.getsizeof(response.content) / 1000000, 1)
        logger.debug(f'{filepath.stem} ({size} MB) downloaded')

        # manage response by mode
        if "pdf" in mode:
          # save pdf file
          with open(filepath, 'wb') as f:
            f.write(response.content)
          logger.debug(f'{filepath} saved')

        if "txt" in mode:
          # save txt file
          text = self._try_extract_text(response, filepath)
          with open(filepath.with_suffix(".txt"), 'w') as f:
            f.write(text)
          logger.debug(f'{filepath.with_suffix(".txt")} saved')

        # test for English OCR layer
        text = self._try_extract_text(response, filepath)
        length, lang, score = self.check_ocr(text)

        # add metadata
        dates.append(str(pd.Timestamp.now().round("S").isoformat()))
        sizes.append(size)
        lengths.append(length)
        langs.append(lang)
        scores.append(score)

        # delete unwanted pdf
        if not "pdf" in mode:
          if filepath.exists():
            pathlib.Path.unlink(filepath)
            logger.debug(f'{filepath} deleted')

      records = [json.dumps(x) for x in [sizes, dates, lengths, langs, scores]]
      records = tuple(records) + (str(row["id"]),)

      # insert into SQL
      self.c.execute(f'''UPDATE pdfs SET 
        size_mb = ?,
        download = ?, 
        words_pdf = ?,
        lang_pdf = ?,
        lang_score_pdf =?
        WHERE id = ?;''',
        records)
      self.conn.commit()


  def sha256(self,item):
    """Convenience wrapper for returning a sha256 checksum for an item."""

    return hashlib.sha256(item).hexdigest()


  def add_exclude_list(self, name: str, lines: str):
    """Adds/replaces an exclude list for PDFS with unwanted 'description' values.
    
    - name = a unique name for an exclude list
    - lines = a string with TXT formatting (one item per line)."""

    self.c.execute(f"CREATE TABLE IF NOT EXISTS excludes (name PRIMARY KEY, list)")
    self.c.execute(f"INSERT OR REPLACE INTO excludes VALUES (?,?)", (name,lines))
    self.conn.commit()
    logger.debug(f"{name} inserted")


  def get_excludes(self, names=None):
    """Generates self.excludes_df. Specify 'names' (str, list of str) to filter items."""

    df = pd.read_sql("SELECT * FROM excludes", self.conn)
    
    if isinstance(names, str):
      names = [names]
    elif isinstance(names, list):
      pass
    elif not names:
      names = list(df["name"])
    else:
      raise TypeError("'names' must be None, a string or list of strings.")

    self.excludes_df = df.loc[df["name"].isin(names)]
    logger.debug(f"retrieved {names}")


  def set_excludes(self, names=None):
    """Sets exclude values in 'pdfs' table using values from 'excludes' table.
    
    names = excludes list(s) to apply (str, list of str)"""

    # get excludes items
    self.get_excludes(names)
    excludes_values = [x for x in self.excludes_df["list"].values]
    excludes_list = [y for x in excludes_values for y in x.split()]
    excludes_set = set(excludes_list)

    # get pdfs table
    df = pd.read_sql("SELECT id, exclude, description FROM pdfs", self.conn)
    for x in ["description", "exclude"]:
      df[x] = df[x].apply(json.loads)

    def set_exclude(description):
      """Sets exclude value for a row in 'pdfs'."""

      excludes = []
      if description:
        for x in description:
          description_list = x.lower().split()
          if [x for x in description_list if x in excludes_set]:
            excludes.append(1)
          else:
            excludes.append(0)
        
        if [x for x in excludes if x]:
          return excludes
        else:
          return None

    # set values and update table
    df["exclude"] = df["description"].apply(set_exclude)
    df["exclude"] = df["exclude"].apply(json.dumps)
    records = df[["exclude", "id"]].to_records(index=False)
    self.c.executemany('''UPDATE pdfs SET exclude = ? WHERE id=?;''',
      records)
    self.conn.commit()
    logger.debug(f"excludes set")


  def del_exclude_files(self, names=None, dir="data/files", dry_run=False):
    """Deletes files in dir if filename has match in exclude list.

    Caution: deletes files whether or not they appear in 'pdfs' table.
    E.g., 'languages' or ['languages', '<another list>']
    Matches exact words, case insensitive, ('summary', 'spanish') 
    'names' refers to one or more exclude lists in the 'excludes' table.
    (See get_excludes docstring)."""

    # get files list
    dir = pathlib.Path(dir)
    if not dir.exists():
      raise OSError(f"{dir} does not exist.")
    stored_pdfs = [x for x in dir.glob('**/*') if x.is_file()]
    stored_pdfs = [x for x in stored_pdfs if x]

    # get exclude patterns
    self.get_excludes(names)
    excludes = [x.split() for x in self.excludes_df["list"].values]
    excludes = [y for x in excludes for y in x]

    deleted = 0
    deletes = []
    for x in stored_pdfs:
      delete = []
      for y in x.stem.lower().split("_"):
        if y in excludes:
          delete.append(True)
      if True in delete:
        deletes.append(str(x))
        deleted += 1
      if not dry_run:
        x.unlink(missing_ok=True)
        x.with_suffix(".txt").unlink(missing_ok=True)
    
    self.del_files = deletes
    logger.debug(f"del {deleted}/{len(stored_pdfs)} (dry_run={dry_run}): self.del_files")


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
      self.ft_model_path = [pathlib.Path("/dummy/path/to/model")]
 
      # logging
      numeric_level = getattr(logging, log_level.upper(), None)
      if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % log_level)
      logger.setLevel(numeric_level)

      self.open_db()