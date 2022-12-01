import json
import pathlib
import time
import unittest

import pandas as pd

from corpusama.source.reliefweb import ReliefWeb
from corpusama.util import util

input_yml = "corpusama/test/test_source/call.yml"
database = "3kd82kc843ke1la0.db"
example_response = "corpusama/test/test_source/.call_response.json"
example_raw = "corpusama/test/test_source/.call_raw.json"
example_log = "corpusama/test/test_source/.call_log.json"
example_pdf = "corpusama/test/test_source/.call_pdf.json"


def save_example_call():
    """Saves example response data for local testing.

    Run once before modifying the reliefweb module.
    Example data must contain at least one value for the file field."""

    job = ReliefWeb(input_yml, database)
    job.one()
    with open(example_response, "w") as f:
        json.dump(job.response_json, f)

    tables = ["_raw", "_pdf", "_log"]
    queries = ["SELECT * FROM _raw", "SELECT * FROM _pdf", "SELECT * FROM _log"]
    for x in range(len(tables)):
        df = pd.read_sql(queries[x], job.db.conn)
        name = f"corpusama/test/test_source/.call{tables[x]}.json"
        df.to_json(name, indent=2)
    pathlib.Path(f"data/{database}").unlink(missing_ok=True)


class Test_ReliefWeb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.job = ReliefWeb(input_yml)

    @classmethod
    def tearDownClass(cls):
        dir = pathlib.Path("data")
        filepath = dir / database
        filepath.unlink(missing_ok=True)

    def test_get_field_names(self):
        self.job.response_json = {"data": [{"fields": {"a": 1, "b": 2}}]}
        self.job._get_field_names()
        self.assertEqual(self.job.field_names, {"a", "b"})

    def test_offset(self):
        self.job.call_n = 2
        self.job.response_json = {"count": 10}
        self.job._offset()
        self.assertEqual(self.job.parameters["offset"], 10)

    def test_inserted_values_match_source(self):
        """Tests that API data has identical columns before and after insertion.

        Does not test insertion itself - see test_database instead"""

        job = ReliefWeb(input_yml, database)
        with open(example_response, "r") as f:
            job.response_json = json.load(f)
        job.now = util.now()
        job._get_field_names()
        job._hash()
        job.insert()
        raw = pd.read_json(example_raw)
        log = pd.read_json(example_log)
        pdf = pd.read_json(example_pdf)
        sql_raw = pd.read_sql("""SELECT id from _raw""", job.db.conn)
        sql_log = pd.read_sql("""SELECT api_params_hash from _log""", job.db.conn)
        sql_pdf = pd.read_sql("""SELECT id from _pdf""", job.db.conn)

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


@unittest.skip("WARNING: comment this line or logging will break when testing.")
class Test_ReliefWeb_Making_Calls(unittest.TestCase):
    """Superficially tests that API calls function properly."""

    @classmethod
    def setUpClass(cls):
        cls.job = ReliefWeb(input_yml)

    def setUp(cls):
        time.sleep(2)
        dir = pathlib.Path("data")
        filepath = dir / database
        filepath.unlink(missing_ok=True)

    def test_run_one(self):
        self.job.one()
        self.assertIsNotNone(self.job.response_json["time"])

    def test_run_all(self):
        self.job.all(1)
        self.assertIsNotNone(self.job.response_json["time"])

    def test_run_new(self):
        # job works
        job = ReliefWeb(input_yml, database)
        job.new(1)
        self.assertIsNotNone(job.response_json["time"])
        # filter gets updated
        job.new(2)
        conditions = job.parameters.get("filter").get("conditions")
        has_filter = [x for x in conditions if x.get("field", None) == "date.changed"]
        self.assertEqual(len(has_filter), 1)

    def test_new_raise_bad_sort_method(self):
        job = ReliefWeb(input_yml, database)
        job.new(1)
        del job.parameters["sort"]
        with self.assertRaises(ValueError):
            job.new(1)


if __name__ == "__main__":
    unittest.main()
