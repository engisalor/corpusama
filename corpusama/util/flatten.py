"""Functions to flatten nested lists and dictionaries."""
import logging

import pandas as pd

from corpusama.util import convert

logger = logging.getLogger(__name__)


def list_of_dict(ls: list) -> dict:
    """Recursively converts a list of dicts to a dict of lists.

    Notes:
        Returns objects as-is if they're not lists or dicts."""

    def _flatten(ls):
        if not isinstance(ls, list):
            return ls
        else:
            if dict not in [type(x) for x in ls]:
                return ls
            # for [dict, dict, nan] objects
            else:
                # convert nan to empty dict
                ls = [x if isinstance(x, dict) else {} for x in ls]
                # convert list of dicts to dict of lists
                dt = pd.DataFrame(ls).to_dict(orient="list")
                # continue with recursion if needed
                for k, v in dt.items():
                    dt[k] = _flatten(v)
                return dt

    return _flatten(ls)


def dataframe(
    df: pd.DataFrame, separator: str = "__", reset_index: bool = True
) -> pd.DataFrame:
    """Flattens a DataFrame with list and dictionary objects.

    Args:
        df: The DataFrame to flatten.
        separator: The character(s) to add between parent and child column names.
        reset_index: Reset the DataFrame index if needed before continuing.

    Notes:
        Deletes nested source columns after completion."""

    # flatten data
    if reset_index:
        df.reset_index(drop=True, inplace=True)
    df = df.map(convert.str_to_obj)
    for col in df.columns:
        # logging.debug(f"column: {col}")  # for debugging
        prefix = "".join([col, separator])
        df[col] = df[col].apply(list_of_dict)
        df = pd.concat([df, pd.json_normalize(df[col]).add_prefix(prefix)], axis=1)
    # drop original list of dict columns
    for col in df.columns:
        types = set([type(x) for x in df[col]])
        if dict in types:
            df.drop(col, inplace=True, axis=1)

    return df
