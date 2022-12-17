"""Functions for converting data types."""
import ast
import json
import logging
import lzma
from html.parser import HTMLParser

import numpy as np
import pandas as pd

from corpusama.util.dataclass import DocBundle

logger = logging.getLogger(__name__)


def to_json_or_str(item: object) -> str:
    """Converts lists/dicts to JSON strings and most other types to ``str``.

    Notes:
        Returns original object if ``bytes``."""

    if isinstance(item, (list, dict)):
        return json.dumps(item)
    elif isinstance(item, bytes):
        return item
    else:
        return str(item)


def str_to_obj(item: str) -> object:
    """Parses an input to an object if possible.

    Notes:
        - Returns non-strings and unparsable strings as-is.
        - Tries to parse strings with ``json.loads``, then ``ast.literal_eval``.
        - May print ``SyntaxWarning: invalid decimal literal`` (can ignore;
            tends to occur when attempting to parse some URL strings)."""

    if not item:
        return item
    elif not isinstance(item, str):
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
    series: pd.Series, strip: bool = True, nan_strings: list = ["none", "null", "nan"]
) -> pd.Series:
    """Converts ``np.nan``, ``"NULL"`` and similar to ``None``.

    Args:
        series: A series to process.
        strip: Strip leading/trailing string whitespace.
        nan_strings: Strings to consider as ``None`` values (case insensitive)."""

    bad_NAs = [np.nan, r"^\s*$"] + [f"(?i)^{x}$" for x in nan_strings]
    if strip:
        series = series.apply(lambda x: x.strip() if isinstance(x, str) else x)
    if series.any():
        series = series.replace(to_replace=bad_NAs, value=None, regex=True)
    else:
        series = pd.Series([None for x in series], dtype=object)
    return series


def empty_list_to_none(item: list) -> None:
    """Converts an empty list to ``None``, otherwise returns as-is."""

    if isinstance(item, list):
        if [x for x in item if x]:
            return item
        else:
            return None
    else:
        return item


def list_to_string(item: list, separator: str = "|", replacement: str = None) -> str:
    """Joins list items with a separator (ignores other object types).

    Args:
        item: List of values.
        separator: Symbol (corresponds to Sketch Engine's ``MULTISEP``).
        replacement: String to replace preexisting cases of ``separator``.

    Notes:
        If ``replacement=None``, function raises an error when an input string already
        contains ``separator``. If such an error occurs, consider excluding the
        attribute from the corpus by adding ``drop: true`` to its entry in the
        ``attribute.yaml``. Otherwise, consider percent encoding for replacement
        values, e.g., ``"%7C"`` to replace ``"|"``."""

    if isinstance(item, list):
        if [x for x in item if separator in str(x)]:
            if not replacement:
                raise ValueError(f"{separator} exists in {item}")
            item = [str(x).replace(separator, replacement) for x in item]
            logger.warning(f"{separator} replaced with '{replacement}' in {item}")
        item = separator.join([str(x) for x in item])
    return item


def html_to_text(html: str) -> str:
    """Extracts text from an HTML string."""

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
    """Converts a ``DocBundle`` to a ``DataFrame``.

    See Also:
        ``util.dataclass.DocBundle``"""

    df = pd.DataFrame({"id": bundle.id, "vert": bundle.doc})
    df["vert_date"] = bundle.date
    df["attr"] = None
    return df


def xz_to_str(obj: bytes) -> str:
    """Decompresses an xz bytes object to a string."""

    return lzma.decompress(obj)
