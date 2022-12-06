"""Methods to generate and modify corpus attributes."""
import json
import logging
from collections import OrderedDict

import pandas as pd

from corpusama.util import convert, dataclass, decorator, flatten, util

logger = logging.getLogger(__name__)


def prep_df(df: pd.DataFrame, drop_attr: list) -> pd.DataFrame:
    """Prepares a DataFrame of raw content for making document attributes.

    Args:
        df: A slice of raw source data.
        drop_attr: A list of fields to exclude from corpus attributes.

    Notes:
        - Flattens data and cleans column names
            (converts ``.`` to ``__`` and ``-`` to ``_``).
        - Combines multiple list values into a str with a separator.

    See Also:
        - ``util.flatten``
        - ``util.util.list_to_string``
        - ``util.convert.nan_to_none``"""

    df = flatten.dataframe(df)
    df = df.applymap(convert.list_to_string)
    df.columns = [x.replace(".", "__").replace("-", "_") for x in df.columns]
    if drop_attr:
        df = df[[x for x in df.columns if x not in drop_attr]]
    df = df.apply(convert.nan_to_none)
    return df


def doc_tag(dt: dict) -> str:
    """Returns a document's XML tag with attributes from a dictionary.

    Args:
        dt: A dictionary of tag key:value pairs.

    Notes:
        Outputs the start-tag only:
            ``<doc id="12345" title="document title>``."""

    dt = OrderedDict(sorted(dt.items()))
    doc_tag = [f'<doc id="{dt["id"]}" ']
    del dt["id"]
    for k, v in dt.items():
        if v:
            doc_tag.append(f"{k}={json.dumps(str(v),ensure_ascii=False)} ")
    doc_tag.append(">")
    return "".join(doc_tag)


def join_vert(row: dict) -> str:
    """Returns a complete vertical document with XML tags and tokens.

    Args:
        row: A record in the ``_vert`` table."""

    doc_start = row["attr"]
    doc_vert = row["vert"]
    doc_end = "</doc>\n"
    return "\n".join([doc_start, doc_vert, doc_end])


def add_doc_tags(df: pd.DataFrame) -> None:
    """Adds a column of XML start-tags with document attributes.

    Args:
        df: The dataframe to work on (modified in-place)."""

    df["doc_tag"] = df.apply(lambda row: doc_tag(dict(row)), axis=1)


def add_years(df: pd.DataFrame, separator: str = "__") -> None:
    """Adds columns with simplified timestamps based off existing ``date_`` columns.

    Args:
        df: The DataFrame with attribute columns.
        separator: The separator used in column names (e.g., ``date__created``).

    Notes:
        - Timestamp columns must be parsable by pd.to_datetime.
        - Modifies the DataFrame in-place.
        - By default, ``__`` is used to separate ReliefWeb fields and subfields:
            ``field_name__subfield_name``."""

    date = "".join(["date", separator])
    source_columns = [x for x in df.columns if x.startswith(date)]
    for col in source_columns:
        df[separator.join([col, "year"])] = pd.to_datetime(df[col]).dt.strftime(r"%Y")


def make_attribute(self, size: int = 100) -> None:
    """Generates attributes for vertical files.

    Args:
        self: A ``Corpus`` object.
        size: The number of table rows to process at a time.

    Notes:
        - Destructive: replaces all attributes in the ``_vert`` table.
        - Executes ``add_years`` and ``add_doc_tags``
            (does not require using other ``attribute`` methods beforehand)."""

    @decorator.while_loop
    def attr_batch(self, size) -> bool:
        """Processes a batch of table records to make attributes."""

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


def export_attribute(
    self,
    print: bool = False,
    parameters: dict = {"DYNTYPE": "index", "MULTISEP": "|", "MULTIVALUE": "y"},
) -> None:
    """Reads all attributes tags from the ``_vert`` table and saves to file.

    Args:
        print: Return a list of attribute strings without saving to file.
        parameters: Dictionary of parameters.

    Notes:
        - Saves attributes to ``/data/<database_name>.attr.go``.

    See Also:
        - ``util.dataclass.Attribute``
        - ``util.util.unique_xml_attrs``"""

    res = self.db.c.execute("SELECT attr FROM _vert")
    tags = ["".join([x[0], "</doc>"]) for x in res.fetchall()]
    all_attrs = util.unique_xml_attrs(tags)
    config = []
    for attr in sorted(all_attrs):
        config.append(dataclass.CorpusAttribute(attr, parameters))
    filepath = self.db.path.with_suffix(".attr.go")

    if not print:
        with open(filepath, "w") as f:
            f.write("".join([x.config_entry for x in config]))
        logger.debug(f"{len(config)} in {filepath}")
    else:
        return config
