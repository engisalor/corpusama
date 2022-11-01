import ast
import json

import numpy as np
import pandas as pd


def str_to_obj(item):
    """Parses a string into an object if possible using json or literal_eval."""

    if not item:
        return item
    elif isinstance(item, (int, float)):
        return item
    else:
        try:
            return json.loads(item)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(item)
            except (SyntaxError, ValueError):
                return item


def nan_to_none(df: pd.DataFrame) -> pd.DataFrame:
    """Converts df empty cells, np.nan, 'NULL' and similar to None."""

    bad_NAs = [np.nan] + [f"(?i)^{x}$" for x in ["", "none", "null", "nan"]]
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
