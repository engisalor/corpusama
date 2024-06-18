"""Methods to generate and modify corpus attributes."""
import logging
from collections import OrderedDict

import pandas as pd

from corpusama.util import convert, flatten, parallel, util
from pipeline.ske_fr import uninorm_4


class Prep_DF:
    """A class to make corpus attributes via a `make` method."""

    def __init__(self, attributes, attr_params: dict, years: bool = True):
        self.attributes = attributes
        self.attr_params = attr_params
        self.years = years
        self.missing = set()

    def make(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Prepares a DataFrame of raw content and generates document attributes.

        Notes:
            Inspect `self.missing` to check for attributes that may be missing from the
            corpus's `attributes` dictionary but existing in `_raw` data.
        """
        # reshape df
        df = flatten.dataframe(df)
        df.columns = [x.replace(".", "__").replace("-", "_") for x in df.columns]
        missing_attr = [x for x in df.columns if x not in self.attributes.keys()]
        if missing_attr:
            self.missing.update(missing_attr)
        df = df[[x for x in df.columns if x not in self.attr_params["drop"]]]
        # add simplified year columns
        if self.years:
            _add_years(df)
        # prepare multivalue columns
        single = [x for x in self.attr_params["single"] if x in df.columns]
        multi = [x for x in df.columns if x not in single]
        for col in multi:
            df[col] = df[col].apply(convert.list_to_string)
        # remove empty lists
        df = df.map(convert.empty_list_to_none)
        # prepare singlevalue columns
        for col in single:
            df[col] = df[col].apply(convert.list_to_string_no_sep)
        # standardize nan values
        df = df.apply(convert.nan_to_none)
        # normalize
        df = df.map(
            lambda x: uninorm_4.normalize_line(x) if isinstance(x, str) else x
        )
        # replace extra whitespace
        df.replace(r"\s+", " ", regex=True, inplace=True)
        # format as XML attributes
        ids = df["id"].copy()
        df = df.map(util.xml_quoteattr)
        # add doc_tag column
        _add_doc_tags(df)
        # return only id and doc_tag
        df = df[["id", "doc_tag"]]
        df["id"] = ids
        return df


def _doc_tag(dt: dict) -> str:
    """Returns a document's XML tag with attributes from a dictionary.

    Args:
        dt: A dictionary of quoted tag items (e.g., {"id": '"1"'}, not "1" or 1).

    Notes:
        Adds a `file_id="FILE_ID"` placeholder whose value is inserted later on.
    """
    dt = OrderedDict(sorted(dt.items()))
    doc_tag = [f'<doc id={dt["id"]} ']
    del dt["id"]
    if dt.get("file_id"):
        doc_tag.append(f'file_id={dt["file_id"]} ')
        del dt["file_id"]
    else:
        doc_tag.append('file_id="FILE_ID" ')
    for k, v in dt.items():
        if v:
            doc_tag.append(f"{k}={v} ")
    doc_tag.append(">")
    return "".join(doc_tag)


def _add_doc_tags(df: pd.DataFrame) -> None:
    """Adds a column of XML start-tags with document attributes.

    Args:
        df: DataFrame to update (modified in-place).
    """
    df["doc_tag"] = df.apply(lambda row: _doc_tag(dict(row)), axis=1)


def _add_years(df: pd.DataFrame, separator: str = "__") -> None:
    """Adds columns with simplified timestamps based off existing `date` columns.

    Args:
        df: DataFrame with attribute columns.
        separator: Separator added in column names (e.g., `date__created`).

    Notes:
        - Timestamp columns must be parsable by pd.to_datetime.
        - Modifies the DataFrame in-place.
    """
    date = "".join(["date", separator])
    source_columns = [x for x in df.columns if x.startswith(date)]
    for col in source_columns:
        df[separator.join([col, "year"])] = pd.to_datetime(df[col]).dt.strftime(r"%Y")


def make_attribute(
    self,
    lang: str,
    chunksize: int = 10000,
    years: bool = True,
    cores: int = 0,
    drops: list = ["api_params_hash", "body", "body_html", "redirects"],
) -> None:
    """Generates XML attributes for records and inserts into `_attr`.

    Args:
        self: `Corpus` object.
        lang: ISO language code.
        chunksize: Number of rows to process at a time.
        years: Run `attribute.add_years` on data (generates 4-digit year columns).
        cores: Cores to run in parallel (0 = auto-detect).
        drops: Columns in `_raw` to ignore.

    Notes:
        Attributes are defined in a corpus's `<config_file>.yml` `attributes` dict.
        - `drops` should exclude text content (e.g. `body_html`) and `redirects`.
        - XML tags include an empty `file_id` value: `<doc id="123" file_id=FILE_ID>`.
    """
    raw_cols = [x[1] for x in self.db.c.execute("pragma table_info(_raw)").fetchall()]
    raw_cols = [x for x in raw_cols if x not in drops]
    raw_query = f"""SELECT {",".join(raw_cols)} FROM _raw
        WHERE id IN (SELECT id FROM _lang WHERE json_extract(_lang.lid,?));"""  # nosec
    attributes = self.config["attributes"]
    attr_params = _get_params(attributes)
    attr_job = Prep_DF(attributes, attr_params, years=years)
    cores = parallel.set_cores(cores)
    res = pd.read_sql(
        raw_query, self.db.conn, chunksize=chunksize, params=(f"$.{lang}",)
    )
    for df in res:
        df = parallel.run(df, attr_job.make, cores)
        self.db.insert(df, "_attr")
    m = f"missing attributes - {attr_job.missing}"
    logging.debug(m)


def _get_params(attributes: dict) -> dict:
    """Reads a dictionary of attributes and returns another of corpus settings.

    Args:
        attributes: Dict of attributes loaded from `attribute_yaml`.

    Notes:
        So far, this function accepts these fields from an `attribute.yaml` file:
        - `drop` (if an attribute is ignored for corpus creation)
        - `MULTIVALUE` (if an attribute can have multiple values with a separator).
    """
    return {
        "drop": [k for k, v in attributes.items() if v.get("drop", False)],
        "single": [k for k, v in attributes.items() if not v.get("MULTIVALUE", False)],
    }


# WORK IN PROGRESS

# def analyze_attribute(self, lang:str, chunksize: int=10000, cores: int =0,
# chunk_examples:int = 1, drop_cols: list = ["body",
# "body_html", "redirects"]) -> pd.DataFrame:
#     """Returns a DF describing values for attributes.

#     Args:
#         self: A `Corpus` object.
#         lang: Two/three-letter ISO language code.
#         chunksize: Number of rows to process at a time.
#         chunk_examples: Number of example values to retrieve for each attribute.
#             Gets N examples from each chunk.
#         cores: Cores to run in parallel (0 = auto-detect).
#         drop_cols: Columns to drop from the `_raw` table before processing.

#     Notes:
#         - Language code must exist in `_lang` table (run `make_langid()` first).
#         - Exclude any `_raw` columns that aren't attributes or if errors occur
#             (e.g. while flattening).
#         - Can process very large tables, but will produce many examples depending on
#             `chunksize` and `chunk_examples`. Consider how many rows exist for `lang`
#             to determine optimal settings.
#         - `_analyze_attribute()` is available as an alternative method (1 batch only).
#     """
#     m = f"invalid lang {lang}: must be string with length 2 or 3"
#     if len(lang) > 3 or len(lang) < 2 or not isinstance(lang,str):
#         raise ValueError(m)
# q = "SELECT * FROM _raw WHERE id IN (SELECT id FROM _lang WHERE
# json_extract(_lang.lid,?))"
#     res = pd.read_sql(q, self.db.conn, chunksize=chunksize, params = (f"$.{lang}",))
#     analysis = pd.DataFrame()
#     n = 0

#     class Batch:
#         def run(df):
#             return _analyze_attribute(df, self.chunk_examples, self.drop_cols)
#         def __init__(self, chunk_examples, drop_cols) -> None:
#             self.chunk_examples = chunk_examples
#             self.drop_cols = drop_cols

#     # TODO combine parallel.run and parallel.run_with_timeout
#     # TODO currently this produces one %NA value for each chunk: we want one value
#     # calculated across all chunks (as in _analyze_attribute)
#     for df in res:
#         logging.debug(f'batch {n}')
#         n += 1
#         if not df.empty:
#             cores = parallel.set_cores(cores)
#             batch = Batch(chunk_examples, drop_cols)
#             df = parallel.run(df, batch.run, cores)
#             analysis = pd.concat([analysis, df])
#     return analysis.sort_values(["%NA", "attribute"])


# def _analyze_attribute(df: pd.DataFrame, examples:int = 5,
#     drop_cols: list = ["body", "body_html", "redirects"]) -> pd.DataFrame:
#     """Analyzes a DataFrame from `_raw` and returns another describing its attributes.

#     Args:
#         lang: DataFrame of `_raw` data.
#         examples: Number of example values to retrieve for each attribute.
#         drop_cols: Columns to drop from the `_raw` table before processing.
#     """
#     df.drop(drop_cols, axis=1, inplace=True)
#     df = flatten.dataframe(df)
#     # make attribute list
#     attrs = {}
#     for col in df.columns:
#         attrs[col] = round(len(df.loc[df[col].isna(), col]) / len(df), 2)
#     # get examples
#     examples_dt = {}
#     for col in df.columns:
#         temp = df.loc[df[col].notnull(), col]
#         if temp.empty:
#             examples_dt[col] = []
#         elif len(temp) < examples:
#             examples_dt[col] = temp.to_list()
#         else:
#             examples_dt[col] = temp.sample(examples).to_list()
#     # make analysis
#     records = [
#         {"attribute": k, "example": i} for k,v in examples_dt.items() for i in v
#       ]
#     analysis = pd.DataFrame.from_records(records)
#     for k,v in attrs.items():
#         analysis.loc[analysis["attribute"] == k, "%NA"] = v
#     return analysis[["%NA", "attribute", "example"]].sort_values(["%NA", "attribute"])
