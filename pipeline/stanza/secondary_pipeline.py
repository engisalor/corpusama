"""A secondary pipeline for adding additional data to corpus .vert.xz files. """

import logging
import lzma
import os
import re
import string
import subprocess  # nosec
from collections import Counter, OrderedDict
from io import TextIOWrapper
from pathlib import Path
from typing import List
from uuid import UUID, uuid4
from xml.sax.saxutils import quoteattr  # nosec

import click
import pandas as pd
from defusedxml import ElementTree
from stanza import Pipeline

_u = uuid4()
# _u = "hello"
s = UUID(str(_u))
s
try:
    import uninorm_4 as uninorm
except ModuleNotFoundError:
    from pipeline.stanza import uninorm_4 as uninorm


# TODO: test running secondary pipeline main several times
# in same dir: does it update files correctly or break?

# default settings
Path(".temp/").mkdir(exist_ok=True)
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


def chunks(ls, n):
    for i in range(0, len(ls), n):
        yield ls[i : i + n]


def sort_files(files):
    return sorted([x for x in files], key=lambda x: int(x.suffixes[0].strip(".")))


def get_xml_attrs(line, closing="</s>") -> OrderedDict:
    dt = OrderedDict(ElementTree.fromstring(line + closing).items())
    return OrderedDict((k, quoteattr(v)) for k, v in dt.items())


def _update_tag(dt, struct, add_first):
    s = f"<{struct} "
    for x in add_first:
        if dt.get(x):
            s += f'{x}={dt[x]} '
            del dt[x]
    for k, v in dt.items():
        if v:
            s += f"{k}={v} "
    s = s.rstrip()
    return s + ">\n"
    

def update_s_tag(dt):
    return _update_tag(dt,"s", ["id"])


def update_doc_tag(line, doc_n, uuid: bool) -> tuple:
    dt = get_xml_attrs(line, "</doc>")
    if uuid:
        dt["ref"] = quoteattr(str(uuid4()))
    else:
        dt["ref"] = quoteattr(str(doc_n))
    s = _update_tag(dt, "doc", ["id", "file_id", "ref"])
    return s, doc_n + 1


def get_sent_lid_tsv(file):
    file = Path(str(file) + ".lid.tsv")
    if not file.exists():
        raise FileNotFoundError(f"langid file missing, run langid(): {file}")
    df = pd.read_csv(file, sep="\t")
    df.columns = ["index", "lang"]
    df.set_index("index", inplace=True)
    df.sort_index(inplace=True)
    df["lang"] = df["lang"].apply(quoteattr)
    return df


def _process_batch(nlp: Pipeline, i: int, outfile: Path, sentences, indexes):
    docs = nlp.bulk_process(sentences)
    _df = pd.DataFrame({"index": indexes, "lang": [doc.lang for doc in docs]})
    _df.to_csv(outfile, sep="\t", mode="a", index=False, header=False)
    process = False
    indexes = []
    sentences = []
    return process, indexes, sentences


def _sentence_id(_f: Path, language, short, long, batch):
    outfile = Path(str(_f) + ".lid.tsv")
    sentence = []
    indexes = []
    sentences = []
    process = False
    nlp = Pipeline(
        lang="multilingual",
        processors="langid",
        download_method=None,
        langid_lang_subset=language,
    )
    if _f.suffix == ".xz":
        _open = lzma.open
        mode = "rt"
    elif _f.suffix == ".vert":
        mode = "r"
        _open = open
    else:
        raise Warning(f"file must end in .vert or .xz: {_f}")
    logging.debug("... make empty file for pandas appends")
    with open(outfile, "w") as f:
        f.write("")
    logging.debug("... read corpus file")
    with _open(_f, mode) as f:
        for i, line in enumerate(f):
            # start new sentence
            if re.match("<s", line):
                if len(sentences) == batch:
                    process = True
                index = i
                sentence = []
            # process sentence
            elif re.match("</s", line):
                clean = clean_lines([" ".join(sentence)])
                tokens = 0
                if clean:
                    tokens = len(clean[0].split())
                # ignore too short or long
                if tokens >= short and tokens < long:
                    sentences.append(clean[0])
                    indexes.append(index)
                # process long sentence separately in chunks
                if tokens >= long:
                    logging.debug(f"... {index} chunk {tokens} tokens")
                    ls = clean[0].split()
                    docs = [" ".join(x) for x in chunks(ls, long)]
                    docs = nlp.bulk_process(docs)
                    dt = Counter([doc.lang for doc in docs])
                    _df = pd.DataFrame(
                        {"index": [index], "lang": [dt.most_common()[0][0]]}
                    )
                    _df.to_csv(outfile, sep="\t", mode="a", index=False, header=False)
            # collect sentence tokens
            else:
                res = re.match(r"\d+\t(\w+)", line)
                if res:
                    sentence.append(res.group(1))
            if process:
                logging.debug(f"... process batch {i}")
                process, indexes, sentences = _process_batch(
                    nlp, i, outfile, sentences, indexes
                )
        if indexes:
            logging.debug("... process remainder")
            _, _, _ = _process_batch(nlp, i, outfile, sentences, indexes)


@click.group()
@click.option("--verbose/--quiet", default=False, show_default=True)
@click.option("--debug/--quiet", default=False, show_default=True)
def cli(verbose: bool, debug: bool):
    """A CLI for adding additional data to corpus .vert.xz files.

    \b
    Notes:
        - To set logging level, pass `--verbose` or `--debug` before other commands,
            e.g., `python secondary_pipeline.py --debug <CMD> <FILE>`.
    """
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(format="%(asctime)s %(message)s", level=level)


@cli.command()
@click.argument(
    "file",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, allow_dash=False, path_type=Path),
)
@click.option(
    "--short",
    type=click.INT,
    default=4,
    show_default=True,
    help="Shortest sentence length (alphabetical tokens) for language identification.",
)
@click.option(
    "--long",
    type=click.INT,
    default=500,
    show_default=True,
    help="Longest sentence length (alphabetical tokens) to process in batches.",
)
@click.option(
    "--batch",
    type=click.INT,
    default=10000,
    show_default=True,
    help="Number of sentences to process per batch (excluding short and long).",
)
@click.option(
    "--language",
    multiple=True,
    default=["en", "fr", "es"],
    show_default=True,
    help="Languages to consider in langid options.",
)
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    show_default=True,
    help="Re-run language identification even if output file exists.",
)
def langid(
    file: List[Path],
    short: int,
    long: int,
    batch: int,
    language: list,
    overwrite: bool,
):
    """Makes a .tsv with language ID results for a .vert(.xz) file (per sentence).

    Notes:
        - Output .tsv file contains the line index for a sentence's <s> tag and the
            detected language for the sentence.
        - Faster on a GPU but can work on modest CPU-based machines. Lower --batch if
            memory errors occur (although this will reduce speed overall).
        - Use --language to detect different languages; adding more and unlikely
            languages inceases noise.
        - Short sentences are ignored due to poor performance (adjust with --short).
        - Sentences a cleaned to only evaluate alphabetical chars. See clean_lines()
            for details and and uninorm_4.py for acknowledgements.
    """
    for _f in file:
        outfile = Path(str(_f) + ".lid.tsv")
        if outfile.exists() and not overwrite:
            logging.info(f"... skip LID for {_f}")
        else:
            logging.info(f"... LID for {_f}")
            _sentence_id(_f, language, short, long, batch)


@cli.command()
@click.argument(
    "file",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, allow_dash=False, path_type=Path),
)
@click.option(
    "--doc_n",
    type=click.INT,
    default=1,
    show_default=True,
    help="Starting number for document reference tags.",
)
@click.option(
    "--docx_n",
    type=click.INT,
    default=1,
    show_default=True,
    help="Starting number for source file (docx) reference tags.",
)
@click.option(
    "--uuid/--no-uuid",
    default=False,
    show_default=True,
    help="Generate UUIDs for every doc and docx line (overrides --doc_n, --docx_n).",
)
@click.option(
    "--clear/--no-clear",
    default=False,
    show_default=True,
    help="Remove the input files and remove the .TMP suffix from new files.",
)
@click.option(
    "--compress/--no-compress",
    default=True,
    show_default=True,
    help="Compress output files with XZ.",
)
@click.option(
    "--keep/--no-keep",
    default=False,
    show_default=True,
    help="Keep `.vert` files after XZ compression.",
)
@click.option(
    "-T",
    "--threads",
    type=click.INT,
    default=0,
    show_default=True,
    help="Number of threads used for XZ compression (0 = maximum).",
)
@click.option(
    "--langid/--no-langid",
    default=False,
    show_default=True,
    help="Add sentence-level language ID results from langid() (run separately).",
)
def main(
    file: List[Path],
    doc_n: int,
    docx_n: int,
    uuid: bool,
    clear: bool,
    compress: bool,
    keep: bool,
    threads: int,
    langid: bool,
) -> None:
    """Runs a secondary pipeline on corpus .<int>.vert(.xz) files.

    \b
    Notes:
        - Outputs files with a .TMP extension unless --clear (deletes original files).
        - Replaces old <doc... ref"<int>"> values, increments +1 for each document
            for all vert or vert.xz files provided.
        - Adds a <docx id="<int>" name="<filename>"> tag.
        - Expects filenames with .<int>.vert(.xz) suffixes: uses <int> to sort when
            files have the same stem.
        - Expects preexisting <doc> tags starting with "id" and "file_id" attributes.
        - Adds sentence-level language ID if --langid and langid() is run beforehand.
    """

    def _inner(
        f: TextIOWrapper,
        d: TextIOWrapper,
        doc_n: int,
        file: Path,
        langid: bool,
        uuid: bool,
    ):
        if langid:
            df = get_sent_lid_tsv(file)
        for i, line in enumerate(f):
            if line.startswith('<doc id="'):
                line, doc_n = update_doc_tag(line, doc_n, uuid)
            elif langid and line.startswith("<s"):
                try:
                    lang = df.loc[i]["lang"]
                    dt = get_xml_attrs(line)
                    dt["lang"] = lang
                    line = update_s_tag(dt)
                except KeyError:
                    pass
            if line.startswith("<docx") or line.startswith("</docx"):
                pass
            else:
                d.write(line)
        return doc_n

    # run
    file = sort_files(file)
    for _f in file:
        _f = Path(_f)
        if _f.suffix == ".xz":
            open_func = lzma.open
            mode = "rt"
            temp = _f.with_suffix("")
        elif _f.suffix == ".vert":
            mode = "r"
            open_func = open
            temp = _f
        else:
            raise Warning(f"_f must end in .vert or .xz: {_f}")
        dest = Path(str(temp) + ".TMP")
        name = quoteattr(_f.name)
        if uuid:
            _ref = quoteattr(str(uuid4()))
        else:
            _ref = quoteattr(str(docx_n))
        with open_func(_f, mode) as f:
            with open(dest, "w") as d:
                d.write(f"<docx ref={_ref} name={name}>\n")
                doc_n = _inner(f, d, doc_n, _f, langid, uuid)
                d.write("</docx>\n")
        if compress:
            cmd = ["xz", dest, "-T", str(threads)]
            if keep:
                cmd.append("-k")
            subprocess.run(cmd)  # nosec
            os.rename(dest.with_suffix(".TMP.xz"), dest.with_suffix(".xz.TMP"))
            dest = dest.with_suffix(".xz.TMP")
        if clear:
            _f.unlink()
            os.rename(dest, dest.with_suffix(""))
        docx_n += 1


if __name__ == "__main__":
    cli()
