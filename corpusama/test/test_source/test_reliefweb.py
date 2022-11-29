import json
import pathlib
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
    job.run()
    with open(example_response, "w") as f:
        json.dump(job.response_json, f)
    job.df_raw.to_json(example_raw, indent=2)
    job.df_log.to_json(example_log, indent=2)
    job.df_pdf.to_json(example_pdf, indent=2)
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

    @unittest.skip("WARNING: comment this line or logging will break.")
    def test_run_no_database(self):
        job = ReliefWeb(input_yml)
        job.run()
        self.assertIsNotNone(job.response_json["time"])


if __name__ == "__main__":
    unittest.main()
