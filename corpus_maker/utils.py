import ast
import json
import logging
import tarfile
import time
from html.parser import HTMLParser

import pandas as pd

logger = logging.getLogger(__name__)
log_file = ".corpus-maker.log"


def html_to_text(html):
    """Extracts text from an html string."""

    class HTMLFilter(HTMLParser):
        text = ""

        def handle_data(self, data):
            self.text += data

    f = HTMLFilter()
    f.feed(html)
    return f.text


def compress_tar(file):
    """Compresses an uncompressed tar archive using xz."""

    tar_old = tarfile.open(file, "r")
    existing = tar_old.getmembers()
    with tarfile.open(f"{file}.xz", "w:xz") as tar:
        now = pd.Timestamp.now().round("S").timestamp()
        for member in existing:
            member.mtime = now
            tar.addfile(member, tar_old.extractfile(member.name))
    tar_old.close()
    logger.debug(f"{file}.tar.xz")


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


def list_to_string(cell, separator="|"):
    """Joins list items with a separator or returns original object."""

    if isinstance(cell, list):
        return separator.join([str(x) for x in cell])
    else:
        return cell


def flatten_list_of_dict(cell):
    """Recursively converts a list of dicts to a dict of lists."""

    def flatten(cell):
        if not isinstance(cell, list):
            return cell
        else:
            if dict not in [type(x) for x in cell]:
                return cell
            # for [dict, dict, nan] objects
            else:
                # convert nan to empty dict
                cell = [x if isinstance(x, dict) else {} for x in cell]
                # convert list of dicts to dict of lists
                dt = pd.DataFrame(cell).to_dict(orient="list")
                # continue with recursion if needed
                for k, v in dt.items():
                    dt[k] = flatten(v)
                return dt

    return flatten(cell)


def flatten_df(df):
    """Flattens a df containing list and dict objects."""

    t0 = time.perf_counter()

    # flatten data
    df = df.copy().applymap(str_to_obj)
    for col in df.columns:
        df[col] = df[col].apply(flatten_list_of_dict)
        df = pd.concat([df, pd.json_normalize(df[col]).add_prefix(col + ".")], axis=1)

    # clean up df
    df = df[sorted(df.columns)]
    df.fillna("", inplace=True)
    df = df.applymap(list_to_string)

    # drop original list of dict columns
    for col in df.columns:
        types = set([type(x) for x in df[col]])
        if dict in types:
            df.drop(col, inplace=True, axis=1)

    # logging
    t1 = time.perf_counter()
    n_seconds = t1 - t0
    rows_second = int(len(df) / n_seconds)
    logger.debug(
        "".join(
            [
                f"{n_seconds:0.1f}s - ",
                f"{len(df):,} rows - ",
                f"{rows_second:,}/s",
            ]
        )
    )

    return df


def format_df(df, add_year_column=["date__original"]):
    """Replaces . with __ in column names, adds *__year columns based on timestamps.

    If date__original is a timestamp column, date__original__year will be added
    with the year value only."""

    df.columns = [x.replace(".", "__") for x in df.columns]
    df.id = df.id.astype(int)
    for col in add_year_column:
        df["__".join([col, "year"])] = pd.to_datetime(df[col]).dt.strftime(r"%Y")

    return df
