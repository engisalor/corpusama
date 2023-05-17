import json
import pathlib
import time
import unittest

import pandas as pd

from corpusama.database.database import Database
from corpusama.source.reliefweb import ReliefWeb
from corpusama.util import util

config_file = "test/config-example.yml"
example_response = "test/test_source/.call_response.json"
example_raw = "test/test_source/.call_raw.json"
example_log = "test/test_source/.call_log.json"
example_pdf = "test/test_source/.call_pdf.json"


def save_example_call():
    """Saves example response data for local testing.

    Run once before modifying the reliefweb module.
    Example data must contain at least one value for the file field."""

    db = Database(config_file)
    job = ReliefWeb(config_file, db)
    job.get_record()
    with open(example_response, "w") as f:
        json.dump(job.response_json, f)

    tables = ["_raw", "_pdf", "_log"]
    queries = ["SELECT * FROM _raw", "SELECT * FROM _pdf", "SELECT * FROM _log"]
    for x in range(len(tables)):
        df = pd.read_sql(queries[x], job.db.conn)
        name = f"test/test_source/.call{tables[x]}.json"
        df.to_json(name, indent=2)
    pathlib.Path(db.config.get("db_name")).unlink(missing_ok=True)


# save_example_call()


class Test_ReliefWeb(unittest.TestCase):
    def setUp(self):
        self.db = Database(config_file)
        self.job = ReliefWeb(config_file, self.db)

    def tearDown(self):
        pathlib.Path(self.db.config.get("db_name")).unlink(missing_ok=True)

    def test_get_field_names(self):
        self.job.response_json = {"data": [{"fields": {"a": 1, "b": 2}}]}
        self.job._get_field_names()
        self.assertEqual(self.job.field_names, {"a", "b"})

    def test_offset(self):
        self.job.call_n = 2
        self.job.response_json = {"count": 10}
        self.job._offset()
        self.assertEqual(self.job.config.get("parameters").get("offset"), 10)

    def test_inserted_values_match_source(self):
        """Tests that API data has identical columns before and after insertion.

        Does not test insertion itself - see test_database instead"""

        with open(example_response, "r") as f:
            self.job.response_json = json.load(f)
        self.job.now = util.now()
        self.job._get_field_names()
        self.job._hash()
        self.job._insert()
        raw = pd.read_json(example_raw)
        log = pd.read_json(example_log)
        pdf = pd.read_json(example_pdf)
        sql_raw = pd.read_sql("""SELECT id from _raw""", self.job.db.conn)
        sql_log = pd.read_sql("""SELECT api_params_hash from _log""", self.job.db.conn)
        sql_pdf = pd.read_sql("""SELECT id from _pdf""", self.job.db.conn)

        self.assertEqual(
            str(raw["id"].sort_values().values), str(sql_raw["id"].sort_values().values)
        )
        self.assertEqual(
            str(log["api_params_hash"].sort_values().values),
            str(sql_log["api_params_hash"].sort_values().values),
        )
        self.assertEqual(
            str(pdf["id"].sort_values().values), str(sql_pdf["id"].sort_values().values)
        )


@unittest.skip("run API calls manually")
class Test_ReliefWeb_Making_Calls(unittest.TestCase):
    """Superficially tests that API calls function properly."""

    def setUp(self):
        time.sleep(2)
        self.db = Database(config_file)
        self.job = ReliefWeb(config_file, self.db)

    def tearDown(self):
        pathlib.Path(self.db.config.get("db_name")).unlink(missing_ok=True)

    def test_get_record(self):
        self.job.get_record()
        self.assertIsNotNone(self.job.response_json["time"])

    def test_get_all_records(self):
        self.job.get_all_records(1)
        self.assertIsNotNone(self.job.response_json["time"])

    def test_get_new_records(self):
        # job works
        self.job.get_new_records(1)
        self.assertIsNotNone(self.job.response_json["time"])
        # filter gets updated
        self.job.get_new_records(2)
        conditions = self.job.config.get("parameters").get("filter").get("conditions")
        has_filter = [x for x in conditions if x.get("field", None) == "date.changed"]
        self.assertEqual(len(has_filter), 1)

    def test_new_raise_bad_sort_method(self):
        self.job.get_new_records(1)
        del self.job.config["parameters"]["sort"]
        with self.assertRaises(ValueError):
            self.job.get_new_records(1)


if __name__ == "__main__":
    unittest.main()
