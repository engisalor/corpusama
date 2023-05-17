import pathlib
import unittest

import pandas as pd

from corpusama.corpus import attribute
from corpusama.corpus.corpus import Corpus
from corpusama.util import io as _io
from corpusama.util.util import now


class Test_Attribute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_file = "test/config-example.yml"
        cls.db_file = "sk1827dj3kc9sl29.db"
        df_prepped = {
            "id": {0: '"1"'},
            "multi": {0: '"a|b|c"'},
            "disaster__a__1": {0: '"hello"'},
            "doc_tag": '<doc id="1" disaster__a__1="hello" multi="a|b|c" >',
        }
        cls.df_prepped = pd.DataFrame(df_prepped)

    def test_get_params(self):
        attributes = _io.load_yaml("corpusama/source/params/rw-attribute.yml")
        attr_params = attribute.get_params(attributes)
        self.assertIn("drop", attr_params.keys())

    def test_prep_df(self):
        attrs = {"disaster__type": {"drop": True}}
        attr_params = {"drop": ["disaster__type"], "single": ["id"]}
        df = pd.DataFrame(
            {"id": [1], "disaster": [{"a.1": [" hello"], "type": ["False"]}]}
        )
        df["multi"] = ['["a", "b", "c"]']
        prep_df = attribute.Prep_DF(attrs, attr_params)
        df = prep_df.make(df)
        self.assertEqual(self.df_prepped["disaster__a__1"][0], df["disaster__a__1"][0])
        self.assertEqual(self.df_prepped["id"][0], df["id"][0])
        self.assertEqual(self.df_prepped["multi"][0], df["multi"][0])
        self.assertTrue(self.df_prepped.equals(df))

    def test_doc_tag(self):
        attrs = {"id": "100", "date": "2002", "country": "wld"}
        tag = attribute.doc_tag(attrs)
        self.assertEqual(tag, "<doc id=100 country=wld date=2002 >")

    def test_join_vert(self):
        joined = '<doc id="1">\n1\tCD\t[number]-m\n\n</doc>\n'
        row = {"attr": '<doc id="1">', "vert": "1\tCD\t[number]-m\n"}
        self.assertEqual(attribute.join_vert(row), joined)

    def test_add_years(self):
        ts = now()
        year = str(pd.Timestamp(ts).year)
        dt = {
            "id": {0: '"1"'},
            "disaster__a__1": {0: '"hello"'},
            "date__col": {0: ts},
            "date__col__year": {0: year},
        }
        result = pd.DataFrame(dt)
        df2 = self.df_prepped.copy()
        df2["date__col"] = ts
        df2 = pd.DataFrame.from_dict(df2)
        attribute.add_years(df2)
        self.assertEqual(result["date__col__year"][0], df2["date__col__year"][0])

    def test_export_attribute(self):
        # FIXME still requires default attribute.yaml file to exist
        # make mock data
        tag = '<doc id="1" >'
        # check attributes
        corpus = Corpus(self.config_file)
        corpus.db.c.execute(
            "INSERT INTO _vert (id, vert_date, attr, vert) VALUES('1','2022',?,'abc')",
            (tag,),
        )
        config = corpus.export_attribute(print=True)
        for substr in ["id", "ATTRIBUTE", "DYNTYPE"]:
            self.assertIn(substr, config)

        pathlib.Path(corpus.db.config.get("db_name")).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
