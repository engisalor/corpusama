"""Methods to generate and modify corpus attributes."""
import json
import logging
from collections import OrderedDict

import pandas as pd

from datamgr.util import convert, dataclass, decorator, flatten, util

logger = logging.getLogger(__name__)


def prep_df(df: pd.DataFrame, drop_attr: list) -> pd.DataFrame:
    """Prepares a dataframe of raw data for constructing document attributes.

    Flattens data, cleans column names (convert . to __ and - to _)
    Combines multiple list values to str with separator.

    - df, dataframe, slice of raw corpus data
    - drop_attr, list, fields to ignore as attributes"""

    df = flatten.dataframe(df)
    df = df.applymap(convert.list_to_string)
    df.columns = [x.replace(".", "__").replace("-", "_") for x in df.columns]
    if drop_attr:
        df = df[[x for x in df.columns if x not in drop_attr]]
    df = df.apply(convert.nan_to_none)
    return df


def doc_tag(dt: dict) -> str:
    """Makes a <doc> tag with attributes."""

    dt = OrderedDict(sorted(dt.items()))
    doc_tag = [f'<doc id="{dt["id"]}" ']
    del dt["id"]
    for k, v in dt.items():
        if v:
            doc_tag.append(f"{k}={json.dumps(str(v),ensure_ascii=False)} ")
    doc_tag.append(">")
    return "".join(doc_tag)


def join_vert(row):
    doc_start = row["attr"]
    doc_vert = row["vert"]
    doc_end = "</doc>\n"
    return "\n".join([doc_start, doc_vert, doc_end])


def add_doc_tags(df: pd.DataFrame):
    """Adds column with <doc> tags containing attributes."""

    df["doc_tag"] = df.apply(lambda row: doc_tag(dict(row)), axis=1)


def add_years(df: pd.DataFrame):
    """Adds year attributes for timestamp columns starting with 'date_'."""

    source_columns = [x for x in df.columns if x.startswith("date__")]
    for col in source_columns:
        df["__".join([col, "year"])] = pd.to_datetime(df[col]).dt.strftime(r"%Y")


def make_attribute(self, size=100):
    """Generates attributes for vertical files.

    Destructive: replaces all existing attributes

    -size, int, rows to process per batch"""

    @decorator.while_loop
    def attr_batch(self, size):
        query = "SELECT * FROM _raw LIMIT ?,?;"
        batch, offset = self.db.fetch_batch(self.attr_run, size, query)
        if not batch:
            return False
        cols = self.db.tables["_raw"]
        df = pd.DataFrame.from_records(batch, columns=cols)
        df = prep_df(df, self.drop_attr)
        add_years(df)
        add_doc_tags(df)
        rowids = self.attr_rowids[offset : offset + size]
        self.db.update_column("_vert", "attr", df["doc_tag"], rowids)
        self.attr_run += 1
        return True

    self.attr_run = 0
    self.attr_rowids = [x[0] for x in self.db.c.execute("SELECT rowid FROM _vert")]
    attr_batch(self, size)


def export_attribute(self, print=False):
    """Reads _vert.attr tags and outputs a set of attributes.

    Uses dataclass.Attribute to determine item format.

    - print, bool, return list without saving file"""

    res = self.db.c.execute("SELECT attr FROM _vert")
    tags = ["".join([x[0], "</doc>"]) for x in res.fetchall()]
    all_attrs = util.unique_xml_attrs(tags)
    config = []
    parameters = {"DYNTYPE": "index", "MULTISEP": "|", "MULTIVALUE": "y"}
    for attr in sorted(all_attrs):
        config.append(dataclass.CorpusAttribute(attr, parameters))
    filepath = self.db.path.with_suffix(".attr.go")

    if not print:
        with open(filepath, "w") as f:
            f.write("".join([x.config_entry for x in config]))
        logger.debug(f"{len(config)} in {filepath}")
    else:
        return config
