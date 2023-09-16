"""Methods to combine sqlite and txt data before processing with a pipeline."""
import logging
import pathlib

import pandas as pd

from corpusama.util import convert, parallel

# TODO export_text requires unit testing


def get_txt_file(path) -> str:
    """Open a file at a given path and output text or `None`; warn if not found."""
    file = pathlib.Path(path)
    if not file.exists():
        logging.warning(f"not found - {path}")
        return None
    with open(file) as f:
        return f.read()


def empty_warning(df: pd.DataFrame) -> None:
    """Logs a warning if empty texts exist."""
    empty_str = len(df.loc[df["text"].str.strip() == "", "text"])
    df.loc[df["text"].str.strip() == "", "text"] = None
    no_text = df.loc[df["text"].isnull()]
    if not no_text.empty:
        logging.warning(f'text = None {len(no_text)} ({empty_str} = ""):\n{no_text}')


class _PrepareText:
    """Class to manage text preparation in parallel."""

    def __init__(self, pdf_dir) -> None:
        self.pdf_dir = pdf_dir

    def run(self, df):
        """Prepare a DataFrame of `Corpus` content so it can be exported."""
        # rename columns
        df.rename({"body_html": "text"}, inplace=True, axis=1)
        # set TXT filepaths
        df.loc[df["file_id"] != 0, "path"] = (
            self.pdf_dir
            + df["id"].astype(str)
            + "/"
            + df["file_id"].astype(str)
            + ".txt"
        )
        # update XML file_id
        df["doc_tag"] = df.apply(
            lambda x: x["doc_tag"].replace("FILE_ID", str(x["file_id"])), axis=1
        )
        # convert HTML to text
        df.loc[df["file_id"] == 0, "text"] = df.loc[df["file_id"] == 0, "text"].apply(
            convert.html_to_text
        )
        # read TXT files
        df.loc[df["file_id"] != 0, "text"] = df.loc[df["file_id"] != 0, "path"].apply(
            get_txt_file
        )
        empty_warning(df)
        # combine text and XML tags
        df.loc[df["text"].notnull(), "text"] = (
            df.loc[df["text"].notnull(), "doc_tag"]
            + "\n"
            + df.loc[df["text"].notnull(), "text"]
            + "\n</doc>"
        )
        return df


def export_text(
    self,
    lang: str,
    stem: str = "reliefweb",
    min_portion: float = 0.8,
    chunksize: int = 25000,
    start_date: str = "1900-01-01",
    end_date: str = "2100-12-31",
    cores: int = 0,
    test: bool = False,
):
    """Combine corpus texts for a given language and save to TXT files.

    Args:
        self: `Corpus` object.
        lang: Language ISO code.
        stem: Prefix for files (naming convention: `<stem>_<lang>_<chunk>.txt`).
        min_portion: Minimum portion of a text necessary to be included in `lang`.
        chunksize: Maximum number of texts to combine per file. A corpus will have
            `ceil(n_texts / chunksize)` files; adjust based on corpus size and CPU/RAM.
        start_date: Earliest date to include.
        end_date: Latest date to include.
        cores: Cores used to process items in a chunk (`0` to auto-detect).
        test: Output first file only (for testing).

    Notes:
        - Combines texts with a given language, inserting XML <doc> strings with
            attributes for each text.
        - Run a test first and increase settings (`cores`, `chunksize`) to improve
            performance.
    """
    q = """SELECT
    _lang.id,_lang.file_id,_lang.lid,_attr.doc_tag,_raw.date,_raw.body_html FROM _lang
    LEFT JOIN _attr ON _lang.id = _attr.id
    LEFT JOIN _raw ON _lang.id = _raw.id
    WHERE json_extract(_lang.lid,?) >= ?
    AND DATE(json_extract(_raw.date, '$.original')) BETWEEN date(?) AND date(?)
    ORDER BY _lang.id,_lang.file_id;"""
    params = (f"$.{lang}", min_portion, start_date, end_date)
    res = pd.read_sql(q, self.db.conn, chunksize=chunksize, params=params)
    file = pathlib.Path(f"{stem}_{lang}_{start_date}_{end_date}.txt")
    cores = parallel.set_cores(cores)
    batch = 1
    for df in res:
        if not df.empty:
            job = _PrepareText(self.config["pdf_dir"])
            df = parallel.run(df, job.run, cores)
            texts = "\n".join(df.loc[df["text"].notnull(), "text"].values)
            with open(file.with_suffix(f".{batch}.txt"), "w") as f:
                f.write(texts)
            logging.debug(f'{file.with_suffix(f".{batch}.txt")}')
            batch += 1
            if test:
                break
