import string
import fasttext
import re
import sys
import hashlib
from pdfminer.high_level import extract_text
import io
import ast
import numpy as np
import requests
import json
import pandas as pd
import sqlite3 as sql
import pathlib
import logging

import rwapi

logger = logging.getLogger(__name__)
log_file = ".rwapi.log"


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

    def call(        
        self,
        input,
        n_calls=1,
        appname=None,
        url="https://api.reliefweb.int/v1/reports?appname=",
        quota=1000,
        wait_dict={0: 1, 5: 49, 10: 99, 20: 499, 30: None}
        ):
        """Manages making one or more API calls and saves results in self.db."""

        call_x = rwapi.Call(input, n_calls, appname, url, quota, wait_dict, self.log_level)
        for call_n in range(n_calls):
            call_x.call_n = call_n
            call_x._quota_enforce()
            call_x._increment_parameters()
            call_x._request()
            self.call_x = call_x
            self.c.execute(
                f"CREATE TABLE IF NOT EXISTS records (id PRIMARY KEY, rwapi_input, rwapi_date) WITHOUT ROWID"
            )
            self._update_columns()
            self._prepare_records()
            self._insert_records()
            self._insert_log()
            self.update_pdf_table()
            call_x._wait()


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

    def _get_records_columns(self):
        """Gets a list of columns from the records table."""

        self.c.execute(f"select * from records")
        self.records_columns = [x[0] for x in self.c.description]

    def _update_columns(self):
        """Updates records table columns when new fields are detected."""

        self._get_records_columns()
        self.columns_old = [x.strip() for x in self.records_columns if x]
        self.columns_new = [x for x in self.call_x.field_names if x not in self.columns_old]
        self.columns_all = self.columns_old + self.columns_new

        for x in self.columns_all:
            try:
                self.c.execute(f"ALTER TABLE records ADD COLUMN '%s' " % x)
            except:
                pass

    def _str_to_obj(self, item):
        """Parses a string into an object if possible using json or literal_eval."""

        try:
            return json.loads(item)
        except:
            try:
                return ast.literal_eval(item)
            except:
                return item

    def _nan_to_None(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converts df empty cells, np.nan, 'NULL' and similar to None."""

        bad_NAs = [np.nan] + [f"(?i)^{x}$" for x in ["", "none", "null", "nan"]]
        return df.replace(to_replace=bad_NAs, value=None, regex=True)

    def _prepare_records(self):
        """Reshapes and prepares response data for adding to the records table."""

        # normalize data
        self.response_df = pd.json_normalize(
            self.call_x.response_json["data"], sep="_", max_level=1
        )
        self.response_df.drop(["id"], axis=1, inplace=True, errors=False)
        self.response_df.columns = [
            x.replace("fields_", "") for x in self.response_df.columns
        ]
        self.response_df = self.response_df.applymap(self._str_to_obj)

        # add columns
        self.response_df["rwapi_input"] = self.call_x.input.name
        self.response_df["rwapi_date"] = self.call_x.now
        for x in [x for x in self.columns_all if x not in self.response_df.columns]:
            self.response_df[x] = None

        # reorder, convert to str
        self.response_df = self.response_df[self.columns_all]
        self.response_df = self.response_df.applymap(json.dumps)
        self.response_df = self._nan_to_None(self.response_df)
        logger.debug(
            f"prepared {len(self.response_df.columns.tolist())} {sorted(self.response_df.columns.tolist())} columns"
        )

    def _insert_records(self):
        """Inserts API data into records table, with report id as primary key."""

        records = self.response_df.to_records(index=False)
        self.c.executemany(
            f"INSERT OR REPLACE INTO records VALUES ({','.join(list('?' * len(self.columns_all)))})",
            records,
        )
        self.conn.commit()
        logger.debug(f"records")

    def _insert_log(self):
        """Updates history of calls (replaces identical old calls)."""

        self.c.execute(
            f"CREATE TABLE IF NOT EXISTS call_log (parameters PRIMARY KEY, rwapi_input, rwapi_date, count, total_count)"
        )
        self.c.execute(
            f"INSERT OR REPLACE INTO call_log VALUES (?,?,?,?,?)",
            (
                json.dumps(self.call_x.parameters),
                json.dumps(self.call_x.input.name),
                "".join(['"', str(self.call_x.now), '"']),
                self.call_x.response_json["count"],
                self.call_x.response_json["totalCount"],
            ),
        )
        self.conn.commit()
        logger.debug(f"call_log")

    def _make_pdf_table(self):
        """Makes 'pdfs' table in database."""

        self.c.execute(
            f"CREATE TABLE IF NOT EXISTS pdfs (id PRIMARY KEY, qty, description, exclude, download, size_mb, words_pdf, lang_pdf, lang_score_pdf, orphan, url)"
        )
        self.pdfs_columns = [
            "id",
            "qty",
            "description",
            "exclude",
            "download",
            "size_mb",
            "words_pdf",
            "lang_pdf",
            "lang_score_pdf",
            "orphan",
            "url",
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
        df = df_records[df_records["file"].notna()].copy()
        df = df.applymap(self._str_to_obj)
        df.reset_index(inplace=True, drop=True)

        # make columns
        df["description"] = df["file"].apply(
            lambda item: [x.get("description", "") for x in item]
        )
        df["url"] = df["file"].apply(lambda item: [x.get("url", "") for x in item])
        df["qty"] = df["file"].apply(len)
        new_columns = [
            "download",
            "size_mb",
            "lang_score_pdf",
            "words_pdf",
            "lang_pdf",
            "exclude",
            "orphan",
        ]
        for x in new_columns:
            df[x] = None
        df.loc[df["qty"] > 1, "exclude"] = np.array(
            [[0] * x for x in df.loc[df["qty"] > 1, "qty"]], dtype=object
        )

        # set datatypes
        df = df.applymap(self._empty_list_to_None)
        df = df.applymap(json.dumps)
        df = self._nan_to_None(df)

        # insert into SQL
        records = df[self.pdfs_columns].to_records(index=False)
        self.c.executemany(
            f"INSERT OR IGNORE INTO pdfs VALUES (?,?,?,?,?,?,?,?,?,?,?)", records
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
        df_merged = pd.merge(
            left=df_records, right=df, on="id", how="outer", indicator=True
        )
        orphan = df_merged[df_merged["_merge"] == "right_only"]["id"].values
        not_orphan = df_merged[df_merged["_merge"] == "both"]["id"].values

        # update pdfs table
        self.c.executemany(
            """UPDATE pdfs SET orphan = '1' WHERE id=?;""", [(x,) for x in orphan]
        )
        self.c.executemany(
            """UPDATE pdfs SET orphan = null WHERE id=?;""", [(x,) for x in not_orphan]
        )
        logger.debug(f"{len(orphan)} orphan(s) detected in 'pdfs' table")
        self.conn.commit()

        # find orphan files (in directory but no record in db)
        if dir:
            dir = pathlib.Path(dir)
            stored_pdfs = [x.stem for x in dir.glob("**/*") if x.is_file()]
            df = df.applymap(self.try_literal)
            filenames = [
                pathlib.Path(x).stem
                for y in df.apply(lambda row: self.make_filenames(row), axis=1)
                for x in y
            ]
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
                suffix = suffix.replace(" ", "_")
            if suffix:
                name = f'{row["id"]}_{x}_{suffix}.pdf'
            else:
                name = f'{row["id"]}_{x}.pdf'
            names.append(re.sub(r"[^.\w -]", "_", name))
        return names

    def check_ocr(self, text, model="lid.176.bin"):
        """Counts words in text and uses fasttext to predict language.

        - model = filename of fasttext model to load (must be in cwd dir/subdir)

        Uses a cleaned version of 'text' to improve accuracy.
        Returns a tuple of (words, language, confidence)."""

        if not text:
            return None
        else:
            # get fasttext model
            if not self.ft_model_path[0].exists():
                self.ft_model_path = [x for x in pathlib.Path().glob("**/lid.176.bin")]
                self.ft_model = fasttext.load_model(str(self.ft_model_path[0]))
                logger.debug(f"using ft model {self.ft_model_path[0]}")
                if len(self.ft_model_path) > 1:
                    logger.warning(f"Multiple {model} files found in cwd")

            # clean text
            drops = "".join([string.punctuation, string.digits, "\n\t"])
            blanks = " " * len(drops)
            text = re.sub(
                r"\S*\\\S*|\S*@\S*|/*%20/S*|S*/S*/S*|http+\S+|www+\S+", " ", text
            )
            text = text.translate(str.maketrans(drops, blanks))
            text = text.translate(
                str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
            )

            # predict
            prediction = self.ft_model.predict(text)
            length = len(text.split())
            lang = prediction[0][0][-2:]
            score = round(prediction[1][0], 2)
            logger.debug(f"{length} words, {lang}: {score}")

            return length, lang, score

    def _try_extract_text(self, response, filepath, maxpages=1000000):
        if filepath.exists():
            text = extract_text(filepath, maxpages=maxpages)
        else:
            try:
                text = extract_text(io.BytesIO(response.content, maxpages=maxpages))
                logger.debug("bytesIO")
            except:
                with open(filepath, "wb") as f:
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
                logger.debug(f"{filepath.stem} ({size} MB) downloaded")

                # manage response by mode
                if "pdf" in mode:
                    # save pdf file
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    logger.debug(f"{filepath} saved")

                if "txt" in mode:
                    # save txt file
                    text = self._try_extract_text(response, filepath)
                    with open(filepath.with_suffix(".txt"), "w") as f:
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
                        logger.debug(f"{filepath} deleted")

            records = [json.dumps(x) for x in [sizes, dates, lengths, langs, scores]]
            records = tuple(records) + (str(row["id"]),)

            # insert into SQL
            self.c.execute(
                f"""UPDATE pdfs SET 
        size_mb = ?,
        download = ?, 
        words_pdf = ?,
        lang_pdf = ?,
        lang_score_pdf =?
        WHERE id = ?;""",
                records,
            )
            self.conn.commit()

    def sha256(self, item):
        """Convenience wrapper for returning a sha256 checksum for an item."""

        return hashlib.sha256(item).hexdigest()

    def add_exclude_list(self, name: str, lines: str):
        """Adds/replaces an exclude list for PDFS with unwanted 'description' values.

        - name = a unique name for an exclude list
        - lines = a string with TXT formatting (one item per line)."""

        self.c.execute(f"CREATE TABLE IF NOT EXISTS excludes (name PRIMARY KEY, list)")
        self.c.execute(f"INSERT OR REPLACE INTO excludes VALUES (?,?)", (name, lines))
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
        self.c.executemany("""UPDATE pdfs SET exclude = ? WHERE id=?;""", records)
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
        stored_pdfs = [x for x in dir.glob("**/*") if x.is_file()]
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
        logger.debug(
            f"del {deleted}/{len(stored_pdfs)} (dry_run={dry_run}): self.del_files"
        )

    def make_dfs(self, tables=["records", "pdfs", "call_log"]):
        """Adds a dict of dfs to instance.

        'tables' specifies which dfs are created (must be from existing options).
        Caution: may use excessive memory."""

        if isinstance(tables, str):
            tables = [tables]
        accepted_tables = ["records", "pdfs", "call_log"]
        if [x for x in tables if x not in accepted_tables]:
            raise ValueError(f"Accepted tables are {tables}")

        self.dfs = {x: pd.read_sql(f"SELECT * FROM {x}", self.conn) for x in tables}
        for k, v in self.dfs.items():
            self.dfs[k] = v.applymap(self._str_to_obj)

        logger.debug(f"generated {tables} dataframes")

    def summarize_descriptions(self, dir="data"):
        """Generates a file with a summary of descriptions in the 'pdfs' table."""

        dir = pathlib.Path(dir)
        file = dir / "_".join([pathlib.Path(self.db).stem, "descriptions.csv"])
        descriptions = [x for x in self.dfs["pdfs"]["description"] if x]
        descriptions = [y for x in descriptions for y in x]
        df_flat = pd.DataFrame({"description": descriptions})
        df_flat["description"].value_counts().to_csv(file)
        logger.debug(f"{file}")

    def __repr__(self):
        return ""

    def __init__(
        self,
        db="data/reliefweb.db",
        log_level="info",
    ):
        # variables
        self.db = db
        self.log_level = log_level
        self.log_file = log_file
        self.ft_model_path = [pathlib.Path("/dummy/path/to/model")]

        # logging
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError("Invalid log level: %s" % log_level)
        logger.setLevel(numeric_level)

        self.open_db()
