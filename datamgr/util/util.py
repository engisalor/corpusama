import logging
import pathlib

import pandas as pd
from defusedxml import ElementTree

logger = logging.getLogger(__name__)


def now():
    """Returns an ISO timestamp rounded to the second."""

    return pd.Timestamp.now().round("S").isoformat()


def join_results(results: tuple, columns: list) -> pd.DataFrame:
    """Makes a dataframe from the fetched results of a join query."""

    df = pd.DataFrame.from_records(results, columns=columns)
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def limit_runs(run: int, runs: int):
    """Returns boolean to set whether a while loop repeats."""

    if run == runs:
        logger.debug(f"{run+1}")
        return False
    else:
        return True


def increment_version(version: str, mode: str):
    """Update a version by major if mode='full' or minor if mode='append'."""

    old = str(version).split(".")
    if mode == "full":
        new = f"{int(old[0]) + 1}.0"
    elif mode == "add":
        new = f"{old[0]}.{int(old[1]) + 1}"
    else:
        raise ValueError("Mode must be 'full' or 'append'.")
    return new


def count_log_lines(message: str, log_file):
    calls_made = 0
    if pathlib.Path(log_file).exists():
        with open(pathlib.Path(log_file), "r") as f:
            daily_log = f.readlines()
        for x in daily_log:
            if message in x:
                calls_made += 1
    return calls_made


def unique_xml_attrs(tags: list):
    all_attrs = set()
    for x in range(len(tags)):
        tree = ElementTree.fromstring(tags[x])
        all_attrs.update(tree.attrib.keys())
    return all_attrs
