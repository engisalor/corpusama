import logging
import pathlib

import pandas as pd

from rwapi.call import Call
from rwapi.db import Database

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

        call_x = Call(input, n_calls, appname, url, quota, wait_dict, self.log_level)
        for call_n in range(n_calls):
            call_x.call_n = call_n
            call_x._quota_enforce()
            call_x._increment_parameters()
            call_x._request()
            call_x._hash()
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
        records["params_hash"] = self.call_x.hash
        for x in [x for x in self.db.columns["records"] if x not in records.columns]:
            records[x] = None
        self.db._insert(records, "records")

    def _insert_log(self):
        """Inserts history of calls."""

        record = [
            {
                "params_hash": self.call_x.hash,
                "parameters": self.call_x.parameters,
                "rwapi_input": self.call_x.input.name,
                "rwapi_date": self.call_x.now,
                "count": self.call_x.response_json["count"],
                "total_count": self.call_x.response_json["totalCount"],
            }
        ]
        df = pd.DataFrame.from_records(record)
        self.db._insert(df, "call_log")

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
        self.db = Database(db, log_level)
