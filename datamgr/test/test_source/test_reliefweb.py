import json
import pathlib
import unittest

import pandas as pd

from datamgr.source.reliefweb import ReliefWeb

input_yml = "datamgr/test/test_source/call.yml"
database = "3kd82kc843ke1la0.db"
example_response = "datamgr/test/test_source/.call_response.json"
example_raw = "datamgr/test/test_source/.call_raw.json"
example_log = "datamgr/test/test_source/.call_log.json"
example_pdf = "datamgr/test/test_source/.call_pdf.json"


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
    pathlib.Path(database).unlink(missing_ok=True)


class Test_Call(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.job = ReliefWeb(input_yml)

    @classmethod
    def tearDownClass(cls):
        pathlib.Path("data/" + database).unlink(missing_ok=True)

    def test_get_field_names(self):
        self.job.response_json = {"data": [{"fields": {"a": 1, "b": 2}}]}
        self.job._get_field_names()
        self.assertEqual(self.job.field_names, {"a", "b"})

    def test_offset(self):
        self.job.call_n = 2
        self.job.response_json = {"count": 10}
        self.job._offset()
        self.assertEqual(self.job.parameters["offset"], 10)

    def test_insert_df_creation(self):
        """Tests that dfs for data insertion are properly constructed.

        Does not test successful insertion into a database.
        (See the tests in test_database regarding insert commands.)"""

        job = ReliefWeb(input_yml, database)
        with open(example_response, "r") as f:
            job.response_json = json.load(f)
        job.now = pd.Timestamp.now().round("S").isoformat()
        job._get_field_names()
        job._hash()
        job.insert()
        raw = pd.read_json(example_raw)
        log = pd.read_json(example_log)
        pdf = pd.read_json(example_pdf)
        self.assertTrue(job.df_raw["id"].equals(raw["id"]))
        self.assertTrue(job.df_log["params_hash"].equals(log["params_hash"]))
        self.assertTrue(job.df_pdf["id"].equals(pdf["id"]))

    @unittest.skip("WARNING: comment this line or logging will break.")
    def test_run_no_database(self):
        job = ReliefWeb(input_yml)
        job.run()
        self.assertIsNotNone(job.response_json["time"])


if __name__ == "__main__":
    unittest.main()
