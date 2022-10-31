import unittest

import numpy as np
import pandas as pd

from rwapi import convert


class Test_Convert(unittest.TestCase):
    def test_str_to_obj(self):
        self.assertEqual(convert.str_to_obj('["a", 1, true]'), ["a", 1, True])
        self.assertEqual(convert.str_to_obj("['a', 1, True]"), ["a", 1, True])
        self.assertIs(convert.str_to_obj(None), None)

    def test_nan_to_none(self):
        df = pd.DataFrame(
            {
                "a": [
                    "nonexistent",
                    "Not-None",
                    {"b": ""},
                    [np.nan, "null"],
                    " ",
                    "",
                    "none",
                    "NULL",
                    "NAN",
                    np.nan,
                ]
            }
        )

        df_clean = convert.nan_to_none(df)
        self.assertEqual(
            list(df_clean.a[:5]),
            ["nonexistent", "Not-None", {"b": ""}, [np.nan, "null"], " "],
        )
        self.assertEqual(list(df_clean.a[5:]), [None] * 5)

    def empty_list_to_none(self):
        self.assertIsInstance(convert.empty_list_to_none([1, 2, 3]), list)
        self.assertIsNone(convert.empty_list_to_none([""]))
        self.assertIsInstance(convert.empty_list_to_none({"a": 1}), dict)
        self.assertIsInstance(convert.empty_list_to_none(""), str)


if __name__ == "__main__":
    unittest.main()
