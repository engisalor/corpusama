"""Utility functions."""
import logging
import pathlib
from xml.sax.saxutils import quoteattr  # nosec

import pandas as pd
from defusedxml import ElementTree

from pipeline.ske_fr import uninorm_4 as uninorm

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
    invalid_tokens: list = ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e"],
):
    """Removes invalid XML tokens from a string, otherwise returns as-is.

    Args:
        invalid_tokens: Tokens to remove before making XML strings.

    Notes:
        - Encodes strings with ``xml.sax.saxutils.quoteattr``:
            may require decoding for URLs & other escaped characters"""

    def replace_invalid(item):
        for k, v in invalid_tokens.items():
            item = item.replace(k, v)
        return item

    invalid_tokens = {x: "" for x in invalid_tokens}
    if isinstance(item, str):
        item = replace_invalid(item)
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


def clean_text(text: str) -> str:
    """Cleans texts to prepare for passing to an NLP pipeline.

    Args:
        text: Text string.

    Notes:
        `uninorm` module from Unitok: Michelfeit et al., 2014; Rychlý & Špalek, 2022.
        License and code available at <https://corpus.tools/wiki/Unitok>.
    """
    lines = text.split("\n")
    lines = [uninorm.normalize_line(x) for x in lines]
    return "".join(lines)
