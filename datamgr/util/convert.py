import ast
import json
from html.parser import HTMLParser

import numpy as np
import pandas as pd


def str_to_obj(item):
    """Parses a item into an object if possible using json or literal_eval."""

    if not item:
        return item
    elif isinstance(item, (int, float, bytes)):
        return item
    else:
        try:
            return json.loads(item)
        except (json.JSONDecodeError, TypeError):
            try:
                return ast.literal_eval(item)
            except (SyntaxError, ValueError):
                return item


def nan_to_none(
    df: pd.DataFrame, strip=True, nan_strings=["none", "null", "nan"]
) -> pd.DataFrame:
    """Converts df empty cells, np.nan, 'NULL' and similar to None.

    - `strip=True` strips leading/trailing string whitespace
    - `nan_strings` sets strings to consider as None values (case insensitive)"""

    bad_NAs = [np.nan, r"^\s*$"] + [f"(?i)^{x}$" for x in nan_strings]
    if strip:
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    return df.replace(to_replace=bad_NAs, value=None, regex=True)


def empty_list_to_none(item):
    """Converts an empty list to None, otherwise returns item."""

    if isinstance(item, list):
        if [x for x in item if x]:
            return item
        else:
            return None
    else:
        return item


def list_to_string(item, separator="|"):
    """Joins list items with a separator (ignores other object types)."""

    if isinstance(item, list):
        if [x for x in item if separator in str(x)]:
            raise ValueError(f"{separator} exists in {item}: use another separator")
        return separator.join([str(x) for x in item])
    else:
        return item


def html_to_text(html):
    """Extracts text from a html string."""

    class HTMLFilter(HTMLParser):
        text = ""

        def handle_data(self, data):
            self.text += data

    if isinstance(html, str):
        f = HTMLFilter()
        f.feed(html)
        return f.text
    else:
        return html
