import unittest

import pandas as pd

from corpusama.corpus import attribute
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
        attr_params = attribute._get_params(attributes)
        self.assertIn("drop", attr_params.keys())

    def test_prep_df(self):
        attrs = {"disaster__type": {"drop": True}}
        attr_params = {"drop": ["disaster__type"], "single": ["id"]}
        # without file_id
        df = pd.DataFrame(
            {"id": [2], "disaster": [{"a.1": [" hello"], "type": ["False"]}]}
        )
        df["multi"] = ['["a", "b", "c"]']
        prep_df = attribute.Prep_DF(attrs, attr_params)
        df = prep_df.make(df)
        ref = '<doc id="2" file_id="FILE_ID" disaster__a__1="hello" multi="a|b|c" >'
        self.assertEqual(df["doc_tag"][0], ref)
        # with file_id
        df = prep_df.make(pd.DataFrame({"id": [2], "file_id": [1234]}))
        self.assertEqual(df["doc_tag"][0], '<doc id="2" file_id="1234" >')

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
        attribute._add_years(df2)
        self.assertEqual(result["date__col__year"][0], df2["date__col__year"][0])


# def test_export_attribute(self):
#     # FIXME still requires default attribute.yaml file to exist
#     # make mock data
#     tag = '<doc id="1" >'
#     # check attributes
#     corpus = Corpus(self.config_file)
#     corpus.db.c.execute(
# "INSERT INTO _vert (id, file_id, lang, vert_date, attr, vert)
# VALUES('1','0','en','2022',?,'abc')",
#         (tag,),
#     )
#     config = corpus.export_attribute(print=True)
#     for substr in ["id", "ATTRIBUTE", "DYNTYPE"]:
#         self.assertIn(substr, config)

#     pathlib.Path(corpus.db.config.get("db_name")).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
