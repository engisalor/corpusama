import unittest

import numpy as np
import pandas as pd

from datamgr.util import flatten


class Test_Flatten(unittest.TestCase):
    def test_flatten_list_of_dict(self):
        ls_of_dict = [
            {
                "name": "Hungary",
                "location": {"lon": 19.5, "lat": 47.06},
                "id": 117,
                "shortname": "Hungary",
                "iso3": "hun",
                "primary": True,
            },
            {
                "name": "Ukraine",
                "location": {"lon": 31.32, "lat": 49.32},
                "id": 241,
                "shortname": "Ukraine",
                "iso3": "ukr",
            },
            {
                "name": "World",
                "id": 254,
                "shortname": "World",
                "iso3": "wld",
                "primary": True,
            },
        ]
        flat_dict = {
            "name": ["Hungary", "Ukraine", "World"],
            "location": {"lon": [19.5, 31.32, np.nan], "lat": [47.06, 49.32, np.nan]},
            "id": [117, 241, 254],
            "shortname": ["Hungary", "Ukraine", "World"],
            "iso3": ["hun", "ukr", "wld"],
            "primary": [True, np.nan, True],
        }
        self.assertEqual(str(flatten.list_of_dict(ls_of_dict)), str(flat_dict))

    def test_flatten_dataframe(self):
        df_nested = pd.read_json("datamgr/test/test_util/test_flatten-0.json")
        df_flattened = pd.read_json("datamgr/test/test_util/test_flatten-1.json")
        df = flatten.dataframe(df_nested)
        self.assertEqual(str(df), str(df_flattened))


if __name__ == "__main__":
    unittest.main()
