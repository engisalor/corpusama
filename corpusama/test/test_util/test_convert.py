import unittest

import numpy as np
import pandas as pd

from corpusama.util import convert


class Test_Convert(unittest.TestCase):
    def test_str_to_obj(self):
        self.assertEqual(convert.str_to_obj("6c6781143df3f3ab"), "6c6781143df3f3ab")
        self.assertEqual(convert.str_to_obj(1.1), 1.1)
        self.assertEqual(convert.str_to_obj("asdf"), "asdf")
        self.assertEqual(convert.str_to_obj('["a", 1, true]'), ["a", 1, True])
        self.assertEqual(convert.str_to_obj(r"{'a':'b'}"), {"a": "b"})
        self.assertIs(convert.str_to_obj(None), None)

    def test_nan_to_none(self):
        df = pd.DataFrame(
            {
                "a": [
                    "nonexistent",
                    " Not-None ",
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

        df_clean = df.apply(convert.nan_to_none, strip=True)
        self.assertEqual(
            list(df_clean.a[:4]),
            ["nonexistent", "Not-None", {"b": ""}, [np.nan, "null"]],
        )
        df_clean_no_strip = df.apply(convert.nan_to_none, strip=False)
        self.assertEqual(
            list(df_clean_no_strip.a[:4]),
            ["nonexistent", " Not-None ", {"b": ""}, [np.nan, "null"]],
        )
        self.assertEqual(list(df_clean.a[4:]), [None] * 6)

    def test_empty_list_to_none(self):
        self.assertIsInstance(convert.empty_list_to_none([1, 2, 3]), list)
        self.assertIsNone(convert.empty_list_to_none([""]))
        self.assertIsInstance(convert.empty_list_to_none({"a": 1}), dict)
        self.assertIsInstance(convert.empty_list_to_none(""), str)

    def test_list_to_string(self):
        ls = [1, 1.3, None, np.nan, "text"]
        self.assertEqual(
            convert.list_to_string(ls, separator="|"), "1|1.3|None|nan|text"
        )
        self.assertEqual(convert.list_to_string(None), None)
        self.assertEqual(convert.list_to_string(1), 1)
        self.assertEqual(convert.list_to_string({1: 1}), {1: 1})
        with self.assertRaises(ValueError):
            convert.list_to_string(["a|b|c"], separator="|")

    def test_html_to_text(self):
        html = "<p>Encyclopedias have existed for around 2,000 years. (Wikipedia)</p>"
        text = "Encyclopedias have existed for around 2,000 years. (Wikipedia)"
        self.assertEqual(convert.html_to_text(html), text)
        self.assertEqual(convert.html_to_text(1), 1)
        self.assertEqual(convert.html_to_text(None), None)
        self.assertEqual(convert.html_to_text([1, 2, 3]), [1, 2, 3])
        self.assertEqual(convert.html_to_text({"a": "b"}), {"a": "b"})
        self.assertTrue(np.isnan(convert.html_to_text(np.nan)))


if __name__ == "__main__":
    unittest.main()
