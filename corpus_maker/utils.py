import ast
import json
import logging
import tarfile
from html.parser import HTMLParser

import pandas as pd

logger = logging.getLogger(__name__)
log_file = ".corpus-maker.log"


def html_to_text(html):
    """Extracts text from a html string."""

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
    """Joins list items with a separator (ignores other object types)."""

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


def flatten_df(df, separator="__"):
    """Flattens a df containing list and dict objects (pops nested source columns).

    New column names are labelled by <source column name><separator><new key>."""

    # flatten data
    df = df.copy().applymap(str_to_obj)
    for col in df.columns:
        prefix = "".join([col, separator])
        df[col] = df[col].apply(flatten_list_of_dict)
        df = pd.concat([df, pd.json_normalize(df[col]).add_prefix(prefix)], axis=1)
    # drop original list of dict columns
    for col in df.columns:
        types = set([type(x) for x in df[col]])
        if dict in types:
            df.drop(col, inplace=True, axis=1)

    return df


def prepare_df(df, year_column=["date__original"]):
    """Prepares a df for making Sketch-Engine formatted vert files.

    Can parse timestamp columns and make new one with the year only.
    Replaces . with __ in column names (. is prohibited for SkE text type names)."""

    # clean up df
    df = df[sorted(df.columns)]
    df.fillna("", inplace=True)
    df = df.applymap(list_to_string)
    df.columns = [x.replace(".", "__") for x in df.columns]
    # add year-only column(s)
    if not year_column:
        year_column = []
    for col in year_column:
        df["__".join([col, "year"])] = pd.to_datetime(df[col]).dt.strftime(r"%Y")

    return df
