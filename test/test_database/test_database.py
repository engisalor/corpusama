import pathlib
import unittest

import pandas as pd

from corpusama.database.database import Database


class Test_Database(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table_names = sorted(["_attr", "_lang", "_log", "_pdf", "_raw"])
        cls.config_file = "test/config-example.yml"

    def tearDown(self):
        file = pathlib.Path(self.db.config.get("db_name"))
        file.unlink(missing_ok=True)

    def test_instantiate(self):
        """Also tests `get_tables()` superficially."""
        self.db = Database(self.config_file)
        self.assertTrue(self.db.path.exists())
        table_names = sorted(list(self.db.tables.keys()))
        self.assertListEqual(table_names, self.table_names)
        for v in self.db.tables.values():
            self.assertTrue(len(v))

    def test_insert(self):
        self.db = Database(self.config_file)
        df = pd.DataFrame(
            {x: [10, {"A": True}, [None, 1.3]] for x in self.db.tables["_log"]}
        )
        self.db.insert(df, "_log")
        df = pd.read_sql("SELECT * from _log", self.db.conn)
        self.assertTrue(len(df) == 3)


if __name__ == "__main__":
    unittest.main()
