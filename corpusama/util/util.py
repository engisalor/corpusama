"""Utility functions."""
import logging
import pathlib
import re
from xml.sax.saxutils import quoteattr  # nosec

import pandas as pd
from defusedxml import ElementTree

logger = logging.getLogger(__name__)


def now() -> str:
    """Returns an ISO timestamp in UTC time rounded to the second."""

    return pd.Timestamp.now(tz="UTC").round("S").isoformat()


def join_results(results: tuple, columns: list) -> pd.DataFrame:
    """Makes a DataFrame from the fetched results of a join query.

    Args:
        results: Query results in tuples of tuples.
        columns: Column names corresponding to each tuple value.

    Notes:
        Removes any duplicate column names."""

    df = pd.DataFrame.from_records(results, columns=columns)
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def limit_runs(run: int, runs: int) -> bool:
    """Returns a boolean to set whether a while loop repeats."""

    if run == runs:
        logger.debug(f"{run+1}")
        return False
    else:
        return True


def count_log_lines(message: str, log_file: str) -> int:
    """Counts the occurrences of a message in a log file.

    Args:
        message: The message to search for.
        log_file: The log filepath.

    Returns:
        An integer with the total number of occurrences found.

    Notes:
        Used to keep track of how many calls have been made for an API."""

    calls_made = 0
    if pathlib.Path(log_file).exists():
        with open(pathlib.Path(log_file), "r") as f:
            daily_log = f.readlines()
        for x in daily_log:
            if message in x:
                calls_made += 1
    return calls_made


def unique_xml_attrs(tags: list) -> set:
    """Returns a set of unique XML attributes.

    Args:
        tags: The list of document tags (XML strings) for corpus content."""

    all_attrs = set()
    for x in range(len(tags)):
        tree = ElementTree.fromstring(tags[x])
        all_attrs.update(tree.attrib.keys())
    return all_attrs


def clean_xml_tokens(
    item,
    invalid_tokens: list = ["\x0b", "\x0b", "\x0c", "\x0c", "\x1c", "\x1d", "\x1e"],
):
    """Removes invalid XML tokens from a string, otherwise returns as-is.

    Args:
        invalid_tokens: Tokens to remove before making XML strings.

    Notes:
        - Encodes strings with ``xml.sax.saxutils.quoteattr``:
            may require decoding for URLs & other escaped characters"""

    if isinstance(item, str):
        return re.sub(f"[{'|'.join(invalid_tokens)}]", "", item)
    else:
        return item


def xml_quoteattr(item: str) -> str:
    """Converts item to an XML attribute string (and strips whitespace).

    Args:
        item: an object convertible to str (ignores ``None``).

    See Also:
        - ``xml.sax.saxutils.quoteattr``"""

    if item:
        return quoteattr(str(item).strip())
    else:
        return item
