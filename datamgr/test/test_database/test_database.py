import unittest

import pandas as pd

from datamgr.database.database import Database

reliefweb_tables = {
    "rw_log": [
        "params_hash",
        "parameters",
        "api_input",
        "api_date",
        "count",
        "total_count",
    ],
    "rw_pdf": [
        "id",
        "file_id",
        "description",
        "filename",
        "filesize",
        "url",
        "mimetype",
    ],
    "rw_corpus": ["id", "vert", "last_mod"],
    "rw_raw": [
        "params_hash",
        "id",
        "country",
        "date",
        "disaster",
        "disaster_type",
        "feature",
        "file",
        "format",
        "headline",
        "image",
        "language",
        "ocha_product",
        "origin",
        "primary_country",
        "source",
        "status",
        "theme",
        "title",
        "url",
        "url_alias",
        "vulnerable_group",
        "body",
        "body_html",
    ],
}


class Test_Database_Variables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database(".temp-28dk37sh2ld83j38.db")
        cls.reliefweb_tables = reliefweb_tables

    @classmethod
    def tearDownClass(cls):
        cls.db.path.unlink(missing_ok=True)

    def test_database_instantiate(self):
        self.assertTrue(self.db.path.exists())
        self.assertEqual(self.db.tables, {})

    def test_get_tables_reliefweb(self):
        self.db.c.executescript(self.db.queries["rw_create"]["query"])
        self.db.get_tables()
        self.assertDictEqual(self.db.tables, self.reliefweb_tables)


class Test_Database_Mock_DF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database(".temp-dk38fj217udksi28.db")
        cls.db.c.executescript(cls.db.queries["rw_create"]["query"])
        cls.db.get_tables()
        cls.df = pd.DataFrame(
            {x: [10, {"A": True}, [None, 1.3]] for x in cls.db.tables["rw_log"]}
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.path.unlink(missing_ok=True)

    def test_insert_and_get_df(self):
        """Compares inserted df with retrieved df.

        Since insert() cleans and standardizes data and
        get_df() converts SQL string values to objects again,
        db.df and db won't be identical in real applications."""

        self.db.insert(self.df, "rw_log")
        self.db.get_df("rw_log")
        self.assertTrue(self.db.df["rw_log"].equals(self.df))


if __name__ == "__main__":
    unittest.main()
