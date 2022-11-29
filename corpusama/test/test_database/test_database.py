import unittest

import pandas as pd

from corpusama.database.database import Database


class Test_Database_Variables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database(".temp-28dk37sh2ld83j38.db")
        cls.table_names = ["_log", "_pdf", "_raw", "_vert", "_archive"]

    @classmethod
    def tearDownClass(cls):
        cls.db.path.unlink(missing_ok=True)

    def test_database_instantiate(self):
        self.assertTrue(self.db.path.exists())
        self.assertEqual(self.db.tables, {})

    def test_get_tables_reliefweb(self):
        self.db.c.executescript(self.db.schema["reliefweb"]["query"])
        self.db.get_tables()
        self.assertListEqual(list(self.db.tables.keys()), self.table_names)


class Test_Database_Mock_DF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database(".temp-dk38fj217udksi28.db")
        cls.db.c.executescript(cls.db.schema["reliefweb"]["query"])
        cls.db.get_tables()
        cls.df = pd.DataFrame(
            {x: [10, {"A": True}, [None, 1.3]] for x in cls.db.tables["_log"]}
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.path.unlink(missing_ok=True)

    def test_insert(self):
        """Checks insertion query."""

        self.db.insert(self.df, "_log")
        # TODO


if __name__ == "__main__":
    unittest.main()
