"""Utility functions."""
import logging
import pathlib

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


def increment_version(version: str, mode: str):
    """Updates a version by major or minor depending on mode.

    Args:
        version: The current version in major.minor format: ``1.0``.
        mode: ``full`` or ``add``.

    Notes:
        Increments the current major version if ``full``, e.g.,
        1.0 -> 2.0, or increments the minor version if ``add``,
        e.g., 1.0 -> 1.1."""

    old = str(version).split(".")
    if mode == "full":
        new = f"{int(old[0]) + 1}.0"
    elif mode == "add":
        new = f"{old[0]}.{int(old[1]) + 1}"
    else:
        raise ValueError("Mode must be 'full' or 'add'.")
    return new


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
