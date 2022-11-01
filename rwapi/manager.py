import io
import json
import logging
import pathlib
import re
import string
import sys

import fasttext
import pandas as pd
import requests
from pdfminer.high_level import extract_text

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
    rw.db.close_db()
    ```"""

    def call(
        self,
        input,
        n_calls=1,
        appname=None,
        url="https://api.reliefweb.int/v1/reports?appname=",
        quota=1000,
        wait_dict={0: 1, 5: 49, 10: 99, 20: 499, 30: None},
    ):
        """Manages making one or more API calls and saves results in self.db."""

        call_x = rwapi.Call(
            input, n_calls, appname, url, quota, wait_dict, self.log_level
        )
        for call_n in range(n_calls):
            call_x.call_n = call_n
            call_x._quota_enforce()
            call_x._increment_parameters()
            call_x._request()
            self.call_x = call_x
            self._insert_records()
            self._insert_log()
            call_x._wait()

    def _insert_records(self):
        """Reshapes and inserts API results to the records table."""

        # normalize data
        records = pd.json_normalize(
            self.call_x.response_json["data"], sep="_", max_level=1
        )
        records.drop(["id"], axis=1, inplace=True, errors=False)
        records.columns = [x.replace("fields_", "") for x in records.columns]
        # add columns
        records["rwapi_input"] = self.call_x.input.name
        records["rwapi_date"] = self.call_x.now
        for x in [x for x in self.db.columns["records"] if x not in records.columns]:
            records[x] = None
        self.db._insert(records, "records")

    def _insert_log(self):
        """Updates history of calls (replaces identical old calls)."""

        self.db.c.execute(
            f"INSERT OR REPLACE INTO call_log VALUES (?,?,?,?,?)",
            (
                self.call_x.parameters,
                self.call_x.input.name,
                "".join(['"', str(self.call_x.now), '"']),
                self.call_x.response_json["count"],
                self.call_x.response_json["totalCount"],
            ),
        )
        self.db.conn.commit()
        logger.debug(f"call logged")

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

        df = pd.read_sql("SELECT * FROM pdfs", self.db.conn)
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
            self.db.c.execute(
                """UPDATE pdfs SET
        size_mb = ?,
        download = ?,
        words_pdf = ?,
        lang_pdf = ?,
        lang_score_pdf = ?
        WHERE id = ?;""",
                records,
            )
            self.db.conn.commit()

    def summarize_descriptions(self, dir="data"):
        """Generates a file with a summary of descriptions in the 'pdfs' table."""

        dir = pathlib.Path(dir)
        file = dir / "_".join([pathlib.Path(self.db_name).stem, "descriptions.csv"])
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
        self.db_name = db
        self.log_level = log_level
        self.log_file = log_file
        self.ft_model_path = [pathlib.Path("/dummy/path/to/model")]

        # logging
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError("Invalid log level: %s" % log_level)
        logger.setLevel(numeric_level)

        # database connection
        self.db = rwapi.db.Database(db, log_level)
