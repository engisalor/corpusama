"""Language identification module.

This module contains methods to identify the languages of texts with several LI tools.
`identify()` is the main function to run. See the example below for general usage.

!!! note
    If pip fails to install fasttext, try downloading and building it locally:
    see their [website](https://fasttext.cc/docs/en/language-identification.html).

    ```bash
    # inspect links before copy-pasting!
    git clone https://github.com/facebookresearch/fastText.git
    cd fastText
    make
    wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin
    # then troubleshoot local pip installation
    ```

Example:
    ```py
    >>> files = ["README.md","license"]

    >>> clean_kwargs = dict(
    ...    min_len = 10,  # exclude lines under N characters
    ...    drops = drop_all,  # characters to exclude from LI
    ... )

    >>> sample_kwargs = dict(
    ...    sample_size = 0,  # desired number of random lines to collect
    ...    tries = 5,  # number of attempts to find suitable lines
    ...    clean_kwargs = clean_kwargs
    ... )

    >>> nlp = stanza.Pipeline(
    ...    lang="multilingual",
    ...    processors="langid",
    ...    download_method=None,
    ...    )

    >>> model = fasttext.load_model("./fastText/lid.176.bin")

    >>> df = identify(
    ...    files,
    ...    sample_kwargs,
    ...    nlp,
    ...    model,
    ... )

    >>> df["top"][0]
    'en'

    ```
"""
import collections
import functools
import logging
import pathlib
import random
import string
from time import perf_counter
from typing import Callable

import fasttext
import numpy as np
import pandas as pd
import stanza

logging.basicConfig(
    encoding="utf-8",
    level=logging.INFO,
    format="%(levelname)s - %(module)s.%(funcName)s - %(message)s",
    handlers=[logging.FileHandler(".logs/langid.log"), logging.StreamHandler()],
)

# default settings
pathlib.Path(".temp/").mkdir(exist_ok=True)
digit = "".join([string.digits])
punct = "".join([string.punctuation])
symbol = "•�…►▼‐■》∗✔⇤"
whitespace = "\t\n\r\x0b\x0c"
drop_all = "".join([digit, punct, symbol, whitespace])
clean_kwargs = dict(
    min_len=10,
    drops=drop_all,
)
sample_kwargs = dict(sample_size=0, tries=5, clean_kwargs=clean_kwargs)
summary_cols = {x: None for x in ["file", "top", "weight", "sample", "langs", "time"]}


def clean_lines(lines: list, min_len: int, drops: str = drop_all) -> list:
    """Cleans a list of lines, removing `drops`, extra spaces and short lines.

    Args:
        lines: Document lines.
        min_len: Remove lines if character length < N.
        drops: String of unwanted characters (punctuation, digits, symbols, \\t, etc.).
            See langid.digit, langid.drop_all, etc (add others as needed).

    !!! warning
        `drops` is set to `langid.drop_all` by default:
            make sure this is appropriate for your data.
    """
    # remove unwanted characters
    lines = [x.translate(str.maketrans(drops, " " * len(drops))) for x in lines]
    # remove extra spaces
    lines = [" ".join(x.split()) for x in lines if x.strip()]
    # remove short lines
    lines = [x for x in lines if len(x) >= min_len]
    return lines


def sample_lines(lines: list, sample_size: int, tries: int, clean_kwargs: dict) -> list:
    """Returns a random sample of cleaned, unique lines, or all if fewer exist.

    Args:
        lines: List of strings.
        sample_size: Desired sample size.
        tries: Rounds of randomized sample collection to try collecting desired size.
        clean_kwargs: Dict of args passed to clean_lines().
    """
    if sample_size > len(lines) or sample_size == 0:
        return clean_lines(lines, **clean_kwargs)
    else:
        clean = set()
        while sample_size > len(clean) and tries > 0:
            tries -= 1
            lines = random.sample(lines, len(lines))
            clean.update(clean_lines(lines, **clean_kwargs))
        return list(clean)[:sample_size]


def _get_lines(file: str, sample_kwargs: dict) -> dict:
    """Opens a file and runs sample_lines(): logs a warning if there's no content.

    Args:
        file: Filename.
        sample_kwargs: args for sample_lines.
    """
    file = pathlib.Path(file)
    with open(file) as f:
        lines = f.readlines()
    sample = sample_lines(lines, **sample_kwargs)
    # check for content
    if not len(sample):
        logging.warning(f"empty - {file}")
        return {}
    else:
        return sample


def _li_wrapper(func: Callable) -> dict:
    """Wraps `_raw` LI functions and generates an analysis.

    Args:
        func: A language identification function with the name `<LI tool>_raw`.

    See:
        For an example, see `stanza.raw`. New LI tools must follow this structure.
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
        langs = func(*args, **kwargs)
        t1 = perf_counter()
        time = round(t1 - t0, 3)
        # process result
        langs_dt = {i: c for i, c in collections.Counter(langs["labels"]).items()}
        langs_dt = dict(
            sorted(langs_dt.items(), key=lambda item: item[1], reverse=True)
        )
        dt = {
            "file": str(args[0]),
            "tool": tool,
            "langs": langs_dt,
            "time": time,
            "params": args[1],
        }
        return _lang_analysis(dt)

    return _inner


def stanza_raw(file: str, sample_kwargs: dict, nlp: stanza.Pipeline) -> dict:
    """Runs Stanza LI on a file, returns a dict of detected languages.

    See:
        The docstring for stanza_full() has more details."""
    sample = _get_lines(file, sample_kwargs)
    if not sample:
        return {"labels": []}
    docs = [stanza.Document([], text=t) for t in sample]
    nlp(docs)
    return {"labels": [doc.lang for doc in docs]}


@_li_wrapper
def stanza_full(file: str, sample_kwargs: dict, nlp: stanza.Pipeline) -> dict:
    """Runs Stanza LI on a file, returns a dict with analysis details.

    Args:
        file: Filepath to text file.
        sample_kwargs: Args passed to sample_lines().
        nlp: Stanza NLP pipeline.
    """
    return stanza_raw(file, sample_kwargs, nlp)


def fasttext_raw(
    file: str,
    sample_kwargs: dict,
    model: fasttext.FastText._FastText,
    scores: bool = False,
) -> dict:
    """Runs fastText LI on a file, returns a dict of detected languages and scores.

    See:
        The docstring for fasttext_full() has more details.
    """
    sample = _get_lines(file, sample_kwargs)
    if not sample:
        return {"labels": []}
    res = model.predict(sample)
    dt = {"labels": [y.replace("__label__", "") for x in res[0] for y in x]}
    if sample and scores:
        dt["scores"] = [y for x in res[1] for y in x]
    return dt


@_li_wrapper
def fasttext_full(
    file: str,
    sample_kwargs: dict,
    model: fasttext.FastText._FastText,
    scores: bool = False,
) -> dict:
    """Runs fasttext LI on a file, returns a dict with analysis details.

    Args:
        file: Text file.
        sample_kwargs: Args passes to sample_lines().
        model: A _FastText object.
        scores: Include scores for every line (discarded by default).

    !!! note
        fastText can provide scores for every text (line) by passing `scores=True`.
    """
    return fasttext_raw(file, sample_kwargs, model, scores)


def _lang_analysis(dt: dict) -> dict:
    """Runs a simple analysis on raw LI data and returns a more detailed dict.

    Args:
        dt: A dictionary produced within the _li_wrapper function.
    """
    langs = dt["langs"]
    if not langs:
        return dt
    top = max([v for v in langs.values()])
    size = sum([v for v in langs.values()])
    if len(langs) < 2:
        weight = None
    else:
        ls = [v for v in langs.values()]
        first = float(ls[0]) / size
        second = float(ls[1]) / size
        weight = round(first / second, 1)
    dt |= {
        "top": list(langs.keys())[list(langs.values()).index(top)],
        "weight": weight,
        "sample": sum([v for v in langs.values()]),
        "langs": {k: (v, round(v / size, 3)) for k, v in langs.items()},
    }
    return dt


def identify(
    files: str | list,
    sample_kwargs: dict,
    nlp: stanza.Pipeline | None,
    model: fasttext.FastText._FastText | None,
) -> pd.DataFrame:
    """Runs language identification on files and makes a DataFrame of results.

    Args:
        files: Filepath(s) to text file(s).
        sample_kwargs: Args passed to sample_lines() in each LI pipeline.
        nlp: (Optional) A Stanza NLP pipeline.
        model: (Optional) A _FastText object.
    """
    t0 = perf_counter()
    df = pd.DataFrame()
    if isinstance(files, str):
        files = [files]
    for file in files:
        dt_st = {}
        dt_fa = {}
        # run LI
        if nlp:
            dt_st = stanza_full(file, sample_kwargs, nlp)
        if model:
            dt_fa = fasttext_full(file, sample_kwargs, model)
        # make DataFrame
        temp = pd.DataFrame.from_records([dt_st, dt_fa])
        df = pd.concat([df, temp])

    t1 = perf_counter()
    t = round(t1 - t0, 2)
    logging.info(f"... {round(t,3)}s - {round(t/len(df), 2)}s / file")
    return df.reset_index(drop=True)


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
        lines = clean_lines(lines, 0)
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
    files: list, out: str = "file-concat", clean_kwargs: dict = clean_kwargs
) -> None:
    """Combines text files into raw and cleaned versions w/ XML tags.

    Args:
        files: List of filenames to read and analyze.
        out: Stem of output file name.
        clean_kwargs: Dict of args passed to `clean_lines()`.

    Notes:
        Use this to test various parameters for `clean_lines()` before running LI
        methods. Output files can be large if working with many texts.
    """
    dest = open(f"{out}.xml", "w")
    dest_clean = open(f"{out}-clean.xml", "w")
    for file in files:
        with open(file) as f:
            lines = f.readlines()
            dest.write(f'<file path="{file}">\n')
            dest.write("".join(lines))
            dest.write("\n</file>\n")
            lines = clean_lines(lines, **clean_kwargs)
            dest_clean.write(f'<file path="{file}">\n')
            dest_clean.write("\n".join(lines))
            dest_clean.write("\n</file>\n")
    dest.close()
    dest_clean.close()


if __name__ == "__main__":
    import doctest

    doctest.testmod()
