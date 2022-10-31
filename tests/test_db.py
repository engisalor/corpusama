import os
import unittest

import pandas as pd

from rwapi.db import Database


class Test_Database(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = "tests/temp.db"
        cls.db = Database("tests/test.db")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_db):
            os.remove(cls.temp_db)

    def test_get_columns(self):
        self.db.get_columns()
        self.assertEqual(len(self.db.columns), 3)

    def test_make_tables(self):
        self.temp_db = Database(self.temp_db)
        self.temp_db.make_tables()
        self.temp_db.c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = sorted([name[0] for name in self.temp_db.c.fetchall()])
        self.assertListEqual(tables, ["call_log", "pdfs", "records"])

    def test_make_dfs(self):
        self.db.make_dfs()
        for v in self.db.dfs.values():
            self.assertIsInstance(v, pd.DataFrame)
            self.assertGreater(len(v), 0)

    def test_orphan_ids(self):
        self.db.orphan_ids()
        self.assertEqual(len(self.db.orphans["ids"]), 1)


if __name__ == "__main__":
    unittest.main()
