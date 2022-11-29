import pathlib
import unittest

import pandas as pd

from corpusama.corpus import attribute
from corpusama.corpus.corpus import Corpus
from corpusama.util.util import now


class Test_Corpus_(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = "sk1827dj3kc9sl29.db"
        df_prepped = {"id": {0: 1}, "new__a__1": {0: "9"}}
        cls.df_prepped = pd.DataFrame(df_prepped)

    @classmethod
    def tearDownClass(cls):
        dir = pathlib.Path("data")
        filepath = dir / cls.db_file
        filepath.unlink()

    def test_prep_df(self):
        df = pd.DataFrame({"id": [1], "new": [{"a.1": [9], "b-1": [False]}]})
        df = attribute.prep_df(df, drop_attr=["new__b_1"])
        self.assertTrue(self.df_prepped.equals(df))

    def test_doc_tag(self):
        attrs = {"id": 100, "date": "2002", "country": "wld"}
        tag = attribute.doc_tag(attrs)
        self.assertEqual(tag, '<doc id="100" country="wld" date="2002" >')

    def test_join_vert(self):
        joined = '<doc id="1">\n1\tCD\t[number]-m\n\n</doc>\n'
        row = {"attr": '<doc id="1">', "vert": "1\tCD\t[number]-m\n"}
        self.assertEqual(attribute.join_vert(row), joined)

    def test_add_years(self):
        ts = now()
        year = str(pd.Timestamp(ts).year)
        dt = {
            "id": {0: 1},
            "new__a__1": {0: "9"},
            "date__col": {0: ts},
            "date__col__year": {0: year},
        }
        result = pd.DataFrame(dt)
        new = self.df_prepped.copy()
        new["date__col"] = ts
        attribute.add_years(new)
        self.assertTrue(result.equals(new))

    def test_export_attribute(self):
        # make mock data
        tag = '<doc id="1" hash="sk182kdk" date="2022" source="A source" >'
        # check attributes
        corpus = Corpus(self.db_file)
        corpus.db.c.execute(
            """
        CREATE TABLE _vert (
        'id' INTEGER PRIMARY KEY,
        'vert_date' TEXT NOT NULL,
        'attr' TEXT,
        'vert' TEXT NOT NULL)"""
        )
        corpus.db.c.execute(
            "INSERT INTO _vert (id, vert_date, attr, vert) VALUES('1','2022',?,'abc')",
            (tag,),
        )
        config = corpus.export_attribute(print=True)
        for substr in ["hash", "id", "date", "source", "ATTRIBUTE"]:
            self.assertIn(substr, str(config))
        pathlib.Path(self.db_file).unlink(missing_ok=True)
