"""Methods to generate and modify corpus attributes."""
import json
import logging
import pathlib
from collections import OrderedDict

import pandas as pd

from corpusama.util import convert, decorator, flatten
from corpusama.util import io as _io
from corpusama.util import parallel, util

logger = logging.getLogger(__name__)


class Prep_DF:
    """A class to supply additional variables when making attributes.

    Methods:
        make: The method for making attributes."""

    def __init__(self, attributes, attr_params: dict, years: bool = True):
        self.attributes = attributes
        self.attr_params = attr_params
        self.years = years

    def make(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Prepares a DataFrame of raw content and generates document attributes.

        Notes:
            Logs a warning if an attribute/field is missing from ``attribute.yaml``.
            Update the yaml file with new values and consider rerunning
            ``make_attribute`` to ensure all attributes are treated properly."""

        # reshape df
        df = flatten.dataframe(df)
        df.columns = [x.replace(".", "__").replace("-", "_") for x in df.columns]
        missing_attr = [x for x in df.columns if x not in self.attributes.keys()]
        if missing_attr:
            logger.warning(f"missing from attribute.yaml: {missing_attr}")
        df = df[[x for x in df.columns if x not in self.attr_params["drop"]]]
        # remove invalid XML tokens
        df = df.applymap(util.clean_xml_tokens)
        # add simplified year columns
        if self.years:
            add_years(df)
        # prepare multivalue columns
        single = [x for x in self.attr_params["single"] if x in df.columns]
        multi = [x for x in df.columns if x not in single]
        for col in multi:
            df[col] = df[col].apply(convert.list_to_string)
        # remove empty lists
        df = df.applymap(convert.empty_list_to_none)
        # prepare singlevalue columns
        for col in single:
            df[col] = df[col].apply(convert.list_to_string_no_sep)
        # standardize nan values
        df = df.apply(convert.nan_to_none)
        # format as XML attributes
        df = df.applymap(util.xml_quoteattr)
        # add doc_tag column
        add_doc_tags(df)
        return df


def doc_tag(dt: dict) -> str:
    """Returns a document's XML tag with attributes from a dictionary.

    Args:
        dt: A dictionary of tag items
            (pre-format with ``prep_df`` or similar first).

    Notes:
        - Outputs the start-tag only:
            ``<doc id="12345" title="document title>``."""

    dt = OrderedDict(sorted(dt.items()))
    doc_tag = [f'<doc id={dt["id"]} ']
    del dt["id"]
    for k, v in dt.items():
        if v:
            doc_tag.append(f"{k}={v} ")
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


def make_attribute(
    self,
    attribute_yaml: str = "corpusama/source/params/rw-attribute.yml",
    size: int = 10000,
    cores=0,
    years: bool = True,
) -> None:
    """Generates attributes for vertical files.

    Args:
        self: A ``Corpus`` object.
        attribute_yaml: File with parameters defining how to treat corpus attributes.
        size: The number of table rows to process at a time.
        cores: Max number of cores to use in parallel.
        years: Run ``attribute.add_years`` on data
            (adds columns simplifying timestamps to 4-digit year only).

    Notes:
        - Makes attribute tags for existing _vert rows only.
        - Destructive: replaces all attributes in the ``_vert`` table."""

    @decorator.while_loop
    def attr_batch(self, size) -> bool:
        """Processes a batch of table records to make attributes."""

        query = "SELECT * FROM _raw WHERE id IN (SELECT id FROM _vert) LIMIT ?,?;"
        batch, offset = self.db.fetch_batch(self.attr_run, size, query)
        if not batch:
            return False
        cols = self.db.tables["_raw"]
        df = pd.DataFrame.from_records(batch, columns=cols)
        prep_df = Prep_DF(self.attributes, self.attr_params, self.years)
        df = parallel.run(df, prep_df.make, self.cores)
        rowids = self.attr_rowids[offset : offset + size]
        self.db.update_column("_vert", "attr", df["doc_tag"], rowids)
        self.attr_run += 1
        return True

    self.attributes = _io.load_yaml(attribute_yaml)
    self.attr_params = get_params(self.attributes)
    self.years = years
    self.attr_run = 0
    self.cores = parallel.set_cores(cores)
    self.attr_rowids = [x[0] for x in self.db.c.execute("SELECT rowid FROM _vert")]
    attr_batch(self, size)


def get_params(attributes: dict) -> dict:
    """Reads a dictionary of attributes and returns another of corpus settings.

    Args:
        attributes: A dictionary of attributes loaded from ``attribute_yaml``.

    Notes:
        Currently, this function accepts these fields from an ``attribute.yaml`` file:
        ``drop`` (whether to include an attribute in a
        corpus) and ``MULTIVALUE`` (whether an attribute can have multiple values
        with a separator)."""

    return {
        "drop": [k for k, v in attributes.items() if v.get("drop", False)],
        "single": [k for k, v in attributes.items() if not v.get("MULTIVALUE", False)],
    }


def export_attribute(
    self,
    default_params: dict = {"DYNTYPE": "freq", "MULTISEP": "|"},
    attribute_yaml: str = "corpusama/source/params/rw-attribute.yml",
    print: bool = False,
) -> None:
    """Reads attribute tags from the ``_vert`` table and saves unique keys to file.

    Args:
        print: Return a list of attribute strings without saving to file.
        default_params: Default parameters for attributes (e.g., DYNTYPE).
        attribute_yaml: File with parameters defining how to treat corpus attributes.

    Notes:
        - Saves attributes to ``/data/<database_name>.attr.go``.

    See Also:
        - https://www.sketchengine.eu/documentation/"""

    attributes = _io.load_yaml(attribute_yaml)
    filepath = self.db.path.with_suffix(".attr.go")
    config = _export(default_params, attributes)
    if print:
        return config
    else:
        with open(filepath, "w") as f:
            f.write(config)
        logger.debug(f"{filepath}")


def _export(default_params: dict, attributes: dict) -> str:
    """A helper function for ``export_attribute``."""

    config = ""
    attributes = {k: v for k, v in attributes.items() if not v.get("drop", False)}
    attributes = {k: v | default_params for k, v in attributes.items()}
    for v in attributes.values():
        if v.get("MULTIVALUE", None) == 0:
            del v["MULTIVALUE"]
            del v["MULTISEP"]

    for attr, params in attributes.items():
        config += f"""\nATTRIBUTE "{attr}" """
        config += "{"
        for k, v in params.items():
            config += f"\n    {k} {json.dumps(str(v))}"
        config += "\n    }"
    return config


def unique_attribute(
    self,
    attribute_yaml: str = "corpusama/source/params/rw-attribute.yml",
) -> set:
    """Returns a set of attributes in ``_vert`` and compares with ``attribute_yaml``.

    Args:
        self: A Corpus object.
        attribute_yaml: File with parameters defining how to treat corpus attributes.

    Notes:
        Logs a warning if attributes exist in ``_vert`` but not ``attribute_yaml``
        (update the file and/or fix in ``Corpus`` code before continuing."""

    res = self.db.c.execute("SELECT attr FROM _vert")
    tags = ["".join([x[0], "</doc>"]) for x in res.fetchall()]
    all_attrs = util.unique_xml_attrs(tags)
    attributes = _io.load_yaml(attribute_yaml)
    fname = pathlib.Path(attribute_yaml).name
    missing_attr = [x for x in all_attrs if x not in attributes.keys()]
    logger.debug(f"{len(attributes)} in {fname}, including {len(all_attrs)} in _vert")
    if missing_attr:
        logger.warning(f"{fname} is missing: {missing_attr}")
    return all_attrs
