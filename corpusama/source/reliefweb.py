"""A module for managing ReliefWeb API calls."""
import logging
import math
import pathlib
from multiprocessing import cpu_count
from time import perf_counter

import pandas as pd

from corpusama.database.database import Database
from corpusama.source import pdf
from corpusama.source.call import Call
from corpusama.util import decorator

logger = logging.getLogger(__name__)


class ReliefWeb(Call):
    """Manages API calls made to ReliefWeb.

    Args:
        input: A JSON/YML filepath or dictionary with parameters.
        database: A database filename, e.g., `mycorpus.db`.
        appname: A unique identifier for using ReliefWeb's API.
        url: A base url for making POST calls.
        quota: A daily usage limit (see ReliefWeb API documentation).
        wait_dict: A dictionary of wait times.

    Methods:
        one: Makes one API call.
        all: Makes repeated API calls by increasing `offset`.
        new: Makes API calls for data that hasn't been retrieved yet.

    Attributes:
        raw: Stores API call data (may be overwritten depending on calls made).

    Notes:
        - The maximum number of daily calls defaults to 1,000.
        - The default wait dictionary is: `{0: 1, 5: 49, 10: 99, 20: 499, 30: None}`.
        - If `db=None`, data is only stored in `ReliefWeb.raw`.
        - Logs a warning if a database is missing columns (update schema
            to save such data or ignore by updating `missing_columns.ignore`).

    See Also:
        - `source.call.Call` (parent class with inherited methods/attributes).
        - Repository documentation for tips on making ReliefWeb calls.

        <https://reliefweb.int/help/api>
        <https://reliefweb.int/terms-conditions>
    """

    def _offset(self) -> None:
        """Adjusts the offset parameter and halts a job if no more results."""
        if self.call_n > 0:
            self.parameters["offset"] += self.response_json["count"]
            if self.response_json["count"] == 0:
                logger.debug("no more results")
                raise SystemExit()
        logger.debug(self.parameters["offset"])

    def get_all_records(self, limit: int = 0) -> None:
        """Makes repeated calls by incrementing the offset field.

        Args:
            limit: The maximum number of calls to make (0 = as many as possible).

        Notes:
            - Makes calls exactly as parameters indicate and increments `offset`
                with each call.
            - Overwrites existing database raw content and starts over again if
                aborted (not usable to progressively download content).
        """
        self.call_n = 0
        self.limit = limit
        if limit == 0:
            self.limit = self.quota
        self.get_record()

    def get_new_records(self, limit: int = 0) -> None:
        """Makes repeated calls starting from the latest `date.changed`.

        Args:
            limit: The maximum number of calls to make (0 = as many as possible).

        Notes:
            - Requires use with a `Database` and that API parameters include
                `"sort": ["date.changed:asc"]`.
            - Calls are made starting with the oldest `date.changed` value.
            - Modified content is overwritten if its `date.changed` is newer
                than the latest value.
            - Can be aborted and restarted and will safely continue at
                the job's previous state.
        """
        self.parameters["offset"] = 0
        if self.parameters.get("sort", None) != ["date.changed:asc"]:
            raise ValueError('Add "sort": ["date.changed:asc"] to parameters first.')
        self._start_from()
        self.all(limit)

    def _start_from(self):
        """Updates `filter` to start from the latest `date.changed`."""
        res = self.db.c.execute("SELECT json_extract(_raw.date,'$.changed') FROM _raw")
        date_changed = [pd.Timestamp(x[0]) for x in res.fetchall()]
        if date_changed:
            latest = pd.Series(date_changed, dtype=object).max().isoformat()
            old = self.params_old.get("filter", {}).get("conditions", [])
            new = [{"field": "date.changed", "value": {"from": latest}}]
            update = {"filter": {"operator": "AND", "conditions": old + new}}
            self.parameters = self.params_old | update
            logger.debug(latest)

    @decorator.while_loop
    def get_record(self) -> None:
        """Makes a single ReliefWeb API call.

        Notes:
            - Aborts if the daily quota or user-defined limit are reached.
            - Is used as the basic building block for other call methods
                (gets repeated in a while loop).

            Wait times for multiple calls are computed based on `wait_dict`
            and the `totalCount` field from the first API call made. E.g., a
            `totalCount` of 1000 and a `parameters.limit` of 100 means 10 calls
            need to be made, which defaults to a 5-second wait period.

            Inserts data into the `_raw` table after each call.
        """
        if not self.appname:
            raise ValueError(f"appname must be set to make API calls ({self.appname})")
        # check whether to abort
        if self.call_n >= self.limit:
            logger.debug(f"limit reached {self.limit}")
            return False
        self._enforce_quota()
        # automatically set limit
        if self.call_n == 1 and self.limit >= self.quota:
            limit = self.response_json["totalCount"] / self.parameters["limit"]
            limit = math.ceil(limit)
            self.limit = min([limit, self.calls_remaining]) + 1
        # prevent excessive wait for second call
        if self.call_n == 0:
            self._set_wait(5)
        else:
            self._set_wait()
        # make call
        self._offset()
        self._request()
        self._get_field_names()
        self._hash()
        keys = ["time", "took", "totalCount", "count"]
        summary = {k: f"{v:,}" for k, v in self.response_json.items() if k in keys}
        logger.debug(f"{summary}")
        # store output
        if not self.db:
            self.raw[self.call_n] = self.response_json
        else:
            self._insert()
        self._wait()
        self.call_n += 1
        return True

    def _get_field_names(self):
        """Makes a set of field names from response data."""
        self.field_names = set()
        for x in self.response_json["data"]:
            self.field_names.update(list(x["fields"].keys()))

        logger.debug(f"{len(self.field_names)} {sorted(self.field_names)}")

    def _insert_log(self):
        """Inserts a log entry for a call into the `_log` table."""
        record = {
            "api_params_hash": self.hash,
            "api_params": self.parameters,
            "api_input": self.input.name,
            "api_date": self.now,
            "count": self.response_json["count"],
            "total_count": self.response_json["totalCount"],
        }
        self.df_log = pd.DataFrame.from_records([record])
        self.db.insert(self.df_log, "_log")

    def _insert_pdf(self):
        """Updates the `_pdf` table after each call."""
        df = self.df_raw.loc[self.df_raw["file"].notna()].copy()
        if not df.empty:
            # make 1 row per file
            df_flat = pd.json_normalize(df["file"].explode())
            df_flat.rename(columns={"id": "file_id"}, inplace=True)
            # add columns
            ids = [[df.iloc[x]["id"]] * len(df.iloc[x]["file"]) for x in range(len(df))]
            df_flat["id"] = [x for y in ids for x in y]
            df_flat = self.db._add_missing_columns(df_flat, "_pdf")
            # warn for missing columns
            ignore = [
                "preview.url-thumb",
                "preview.url-small",
                "preview.url-large",
                "preview.version",
                "preview.url",
            ]
            self._missing_columns(df_flat, "_pdf", ignore)
            # insert
            self.db.insert(df_flat, "_pdf")

    def _missing_columns(self, df: pd.DataFrame, table: str, ignore: list = []) -> None:
        """Warns if any incoming data is missing a dest. column for a database table.

        Args:
            df: The DataFrame with data to insert.
            table: The destination table.
            ignore: List of unwanted columns to ignore.
        """
        missing_cols = [x for x in df.columns if x not in self.db.tables[table]]
        missing_cols = [x for x in missing_cols if x not in ignore]
        if missing_cols:
            logger.warning(f"{table} has missing columns: {missing_cols}")

    def _insert(self) -> None:
        """Reshapes and inserts ReliefWeb JSON data into a database.

        Notes:
            - Normalizes JSON data and reshapes to a DataFrame.
            - Replaces `-` with `_` in column names.
            - Adds empty columns from the `_raw` table if missing from
                response data.
            - Adds API metadata columns.
        """
        # normalize data
        df = pd.json_normalize(self.response_json["data"], sep="_", max_level=1)
        # manage columns
        df.drop(["fields_id"], axis=1, inplace=True, errors="ignore")
        df.columns = [x.replace("fields_", "") for x in df.columns]
        renamed_columns = {
            col: col.replace("-", "_") for col in df.columns if "-" in col
        }
        df.rename(columns=renamed_columns, inplace=True)
        df["api_params_hash"] = self.hash
        df = self.db._add_missing_columns(df, "_raw")
        # warn for missing columns
        self._missing_columns(df, "_raw", ["score", "vulnerable_groups"])
        # insert data
        self.df_raw = df
        if not df.empty:
            self.db.insert(df, "_raw")
            self._insert_log()
            self._insert_pdf()
        else:
            logger.debug("no more results")
            raise SystemExit()

    def get_pdfs(self, min: int = 0, max: int = 0, wait: int = 5) -> None:
        """Downloads ReliefWeb PDFs based on records in the _pdf table.

        Args:
            min: List start index.
            max: List stop index.
            wait: Minimum seconds to throttle PDF requests (applies if download
                time < `min_wait`).

        Notes:
            - Compares file sizes of downloaded PDFs with Database _pdf.filesize values
                and if changed re-downloads file.
            -Set min and max to run small tests or start from a certain index to ignore
                already downloaded content.
        """
        df = pd.read_sql("SELECT * from _pdf", self.db.conn)
        df["local_file"] = (
            df["id"].astype(str) + "/" + df["file_id"].astype(str) + ".pdf"
        )
        if min > len(df):
            min = len(df)
        if max > len(df) or max == 0:
            max = len(df)
        logger.info(f"downloading files {min}-{max}")
        for x in range(min, max):
            url = df.iloc[x]["url"]
            file = self.pdf_dir / pathlib.Path(df.iloc[x]["local_file"])
            file.parent.mkdir(parents=True, exist_ok=True)
            msg = ""
            if file.exists():
                # size comparison to determine changed content
                if df.iloc[x]["filesize"] == file.stat().st_size:
                    logger.info(f"{x} - skip")
                else:
                    msg = pdf.get_request(file, url, wait)
                    logger.info(f"{x} - {msg}")
            else:
                msg = pdf.get_request(file, url, wait)
                logger.info(f"{x} - {msg}")

    def extract_pdfs(
        self,
        min=0,
        max=0,
        clean: bool = True,
        overwrite: bool = False,
        timeout: int = 30,
    ):
        """Extracts text for PDFs in `ReliefWeb.pdf_dir` and saves to filesystem.

        Args:
            self: ReliefWeb object.
            min: Starting list index.
            max: Ending list index.
            clean: Whether to clean text (see `pdf.clean_text`).
            overwrite: Whether to overwrite if TXT file exists.
            cores: Cores to run in parallel (use `0` to set automatically).

        Notes:
            See `pdf.extract_text` for extracting individual files. Collects file
            list on first execution. Subsequent executions reuse the same file list:
            changes on filesystem won't be detected unless re-instantiated.
        """
        # manage files
        if not self.pdfs:
            pdfs = self.pdf_dir.rglob("*.pdf")
            self.pdfs = [f for f in pdfs]
            logger.info(f"found {len(self.pdfs)} in {self.pdf_dir}")
        nfiles = len(self.pdfs)
        nfiles_total = nfiles
        if min > nfiles:
            min = nfiles
        if max > nfiles or max == 0:
            max = nfiles
        pdfs = self.pdfs[min:max]
        if not overwrite:
            pdfs = [f for f in pdfs if not f.with_suffix(".txt").exists()]
            nfiles = len(pdfs)
            logger.info(f"remaining {len(pdfs)} files")
        else:
            logger.info(f"overwrite {len(pdfs)} files")
        # run extraction
        t0 = perf_counter()
        extractor = pdf.ExtractFiles(clean, overwrite)
        _ = extractor.run(pdfs, timeout)
        t1 = perf_counter()
        logger.info(f"{nfiles} files: {round(t1-t0,2)}s ({nfiles_total} total)")

    def __repr__(self):
        return ""

    def __init__(
        self,
        input,
        database,
        appname=None,
        pdf_dir=None,
        url="https://api.reliefweb.int/v1/reports?appname=",
        quota=1000,
        wait_dict={0: 1, 5: 49, 10: 99, 20: 499, 30: None},
    ):
        super().__init__(source="reliefweb")
        # variables
        self.input = input
        self.url = url
        self.quota = quota
        self.wait_dict = wait_dict
        self.db_name = database
        self.db = None
        self.pdfs = None
        self.raw = {}
        self.cores = int(cpu_count() / 2)
        self.log = {}
        self.limit = 1
        if not appname:
            self.appname = self.config["reliefweb"]["appname"]
        if not pdf_dir:
            self.pdf_dir = pathlib.Path(self.config["reliefweb"]["pdf_dir"])
        # prepare job
        if database:
            self.db = Database(database)
            if not self.db.tables:
                self.db.c.executescript(self.db.schema["reliefweb"]["query"])
                self.db.get_tables()
        self.url = "".join([self.url, self.appname])
        self._get_parameters()
        self.params_old = self.parameters.copy()
