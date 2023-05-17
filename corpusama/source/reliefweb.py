"""A module for managing ReliefWeb API calls and PDFs."""
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


class ReliefWeb(Call):
    """Manages data retrieval for ReliefWeb."""

    def _offset(self) -> None:
        """Adjusts the offset parameter and halts a job if no more results."""
        if self.call_n > 0:
            self.config["parameters"]["offset"] += self.response_json["count"]
            if self.response_json["count"] == 0:
                logging.debug("no more results")
                raise SystemExit()
        logging.debug(self.config.get("parameters").get("offset"))

    def get_all_records(self, stop_at: int = 0) -> None:
        """Makes repeated calls in batches, incrementing the `offset` field.

        Args:
            stop_at: The maximum number of calls to make (0 = as many as possible).

        Notes:
            - Makes calls using `self.config["parameters"]`
            - Overwrites existing database raw content and starts over again if
                aborted (not usable to progressively download content).
        """
        self.call_n = 0
        self.stop_at = stop_at
        if not self.stop_at:
            self.stop_at = self.config.get("quota")
        self.get_record()

    def get_new_records(self, stop_at: int = 0) -> None:
        """Makes repeated calls starting from the latest `date.changed`.

        Args:
            stop_at: The maximum number of calls to make (0 = as many as possible).

        Notes:
            - `self.config["parameters"]` must include `"sort": ["date.changed:asc"]`.
            - Calls are made starting with the oldest `date.changed` value.
            - Modified content is overwritten if a newer `date.changed` is found.
            - Can be aborted and restarted safely, continuing at last made call.
        """
        self.config["parameters"]["offset"] = 0
        if self.config.get("parameters").get("sort", None) != ["date.changed:asc"]:
            raise ValueError('Add `"sort": ["date.changed:asc"]` to parameters first.')
        self._start_from()
        self.get_all_records(stop_at)

    def _start_from(self):
        """Updates `filter` to start from the latest `date.changed`."""
        res = self.db.c.execute("SELECT json_extract(_raw.date,'$.changed') FROM _raw")
        date_changed = [pd.Timestamp(x[0]) for x in res.fetchall()]
        if date_changed:
            latest = pd.Series(date_changed, dtype=object).max().isoformat()
            old = self.params_old.get("filter", {}).get("conditions", [])
            new = [{"field": "date.changed", "value": {"from": latest}}]
            update = {"filter": {"operator": "AND", "conditions": old + new}}
            self.config["parameters"] = self.params_old | update
            logging.debug(latest)

    @decorator.while_loop
    def get_record(self) -> None:
        """Makes a single ReliefWeb API call.

        Notes:
            - Aborts if the daily quota or user-defined stop_at are reached.
            - Is used as the basic building block for other call methods.

            Wait times for multiple calls are computed based on `wait_dict`
            and the `totalCount` field from the first API call made. E.g., a
            `totalCount` of 1000 and a `parameters.stop_at` of 100 means 10 calls
            need to be made, which defaults to a 5-second wait period.

            Inserts data into the `_raw` table after each call.
        """
        # check whether to abort
        if self.call_n >= self.stop_at:
            logging.debug(f"limit reached {self.stop_at}")
            return False
        self._enforce_quota()
        # automatically set stop_at
        if self.call_n == 1 and self.stop_at >= self.config.get("quota"):
            stop_at = self.response_json["totalCount"] / self.config.get(
                "parameters"
            ).get("limit")
            stop_at = math.ceil(stop_at)
            self.stop_at = min([stop_at, self.calls_remaining]) + 1
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
        # log summary
        keys = ["time", "took", "totalCount", "count"]
        summary = {k: f"{v:,}" for k, v in self.response_json.items() if k in keys}
        logging.debug(f"{summary}")
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

        logging.debug(f"{len(self.field_names)} {sorted(self.field_names)}")

    def _insert_log(self):
        """Inserts a log entry for a call into the `_log` table."""
        record = {
            "api_params_hash": self.hash,
            "api_params": self.config.get("parameters"),
            "config_file": self.config.get("config_file"),
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
        """Warns if any incoming data lacks a column for a database table.

        Args:
            df: The DataFrame with data to insert.
            table: The destination table.
            ignore: List of unwanted columns to ignore.
        """
        missing_cols = [x for x in df.columns if x not in self.db.tables[table]]
        missing_cols = [x for x in missing_cols if x not in ignore]
        if missing_cols:
            logging.warning(f"{table} has missing columns: {missing_cols}")

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
            col: col.replace("-", "_").replace(".", "_") for col in df.columns
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
            logging.debug("no more results")
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
        logging.info(f"downloading files {min}-{max}")
        for x in range(min, max):
            url = df.iloc[x]["url"]
            file = pathlib.Path(self.config.get("pdf_dir")) / pathlib.Path(
                df.iloc[x]["local_file"]
            )
            file.parent.mkdir(parents=True, exist_ok=True)
            msg = ""
            if file.exists():
                # size comparison to determine changed content
                if df.iloc[x]["filesize"] == file.stat().st_size:
                    logging.info(f"{x} - skip")
                else:
                    msg = pdf.get_request(file, url, wait)
                    logging.info(f"{x} - {msg}")
            else:
                msg = pdf.get_request(file, url, wait)
                logging.info(f"{x} - {msg}")

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
            pdf_dir = pathlib.Path(self.config.get("pdf_dir"))
            pdfs = pdf_dir.rglob("*.pdf")
            self.pdfs = [f for f in pdfs]
            logging.info(f"found {len(self.pdfs)} in {pdf_dir}")
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
            logging.info(f"remaining {len(pdfs)} files")
        else:
            logging.info(f"overwrite {len(pdfs)} files")
        # run extraction
        t0 = perf_counter()
        extractor = pdf.ExtractFiles(clean, overwrite)
        _ = extractor.run(pdfs, timeout)
        t1 = perf_counter()
        logging.info(f"{nfiles} files: {round(t1-t0,2)}s ({nfiles_total} total)")

    def __init__(
        self,
        config: str,
        db: Database,
    ):
        super().__init__(config=config)
        self.pdfs = None
        self.stop_at = 1
        self.raw = {}
        self.cores = int(cpu_count() / 2)
        self.log = {}
        self.params_old = self.config.get("parameters")
        self.db = db
