import ast
import json
import lzma
from html.parser import HTMLParser

import numpy as np
import pandas as pd

from datamgr.util.dataclass import DocBundle


def to_json_or_str(item):
    """Converts lists/dicts to JSON str and other types to str."""

    if isinstance(item, (list, dict)):
        return json.dumps(item)
    elif isinstance(item, bytes):
        return item
    else:
        return str(item)


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
    series: pd.Series, strip=True, nan_strings=["none", "null", "nan"]
) -> pd.Series:
    """Converts np.nan, 'NULL' and similar to None.

    - `strip=True` strips leading/trailing string whitespace
    - `nan_strings` sets strings to consider as None values (case insensitive)"""

    bad_NAs = [np.nan, r"^\s*$"] + [f"(?i)^{x}$" for x in nan_strings]
    if strip:
        series = series.apply(lambda x: x.strip() if isinstance(x, str) else x)
    if series.any():
        series = series.replace(to_replace=bad_NAs, value=None, regex=True)
    else:
        series = [None for x in series]
    return series


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


def docbundle_to_df(bundle: DocBundle) -> pd.DataFrame:
    """Converts a DocBundle to a DataFrame."""

    df = pd.DataFrame({"id": bundle.id, "vert": bundle.doc})
    df["vert_date"] = bundle.date
    df["attr"] = None
    return df


def xz_to_str(obj):
    """Converts an xz compressed bytes object to a string."""

    return lzma.decompress(obj)
