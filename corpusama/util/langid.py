"""Language identification module.

This module contains methods to identify the languages of texts with several LI tools.
The `LangID` class is the main entry point. See the example below for usage and notes
on installation requirements.

For the `uninorm` module, see Michelfeit et al., 2014; Rychlý & Špalek, 2022:
<https://corpus.tools/wiki/Unitok>.

Example:
    ```py
    >>> files = ["README.md","license"]

    >>> sample_kwargs = dict(
    ...    sample_size = 0,  # desired number of random lines to collect (0=everything)
    ...    tries = 5,        # max number of attempts to find suitable lines
    ...    min_len = 10,     # ignore lines under n characters long
    ...    drops = drop_all, # string of characters to remove before language detection
    ... )

    >>> nlp = stanza.Pipeline(
    ...    lang="multilingual",
    ...    processors="langid",
    ...    download_method=None,
    ...    )

    >>> model = fasttext.load_model("./fastText/lid.176.bin")

    >>> lid = LangID(
    ...    files,
    ...    sample_kwargs,
    ...    nlp,
    ...    model,
    ...    threshold=0.6  # ignore low-confidence lines (fastText only)
    ... )

    >>> len(lid.df)  # generates a DataFrame at `LangiD.df`
    4

    ```
"""
import functools
import logging
import pathlib
import random
import string
from logging.handlers import TimedRotatingFileHandler
from time import perf_counter
from typing import Callable
from math import ceil

# import fasttext
import numpy as np
import pandas as pd
import stanza

from pipeline.ske_fr import uninorm_4 as uninorm

log_file = ".logs/langid.log"
file_handler = TimedRotatingFileHandler(log_file, "midnight", backupCount=1)
stream_handler = logging.StreamHandler()

logging.basicConfig(
    encoding="utf-8",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
    handlers=[stream_handler, file_handler],
)

# default settings
pathlib.Path(".temp/").mkdir(exist_ok=True)
digit = "".join([string.digits])
punct = '!"#$%&()*+,./:;<=>?@[\\]^_`{|}~'
symbol = "•�…►▼‐■》∗✔⇤–●▪➔­­;«»◊›➢“©□"
whitespace = "\t\n\r\x0b\x0c"
drop_all = "".join([digit, punct, symbol, whitespace])
summary_cols = {x: None for x in ["file", "top", "weight", "sample", "langs", "time"]}
li_columns = ["file", "tool", "lid", "time", "top"]


def clean_lines(lines: list, drops: str = drop_all) -> list:
    """Cleans a list of lines, removing `drops`, extra spaces and short lines.

    Args:
        lines: List of document lines.
        drops: String of unwanted chars (punctuation, digits, symbols, whitespace).

    Notes:
        - Converts all-uppercase lines to lowercase (improves LI but ignores proper
            nouns, etc.).
        - Relies on `uninorm.normalize_line` (see `langid` module docstring).
    """
    # clean
    lines = [uninorm.normalize_line(x) for x in lines]
    # remove unwanted characters
    # TODO somewhat redundant w/ uninorm; removing punct, symbols, digits still needed
    lines = [x.translate(str.maketrans(drops, " " * len(drops))) for x in lines]
    # remove extra spaces
    lines = [" ".join(x.split()) for x in lines if x.strip()]
    # convert to lower if needed
    lines = [x.lower() if x.isupper() else x for x in lines]
    return lines


def sample_lines(
    lines: list,
    sample_size: int,
    tries: int = 5,
    drops: str = drop_all,
    **kwargs,
) -> list:
    """Returns a random sample of cleaned, unique lines, or all if fewer exist.

    Args:
        lines: List of lines from a text.
        sample_size: Desired sample size (`0` includes everything).
        tries: Rounds of randomized sample collection to try collecting desired size.
        min_len: Remove lines if character length < N.
        drops: String of unwanted characters (punctuation, digits, symbols, \\t, etc.).
            See `langid.digit`, `langid.drop_all`, etc (add others as needed).
        kwargs: Other `sample_kwargs` used by related functions.
    """
    if sample_size > len(lines) or sample_size == 0:
        return clean_lines(lines, drops)
    else:
        clean = set()
        while sample_size > len(clean) and tries > 0:
            tries -= 1
            lines = random.sample(lines, len(lines))
            clean.update(clean_lines(lines, drops))
        return list(clean)[:sample_size]


def _get_lines(s: str, is_file: bool, sample_kwargs: dict) -> list|dict:
    """Opens a file and runs sample_lines(): logs a warning if there's no content.

    Args:
        s: Filename or text string.
        is_file: Whether `s` is a filepath `True` or a text `False`.
        sample_kwargs: args for sample_lines.
    """
    if is_file:
        if pathlib.Path(s).exists():
            with open(s) as f:
                lines = f.readlines()
        else:
            lines = []
            logging.error(f"no such file - {s}")
    else:
        lines = s.split("\n")
    sample = sample_lines(lines, **sample_kwargs)
    # check for content
    if not len(sample):
        logging.warning(f"empty - {s}")
        return {}
    else:
        return sample


def _li_wrapper(func: Callable) -> dict:
    """Wraps `_raw` LI functions and generates an analysis.

    Args:
        func: A language identification function with the name `<LI tool>_raw`.

    See:
        For an example see `identify_stanza()`.
    """

    @functools.wraps(func)
    def _inner(*args, **kwargs):
        # determine LI tool
        if "stanza" in func.__name__:
            tool = "stanza"
        elif "fasttext" in func.__name__:
            tool = "fasttext"
        else:
            raise ValueError(f"couldn't determine LI tool type from {func}")
        # run LI
        t0 = perf_counter()
        dt = func(*args, **kwargs)
        t1 = perf_counter()
        time = round(t1 - t0, 3)
        # make dict
        if args[1] is True:
            file = str(args[0])
        else:
            file = None
        dt |= {"file": file, "tool": tool, "time": time, "params": args[2]}
        return dt

    return _inner


def _sort_lines(lines: list, sample_kwargs: dict) -> dict:
    """Sorts lines by string length and returns a dict.

    Args:
        sample_kwargs: Settings dict that includes `min_len`.
    """
    long = []
    short = []
    for line in lines:
        if len(line) >= sample_kwargs["min_len"]:
            long.append(line)
        else:
            short.append(line)
    langs_short = ["short"] * len(short)
    bytes_short = [len(x.encode("utf8")) for x in short]
    return {
        "long": long,
        "short": short,
        "langs_short": langs_short,
        "bytes_short": bytes_short,
    }


@_li_wrapper
def identify_stanza(
    s: str, is_file: bool, sample_kwargs: dict, nlp: stanza.Pipeline, chunksize: int = 1000000
) -> dict:
    """Runs Stanza LI on `s`, returns a dict with results.

    Args:
        s: Filename or text string.
        is_file: Whether `s` is a filepath `True` or a text `False`.
        sample_kwargs: Args passed to `sample_lines()` and `clean_lines()`.
        nlp: Stanza NLP pipeline.
        chunksize: Max bytes of text fed to Stanza at a time.
    """
    results = {"langs": [], "bytes": []}
    sample = _get_lines(s, is_file, sample_kwargs)
    if not sample:
        return results
    size = len("".join(sample).encode("utf8"))
    chunks = 1
    if size > chunksize:
        chunks = ceil(size/chunksize) # 2903051 breaks at this size
        logging.info(f"split {size} bytes into {chunks} chunks")
    
    def _inner(batch) -> None:
        dt = _sort_lines(batch, sample_kwargs)
        docs = [stanza.Document([], text=t) for t in dt["long"]]
        nlp(docs)
        results["langs"].extend([doc.lang for doc in docs] + dt["langs_short"])
        results["bytes"].extend([len(x.encode("utf8")) for x in dt["long"]] + dt["bytes_short"])

    for batch in np.array_split(sample, chunks):
        _inner(batch)

    return results



@_li_wrapper
def identify_fasttext(
    s: str,
    is_file: bool,
    sample_kwargs: dict,
    # model: fasttext.FastText._FastText,
) -> dict:
    """Runs fasttext LI on `s`, returns a dict with results.

    Args:
        s: Filename or text string.
        is_file: Whether `s` is a filepath `True` or a text `False`.
        sample_kwargs: Args passes to `sample_lines()` and `clean_lines()`.
        model: A `_FastText` object.
    """
    print("WARNING: fasttext is deprecated as of v0.3.0")
    # sample = _get_lines(s, is_file, sample_kwargs)
    # if not sample:
    #     return {"langs": [], "scores": [], "bytes": []}
    # dt = _sort_lines(sample, sample_kwargs)
    # res = model.predict(dt["long"])
    # return {
    #     "langs": [y.replace("__label__", "") for x in res[0] for y in x]
    #     + dt["langs_short"],
    #     "scores": [y for x in res[1] for y in x] + [1] * len(dt["langs_short"]),
    #     "bytes": [len(x.encode("utf8")) for x in dt["long"]] + dt["bytes_short"],
    # }


def analyze(
    dt: dict, threshold: float = 0.6, columns: list = li_columns, max_langs=4
) -> dict:
    """Runs an analysis on raw LI data and returns a more detailed dict.

    Args:
        dt: A dictionary produced with `_li_wrapper()`.
        threshold: (0-1.0) Minimum confidence needed to consider an LI result valid
            (fastText only). Labels anything under threshold as `unknown`.
        columns: Data to include in output. Use `[]` to get everything.
        max_langs: The maximum number of languages expected in a multilingual text. If
            LI results include many languages, only those with a significant portion
            (`1 / max_langs+1`) of the text are included. E.g., `max_langs=4`
            ignores LI results for languages that make up less than 20% of a text if
            4 or more languages are detected.

    Notes:
        - Modeled off Abadji et al. (2022) <https://aclanthology.org/2022.lrec-1.463>.
        - Includes `unknown` and `short` in language results when large enough.
    """
    if not columns:
        columns = [k for k in dt.keys()]
    if not dt["langs"]:
        return {k: v for k, v in dt.items() if k in columns}
    # label lines as "unknown" if score < threshold
    if "scores" in dt.keys():
        dt["langs"] = [
            dt["langs"][x] if dt["scores"][x] > threshold else "unknown"
            for x in range(len(dt["langs"]))
        ]
    # get sum of bytes per language
    langs = set(dt["langs"])
    _bytes = {
        x: sum([dt["bytes"][y] for y in range(len(dt["langs"])) if dt["langs"][y] == x])
        for x in langs
    }
    # summarize top languages
    filesize = sum([v for v in _bytes.values()])
    num_langs = len(langs)
    if num_langs > max_langs:
        num_langs = max_langs
    multilingual_threshold = 1 / (num_langs + 1)
    ids = {}
    for k in langs:
        bytes_size = round(_bytes[k] / filesize, 2)
        if bytes_size >= multilingual_threshold:
            ids[k] = bytes_size
    # sort top languages and add to output
    dt["lid"] = dict(sorted(ids.items(), key=lambda item: item[1], reverse=True))
    return {k: v for k, v in dt.items() if k in columns}


def identify(
    s: str | list,
    sample_kwargs: dict,
    nlp: stanza.Pipeline | None,
    model: None ,# fasttext.FastText._FastText | None,
    threshold: float = 0.6,
    columns: list = li_columns,
    is_file: bool = True,
) -> pd.DataFrame:
    """Runs language identification on `s` and makes a DataFrame of results.

    Args:
        s: Filepath(s) or text(s).
        sample_kwargs: Args passed to `sample_lines()` and `clean_lines()`.
        nlp: (Optional) A Stanza NLP pipeline.
        model: (Optional) A _FastText object.
        threshold: (0.0<1.0) Minimum confidence needed to consider an LI result valid
            (fastText only).
        columns: Data to include in output. Use `[]` to get everything.
        is_file: Whether `s` is a filepath `True` or a text `False`.
    """
    t0 = perf_counter()
    df = pd.DataFrame()
    if isinstance(s, str):
        s = [s]
    n = 0
    for t in s:
        dt_st = {}
        dt_fa = {}
        # run LI
        if nlp:
            dt_st = identify_stanza(t, is_file, sample_kwargs, nlp)
            dt_st = analyze(dt_st, threshold, columns)
        if model:
            dt_fa = identify_fasttext(t, is_file, sample_kwargs, model)
            dt_fa = analyze(dt_fa, threshold, columns)

        # make DataFrame
        temp = pd.DataFrame.from_records([dt_st, dt_fa])
        df = pd.concat([df, temp])
        n += 1

    df.drop(df[df["tool"].isna()].index, inplace=True)
    t1 = perf_counter()
    t = round(t1 - t0, 2)
    logging.info(f"... {round(t,3)}s - {round(t/len(df), 2)}s / text")
    return df.reset_index(drop=True)


def _has_lang(dt: dict, lang: str) -> bool:
    """Returns `True` if a language exists in a dict of LI results.

    Args:
        dt: A dictionary of LI results, e.g., from `identify_stanza()`.
        lang: 2-3 letter ISO of a language to detect.
    """
    return lang in dt.keys()


def _is_l1(dt: dict, lang: str) -> bool:
    """Returns `True` if a language is the top result in a dict of LI results.

    Args:
        dt: A dictionary of LI results, e.g., from `identify_stanza()`.
        lang: 2-3 letter ISO of a language to detect.
    """
    if not dt or not isinstance(dt, dict):
        return np.NaN
    top = list(dt.keys())[list(dt.values()).index(max(dt.values()))]
    return lang == top


def _multiling(dt: dict) -> bool:
    """Returns `True` if 2+ languages exist (excludes `unknown` & `short`).

    Args:
        dt: A dictionary of LI results, e.g., from `identify_stanza()`.
    """
    if not dt or not isinstance(dt, dict):
        return np.NaN
    return len([x for x in dt.keys() if x not in ["unknown", "short"]]) > 1


def _l1(dt: dict) -> str:
    """Returns the top language for a in a dict of LI results.

    Args:
        dt: A dictionary of LI results, e.g., from `identify_stanza()`.
    """
    if not dt or not isinstance(dt, dict):
        return np.NaN
    return list(dt.keys())[list(dt.values()).index(max(dt.values()))]


class LangID:
    """A class to run language identification on files and inspect results.

    Args:
        s: Filepath(s) or text(s).
        sample_kwargs: Args passed to `sample_lines()` and `clean_lines()`.
        nlp: (Optional) A Stanza NLP pipeline.
        model: (Optional) A _FastText object.
        threshold: (0-1.0) Minimum confidence needed to consider an LI result valid
            (fastText only).
        columns: Data to include in output. Use `[]` to get everything.
        is_file: Whether `s` is a filepath `True` or a text `False`.

    Attributes:
        df (pd.Dataframe): Language analysis results.

    Notes:
        - Methods beginning with `add_` generate a column in `LangID.df` (may be run
            automatically on instantiation).
        - Methods beginning with `get_` return a slice of `LangID.df` w/ a filter.
        - Languages are given a two- or three-letter ISO label  (`en`, `es`, etc.).
            Labels tend to match between Stanza and fastText, but compare their
            documentation to verify.
        - `size`: The proportion of a document in bytes that's in X language (0-1.0).
        - `l1`: The language with the highest proportion in a text.
        - `multiling`: Whether a text has two or more languages (excluding `unknown`).
    """

    def add_l1(self):
        """Adds a column indicating the top language for each text."""
        self.df["l1"] = self.df["lid"].apply(_l1)

    def add_l1_size(self):
        """Adds a column indicating the top language's size (0-1.0) for each text."""
        if "l1" not in self.df.columns:
            self.add_l1()
        self.df.loc[self.df["l1"].notna(), "l1_size"] = self.df.loc[
            self.df["l1"].notna()
        ].apply(lambda row: row["lid"].get(row["l1"]), axis=1)

    def add_multiling(self):
        """Adds a column indicating whether each text may be multilingual."""
        self.df["multiling"] = self.df["lid"].apply(_multiling)

    def get_has_lang(self, iso: str) -> pd.DataFrame:
        """Returns rows containing `iso` language."""
        return self.df.loc[self.df["lid"].apply(_has_lang, lang=iso)]

    def get_l1_is(self, iso: str) -> pd.DataFrame:
        """Returns rows where `iso` is the top language."""
        return self.df.loc[self.df["lid"].apply(_is_l1, lang=iso)]

    def get_l1_size_lt(self, size: float) -> pd.DataFrame:
        """Returns rows where `l1_size` is lesser than `size`."""
        if "l1_size" not in self.df.columns:
            self.add_l1_size()
        return self.df.loc[self.df["l1_size"] <= size]

    def get_l1_size_gt(self, size: float):
        """Returns rows where `l1_size` is greater than `size`."""
        if "l1_size" not in self.columns:
            self.add_l1_size()
        return self.df.loc[self.df["l1_size"] >= size]

    def get_l1_size_between(self, low: float, high: float):
        """Returns rows where `l1_size` is between `low` and `high`."""
        if "l1_size" not in self.df.columns:
            self.add_l1_size(self.df)
        return self.df.loc[(self.df["l1_size"] >= low) & (self.df["l1_size"] <= high)]

    def __init__(
        self,
        s: str | list,
        sample_kwargs: dict,
        nlp: stanza.Pipeline | None,
        model: None, # fasttext.FastText._FastText | None,
        threshold: float,
        columns: list = li_columns,
        is_file: bool = True,
    ):
        self.df = identify(s, sample_kwargs, nlp, model, threshold, columns, is_file)
        if "lid" in self.df.columns:
            self.add_multiling()
            self.add_l1()
            self.add_l1_size()
        else:
            self.df["lid"] = None
            self.df["multiling"] = None
            self.df["l1"] = None
            self.df["l1_size"] = None


def file_stats(files: list, out: str = "file-stats") -> None:
    """Generates descriptive stats for a list of files: N lines, N characters, etc.

    Args:
        files: List of filenames to read and analyze.
        out: Stem of output file name.

    Notes:
        Saves to a CSV file with descriptive statistics for each input file.
        Stats include the number of characters and lines, as well as `chars_q<N>`,
        which is the length of lines, in characters, by quartile.
    """
    # generate stats
    stats = pd.DataFrame()
    for file in files:
        with open(file) as f:
            lines = f.readlines()
        lines = clean_lines(lines)
        if not lines:
            line_chars = []
            lines = []
            quant = [0] * 5
        else:
            line_chars = [len(line) for line in lines]
            q_list = [0, 0.25, 0.5, 0.75, 1]
            quant = np.quantile(line_chars, q_list, axis=0, method="nearest")
        row = {
            "file": [file],
            "chars": [sum(line_chars)],
            "lines": [len(lines)],
            "chars_q0": [quant[0]],
            "chars_q1": [quant[1]],
            "chars_q2": [quant[2]],
            "chars_q3": [quant[3]],
            "chars_q4": [quant[4]],
        }
        temp = pd.DataFrame(row)
        stats = pd.concat([stats, temp])
    # save
    stats.reset_index(drop=True).to_csv(f"{out}.csv")


def file_concat(
    files: list, out: str = "file-concat", min_len: int = 10, drops: str = drop_all
) -> None:
    """Combines text files into raw and cleaned versions w/ XML tags.

    Args:
        files: List of filenames to read and analyze.
        out: Stem of output file name.
        min_len: Remove lines if character length < N.
        drops: String of unwanted characters (punctuation, digits, symbols, \\t, etc.).
            See `langid.digit`, `langid.drop_all`, etc (add others as needed).

    Notes:
        Use this to test various parameters for `clean_lines()` before running LI.
        Output files can be large if working with many texts.
    """
    dest = open(f"{out}.xml", "w")
    dest_clean = open(f"{out}-clean.xml", "w")
    for file in files:
        with open(file) as f:
            lines = f.readlines()
            dest.write(f'<file path="{file}">\n')
            dest.write("".join(lines))
            dest.write("\n</file>\n")
            lines = clean_lines(lines, drops)
            dest_clean.write(f'<file path="{file}">\n')
            dest_clean.write("\n".join(lines))
            dest_clean.write("\n</file>\n")
    dest.close()
    dest_clean.close()


if __name__ == "__main__":
    import doctest

    doctest.testmod()
