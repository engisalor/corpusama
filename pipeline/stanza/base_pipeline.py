"""A pipeline to process texts with Stanza.

Produces CoNLLU-formatted output and converts this to be compatible with Sketch Engine.

On CONLL-U, see:
    https://universaldependencies.org/format.html

On Sketch Engine's CoNNL-based format, see:
    https://www.sketchengine.eu/documentation/building-sketches-from-parsed-corpora

Optionally normalizes text with `uninorm`, see:
    Unitok: Michelfeit et al., 2014; Rychlý & Špalek, 2022.
    License and code available at <https://corpus.tools/wiki/Unitok>.

Designed for use with ReliefWeb texts processed with Corpusama. One or more texts can
be supplied in a file, with each text surrounded by `<doc>` XML tags. See README for
examples.
"""

import logging
import lzma
import os
import re
import subprocess  # nosec
from io import TextIOWrapper
from math import ceil
from pathlib import Path
from time import perf_counter
from typing import List
from xml.sax.saxutils import quoteattr  # nosec

import click
import stanza
from defusedxml.ElementTree import fromstring
from nltk import download, sent_tokenize
from numpy import array_split
from stanza import DownloadMethod
from stanza.utils.conll import CoNLL

try:
    import uninorm_4 as uninorm
except ModuleNotFoundError:
    from pipeline.stanza import uninorm_4 as uninorm


nltk_langs = {
    "en": "english",
    "fr": "french",
    "es": "spanish",
}


@click.group()
@click.option("--verbose/--quiet", default=False, show_default=True)
@click.option("--debug/--quiet", default=False, show_default=True)
@click.option(
    "--environ",
    multiple=True,
    default=["PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"],
    show_default=True,
    help="Set environment variables.",
)
def cli(verbose: bool, debug: bool, environ: List[str]):
    """A CLI to generate corpus files from ReliefWeb.

    \b
    Notes:
        - To set logging level, pass `--verbose` or `--debug` before other commands,
            e.g., `python base_pipeline.py --debug verify <FILE>`.
    """
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(format="%(asctime)s %(message)s", level=level)

    for arg in environ:
        environ = arg.split("=")
        os.environ[environ[0]] = environ[1]
        logging.info(f"environ - {environ[0]}={os.environ[environ[0]]}")


# def spellcheck(word, dictionaries="en_US,es_ES,fr_FR") -> bool:
#     """Checks if a word exists in hunspell dictionaries."""
#     if len(word.split()) > 1:
#         raise ValueError(f"word cannot include whitespace: '{word}'")
#     result = subprocess.run(
#         ["hunspell", "-d", dictionaries], input=word.encode(), capture_output=True
#     )
#     hunspell = result.stdout.decode()
#     hunspell = [x for x in hunspell.split("\n")[1:] if x][0][0]
#     if hunspell in ["&", "#"]:
#         return False
#     else:
#         return True


def wrap_lines(match, hunspell: bool = False, dictionaries="en_US,es_ES,fr_FR"):
    """Joins words split by a dash and new line if found in hunspell dictionaries."""
    candidate = "".join(match.groups())

    if not hunspell:
        # logging.debug(f"wrap -{candidate}")
        return candidate + "\n"
    # elif spellcheck(candidate, dictionaries):
    #     # logging.debug(f"wrap -{candidate}")
    #     return candidate + "\n"
    else:
        # logging.debug(f"reject -{candidate}")
        return match.group()


def clean_text(text: str, keep_empty=False) -> str:
    """Cleans texts to prepare for passing to an NLP pipeline."""
    lines = text.split("\n")
    lines = [uninorm.normalize_line(x, keep_empty=keep_empty) for x in lines]
    return "".join(lines)


def splice_mwt_lines(mwt_parts: list) -> str:
    """Splices multiword term CoNLLU lines into a Sketch Engine-compatible format."""
    old = list(
        map(
            ",".join,
            zip(*[mwt_parts[x] for x in range(len(mwt_parts)) if x > 0]),
        )
    )
    new = [(x if not len(set(x.split(","))) == 1 else x.split(",")[0]) for x in old]
    new[1] = mwt_parts[0][1]
    new[-1] = mwt_parts[0][-1]
    return "\t".join(new) + "\n"


def _conll_to_vert(source: TextIOWrapper, dest: TextIOWrapper) -> None:
    """Converts a source `.conllu` file to a `.vert` destination file.

    Notes:
        - Expects at least one metadata key-value in the source `.conllu` file, e.g.,
            `# id = 12`.
        - Joins multiword terms into single lines, e.g.,
            conllu files have 3 lines for `don't`, whereas in vertical format multiple
            tokens (do+not) appear on one line with a `,` separator.
        - Rewrites sentence id tags, starting at 0 for each document.
    """
    first_doc = True
    mwt_ids = []
    mwt_parts = []
    n = 0
    for i, line in enumerate(source):
        # write document tag
        if line.startswith("# newdoc"):
            if first_doc:
                dest.write("<doc")
                first_doc = False
            else:
                dest.write("\n</doc>\n<doc")
            new_doc = True
        # write sentence tag
        elif line.startswith("# sent_id"):
            if new_doc:
                n = 0
                dest.write(f'>\n<s id="{n}">\n')
                # to preserve existing ids
                # dest.write(re.sub(r"# sent_id = (\d+)", r'>\n<s id="\1">', line))
                new_doc = False
            else:
                n += 1
                dest.write(f'\n<s id="{n}">\n')
                # dest.write(re.sub(r"# sent_id = (\d+)", r'\n<s id="\1">', line))
        # ignore text line
        elif line.startswith("# text"):
            pass
        # write metadata
        elif line.startswith("#"):
            tup = re.search(r"# (\S+) = (.*)\n", line).groups()
            line = f" {tup[0]}={quoteattr(tup[1])}"
            dest.write(line)
        # parse content
        elif line.startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
            # activate mwt line logic
            if re.match(r"\d+-\d+", line):
                # write any preceding mwt line group
                if mwt_ids:
                    spliced = splice_mwt_lines(mwt_parts)
                    dest.write(spliced)
                    # dest.write(line)
                    mwt_parts = []
                    mwt_ids = []
                # activate mwt line collection
                ids = [int(x) for x in line.split("\t")[0].split("-")]
                mwt_ids = [str(x) for x in range(ids[0], ids[1] + 1)]
            # parse mwt content
            if mwt_ids:
                id = re.match(r"\d+", line).group()
                # collect mwt line member
                if id in mwt_ids:
                    mwt_parts.append([x.strip() for x in line.split("\t")])
                # write mwt line group
                else:
                    spliced = splice_mwt_lines(mwt_parts)
                    dest.write(spliced)
                    dest.write(line)
                    mwt_parts = []
                    mwt_ids = []
            # write single-word line
            else:
                dest.write(line)
        # activate end of sentence logic
        else:
            # sanity check
            if line.strip():
                raise ValueError(f"unused non-empty line - {i} - {line}")
            # write any trailing mwt group
            if mwt_ids:
                spliced = splice_mwt_lines(mwt_parts)
                dest.write(spliced)
                mwt_parts = []
                mwt_ids = []
            # end sentence tag
            dest.write("</s>")
    # end document tag
    dest.write("\n</doc>\n")


@cli.command()
@click.argument(
    "file",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, allow_dash=False, path_type=Path),
)
@click.option(
    "--force/--no-force",
    default=True,
    show_default=True,
    help="Overwrite existing output files.",
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
def conll_to_vert(
    file: List[Path], force: bool, compress: bool, keep: bool, threads: int
) -> None:
    """Converts a `.conllu` file to a SkE-compatible `.vert` format.

    \b
    Notes:
        - Accepts `.conllu` and `.conllu.xz` files.
        - See `_conll_to_vert` docstring for more details.
    """
    for _f in file:
        dest = _f.with_suffix(".vert")
        if _f.suffix == ".xz":
            dest = _f.with_suffix("").with_suffix(".vert")
        dest_xz = dest.with_suffix(".vert.xz")

        if not force and (dest.exists() or (compress and dest_xz.exists())):
            raise ValueError("Output already exists: use `--force` to overwrite")

        with open(dest, "w") as d:
            if _f.suffix == ".xz":
                f = lzma.open(_f, "rt")
            else:
                f = open(_f)
            _conll_to_vert(f, d)
            f.close()

        if compress:
            dest_xz.unlink(missing_ok=True)
            cmd = ["xz", dest, "-T", str(threads)]
            if keep:
                cmd.append("-k")

            subprocess.run(cmd)  # nosec


@cli.command()
@click.argument(
    "file",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, allow_dash=False, path_type=Path),
)
def verify(file: List[Path]) -> None:
    """Counts docs in source and dest files (`.txt`, `.conllu`, `.vert` and `.xz`).

    Notes:
        - Exits silently on success, raises an exception if counts don't match.
    """

    def process_file(file: Path, f) -> int:
        docs = 0
        for line in f:
            if ".conllu" in file.suffixes and line.startswith("# newdoc"):
                docs += 1
            elif line.startswith("<doc id="):
                docs += 1
        return docs

    def inner(file: Path) -> int:
        if file.suffix == ".xz":
            with lzma.open(file, "rt") as f:
                docs = process_file(file, f)
        else:
            with open(file) as f:
                docs = process_file(file, f)
        return docs

    for _f in file:
        if _f.suffix == ".xz":
            _f = _f.with_suffix("")

        txt = conllu = _f.with_suffix(".txt")
        conllu = _f.with_suffix(".conllu")
        vert = _f.with_suffix(".vert")
        conllu_xz = _f.with_suffix(".conllu.xz")
        vert_xz = _f.with_suffix(".vert.xz")
        txt_xz = conllu = _f.with_suffix(".txt.xz")

        results = {}
        for f in set([_f, txt, conllu, vert, txt_xz, conllu_xz, vert_xz]):
            if f.exists():
                results[f.name] = inner(f)
                logging.debug(f"verify - found - {f.name}")
        counts = set(results.values())
        if len(counts) != 1:
            raise ValueError(f"verify fail - {results.items()}")
        else:
            logging.info(f"verify pass - {results.items()}")


class NLP:
    """Class to manage Stanza NLP pipelines for files generated from Corpusama."""

    def _to_conll_inner(self) -> None:
        t0 = perf_counter()
        xml = fromstring(self.meta + "</doc>\n")
        id = xml.items()[0][1]
        file_id = xml.items()[1][1]
        if self.uninorm:
            doc = clean_text(self.doc)
            logging.debug(f"{self.n} - clean - {id}/{file_id}")
        else:
            doc = self.doc
        if self.wrap:
            a = re.compile(r"( \w+)-\n(\w+ *)")
            doc = a.sub(wrap_lines, doc)
            logging.debug(f"{self.n} - wrap - {id}/{file_id}")
        _bytes = len(doc.encode())

        with open(self.dest, "a") as f:
            f.write(
                "# newdoc\n"
                + "\n".join([f"# {x[0]} = {x[1]}" for x in xml.items()])
                + "\n"
            )

        if _bytes < self.big:
            logging.debug(f"{self.n} - neural - {id}/{file_id}")
            doc = self.nlp.process(doc)
            CoNLL.write_doc2conll(doc, self.dest, "a")
        else:
            doc = sent_tokenize(doc, self.nltk_lang)
            logging.debug(f"{self.n} - split - {id}/{file_id}")
            n_chunks = ceil(_bytes / self.chunk)
            array = array_split(doc, n_chunks)
            array = [x for x in array if x.size > 0]
            for chunk in array:
                _size = len("\n".join(chunk).encode())
                if not _size > self.chunk * self.max:
                    logging.debug(f"{self.n} - chunk - {_size}")
                    docs = self.nlp.bulk_process(chunk)
                    for d in docs:
                        CoNLL.write_doc2conll(d, self.dest, "a")
                else:
                    logging.debug(f"{self.n} - big chunk - {_size}")
                    for unit in chunk:
                        __size = len(unit.encode())
                        if __size > self.chunk:
                            lines = unit.split("\n")
                            n_mini = ceil(__size / self.chunk)
                            mini_array = array_split(lines, n_mini)
                            mini_chunk = ["\n".join(x) for x in mini_array]
                            mini_docs = self.nlp.bulk_process(mini_chunk)
                            for doc in mini_docs:
                                CoNLL.write_doc2conll(doc, self.dest, "a")
                            logging.debug(
                                f"{self.n} - big chunk - force split - first 100 chars"
                                + f" - {repr(mini_chunk[0][:100])}"
                            )
                        else:
                            doc = self.nlp.process(unit)
                            CoNLL.write_doc2conll(doc, self.dest, "a")

        t1 = perf_counter()
        secs = t1 - t0
        msg = f"{self.n} - {_bytes:,} - {_bytes/secs:,.0f} b/s - {id}/{file_id}"
        logging.info(msg)
        self.doc = ""
        self.n += 1

    def _process_file(self, f) -> None:
        for i, line in enumerate(f):
            if line.startswith('<doc id="'):
                self.meta = line
                self.doc = ""
            elif line.startswith("</doc>"):
                self._to_conll_inner()
            else:
                self.doc += line
        if self.doc:
            self._to_conll_inner()

    def start_nlp(self) -> None:
        download("punkt", quiet=True)
        self.nlp = stanza.Pipeline(
            self.lang,
            processors=self.processors,
            download_method=self.download_method,
            logging_level="WARN",
            tokenize_batch_size=32,  # 32
            mwt_batch_size=50,  # 50
            pos_batch_size=100,  # 100
            lemma_batch_size=50,  # 50
            depparse_batch_size=200,  # 5000
        )

    def to_conll(self) -> None:
        self.dest.unlink(missing_ok=True)
        self.start_nlp()
        if self.source.suffix == ".xz":
            with lzma.open(self.source, "rt") as f:
                self._process_file(f)
        else:
            with open(self.source) as f:
                self._process_file(f)

    def __init__(
        self,
        file: str,
        lang: str,
        processors: str,
        uninorm: bool,
        wrap: bool,
        big: int,
        chunk: int,
        max: int,
        tokenize_batch_size: int,
        mwt_batch_size: int,
        pos_batch_size: int,
        lemma_batch_size: int,
        depparse_batch_size: int,
        download_method: DownloadMethod = DownloadMethod.REUSE_RESOURCES,
    ) -> None:
        self.file = file
        self.source = Path(self.file)
        self.dest = self.source.with_suffix(self.source.suffix + ".conllu")
        self.doc = ""
        self.meta = ""
        self.n = 0
        self.uninorm = uninorm
        self.wrap = wrap
        self.big = big
        self.chunk = chunk
        self.max = max
        self.lang = lang
        self.nltk_lang = nltk_langs[lang]
        self.processors = processors
        self.tokenize_batch_size = tokenize_batch_size
        self.mwt_batch_size = mwt_batch_size
        self.pos_batch_size = pos_batch_size
        self.lemma_batch_size = lemma_batch_size
        self.depparse_batch_size = depparse_batch_size
        self.download_method = download_method
        logging.info(f"file={file}")
        logging.info(f"uninorm={uninorm}")
        logging.info(f"wrap={wrap}")
        logging.info(f"big={big:,}")
        logging.info(f"chunk={chunk:,}")
        logging.info(f"max={max:,}")


@cli.command()
@click.argument(
    "file",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, allow_dash=False, path_type=Path),
)
@click.option(
    "-l",
    "--lang",
    required=True,
    type=click.STRING,
    help="Language (`en`, `es`, etc.).",
)
@click.option(
    "-p",
    "--processors",
    default="tokenize,mwt,pos,lemma,depparse",
    type=click.STRING,
    show_default=True,
    help="Stanza processors.",
)
@click.option(
    "-b",
    "--big",
    type=click.INT,
    default=10000,
    show_default=True,
    help="""Disable neural sentence segmentation at n bytes of text
and use rule-based segmentation instead (`0` never uses neural).""",
)
@click.option(
    "-c",
    "--chunk",
    type=click.INT,
    default=1000,
    show_default=True,
    help="""Desired chunksize in bytes to feed Stanza for big docs
(permits longer sentences until `max` size is reached.""",
)
@click.option(
    "-m",
    "--max",
    type=click.INT,
    default=8,
    show_default=True,
    help="""Largest multiple of chunksize allowed before forcing
smaller sentence segmentation, e.g., `8*chunk` bytes.""",
)
@click.option(
    "--wrap/--no-wrap",
    default=True,
    show_default=True,
    help="Remove hyphens in line-wrapped words.",
)
@click.option(
    "--uninorm/--no-uninorm",
    default=True,
    show_default=True,
    help="Clean docs with `uninorm` (See module docstring for details).",
)
@click.option(
    "--tokenize_batch_size",
    default=32,
    type=click.INT,
    show_default=True,
    help="Stanza option, (upstream default = `32`)",
)
@click.option(
    "--mwt_batch_size",
    default=50,
    type=click.INT,
    show_default=True,
    help="Stanza option, (upstream default = `50`)",
)
@click.option(
    "--pos_batch_size",
    default=100,
    type=click.INT,
    show_default=True,
    help="Stanza option, (upstream default = `100`)",
)
@click.option(
    "--lemma_batch_size",
    default=50,
    type=click.INT,
    show_default=True,
    help="Stanza option, (upstream default = `50`)",
)
@click.option(
    "--depparse_batch_size",
    default=200,
    type=click.INT,
    show_default=True,
    help="Stanza option, (upstream default = `5000`)",
)
def to_conll(
    file: List[Path],
    lang: str,
    processors: str,
    big: int,
    chunk: int,
    max: int,
    wrap: bool,
    uninorm: bool,
    tokenize_batch_size: int,
    mwt_batch_size: int,
    pos_batch_size: int,
    lemma_batch_size: int,
    depparse_batch_size: int,
) -> None:
    """Makes `.conllu` files for docs in plaintext file demarcated with <doc> tags."""
    for _f in file:
        nlp = NLP(
            _f,
            lang,
            processors,
            uninorm,
            wrap,
            big,
            chunk,
            max,
            tokenize_batch_size,
            mwt_batch_size,
            pos_batch_size,
            lemma_batch_size,
            depparse_batch_size,
        )
        nlp.to_conll()


if __name__ == "__main__":
    cli()
