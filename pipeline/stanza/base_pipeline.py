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

import argparse
import logging
import lzma
import os
import re

# import subprocess
from math import ceil
from pathlib import Path
from time import perf_counter
from xml.sax.saxutils import quoteattr  # nosec

import stanza
import uninorm_4 as uninorm
from defusedxml.ElementTree import fromstring
from nltk import download, sent_tokenize
from numpy import array_split
from stanza import DownloadMethod
from stanza.utils.conll import CoNLL

nltk_langs = {
    "en": "english",
    "fr": "french",
    "es": "spanish",
}


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


def clean_text(text: str) -> str:
    """Cleans texts to prepare for passing to an NLP pipeline."""
    lines = text.split("\n")
    lines = [uninorm.normalize_line(x) for x in lines]
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


def conll_to_vert(file: str) -> None:
    """Converts a `.conllu` file to a SkE-compatible vertical format."""
    source = Path(file)
    dest = source.with_suffix(".vert")
    dest.unlink(missing_ok=True)
    with open(source) as f:
        with open(dest, "w") as d:
            first_doc = True
            mwt_ids = []
            mwt_parts = []
            n = 0
            for i, line in enumerate(f):
                # write document tag
                if line.startswith("# newdoc"):
                    if first_doc:
                        d.write("<doc")
                        first_doc = False
                    else:
                        d.write("\n</doc>\n<doc")
                    new_doc = True
                # write sentence tag
                elif line.startswith("# sent_id"):
                    if new_doc:
                        n = 0
                        d.write(f'>\n<s id="{n}">\n')
                        # to preserve existing ids
                        # d.write(re.sub(r"# sent_id = (\d+)", r'>\n<s id="\1">', line))
                        new_doc = False
                    else:
                        n += 1
                        d.write(f'\n<s id="{n}">\n')
                        # d.write(re.sub(r"# sent_id = (\d+)", r'\n<s id="\1">', line))
                # ignore text line
                elif line.startswith("# text"):
                    pass
                # write metadata
                elif line.startswith("#"):
                    tup = re.search(r"# (\S+) = (.*)\n", line).groups()
                    line = f" {tup[0]}={quoteattr(tup[1])}"
                    d.write(line)
                # parse content
                elif line.startswith(
                    ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
                ):
                    # activate mwt line logic
                    if re.match(r"\d+-\d+", line):
                        # write any preceding mwt line group
                        if mwt_ids:
                            spliced = splice_mwt_lines(mwt_parts)
                            d.write(spliced)
                            # d.write(line)
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
                            d.write(spliced)
                            d.write(line)
                            mwt_parts = []
                            mwt_ids = []
                    # write single-word line
                    else:
                        d.write(line)
                # activate end of sentence logic
                else:
                    # sanity check
                    if line.strip():
                        raise ValueError(f"unused non-empty line - {i} - {line}")
                    # write any trailing mwt group
                    if mwt_ids:
                        spliced = splice_mwt_lines(mwt_parts)
                        d.write(spliced)
                        mwt_parts = []
                        mwt_ids = []
                    # end sentence tag
                    d.write("</s>")
            # end document tag
            d.write("\n</doc>")


class NLP:
    """Runs Stanza NLP on files generated from Corpusama."""

    def _to_conll_inner(self) -> None:
        t0 = perf_counter()
        xml = fromstring(self.meta + "</doc>\n")
        id = xml.items()[0][1]
        file_id = xml.items()[1][1]
        if self.uninorm:
            doc = clean_text(self.doc)
            logging.debug(f"{self.n} - cleaned - {id}/{file_id}")
        else:
            doc = self.doc
        if self.wrap:
            a = re.compile(r"( \w+)-\n(\w+ *)")
            doc = a.sub(wrap_lines, doc)
            logging.debug(f"{self.n} - wrapped - {id}/{file_id}")
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
                if not _size > self.chunk * self.force:
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
            self.language,
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

    def verify(self) -> None:
        def process_file(file: Path, f) -> int:
            docs = 0
            for line in f:
                if ".conllu" in file.suffixes and line.startswith("# newdoc"):
                    docs += 1
                elif line.startswith("<doc id="):
                    docs += 1
            return docs

        def inner(file: Path) -> int:
            if self.source.suffix == ".xz":
                with lzma.open(self.source, "rt") as f:
                    docs = process_file(file, f)
            else:
                with open(file) as f:
                    docs = process_file(file, f)
            logging.info(f"verify - {docs:,} docs in {file}")
            return docs

        s = inner(self.source)
        d = inner(self.dest)
        v = None
        if self.source.with_suffix(".vert").exists():
            v = inner(self.source.with_suffix(".vert"))
        if not s == d:
            raise ValueError(f"verify - doc counts {s} != {d} .conllu")
        if v and v != s:
            raise ValueError(f"verify - doc counts {s} != {v} .vert")

    def __init__(
        self,
        file: str,
        language: str,
        processors: str = "tokenize,mwt,pos,lemma,depparse",
        uninorm: bool = True,
        wrap: bool = True,
        big: int = 0,
        chunk: int = 1000,
        force: int = 10,
        download_method: DownloadMethod = DownloadMethod.REUSE_RESOURCES,
    ) -> None:
        self.file = file
        self.source = Path(self.file)
        self.dest = self.source.with_suffix(".conllu")
        self.doc = ""
        self.meta = ""
        self.n = 0
        self.uninorm = uninorm
        self.wrap = wrap
        self.big = big
        self.chunk = chunk
        self.force = force
        self.language = language
        self.nltk_lang = nltk_langs[language]
        self.processors = processors
        self.download_method = download_method
        logging.info(f"file={file}")
        logging.info(f"uninorm={uninorm}")
        logging.info(f"wrap={wrap}")
        logging.info(f"big={big:,}")
        logging.info(f"chunk={chunk:,}")
        logging.info(f"force={force:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--environ",
        nargs="*",
        default=["PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"],
        help="Environment variables",
    )
    parser.add_argument(
        "--nlp",
        default="tokenize,mwt,pos,lemma,depparse",
        help="Stanza processors (default `tokenize,mwt,pos,lemma,depparse`)",
    )
    parser.add_argument(
        "--big",
        type=int,
        default=0,
        help="""Disable neural sentence segmentation at n bytes of text
          and use rule-based segmentation instead (default `0` never use neural)""",
    )
    parser.add_argument(
        "--chunk",
        type=int,
        default=1000,
        help="""Desired chunksize in bytes to feed Stanza for big docs
          (default `1000`; permits longer sentences until `force` size is reached""",
    )
    parser.add_argument(
        "--force",
        type=int,
        default=10,
        help="""Largest multiple of chunksize allowed before forcing
        smaller sentence segmentation (default `10`, e.g., `10*chunk` bytes)""",
    )
    parser.add_argument(
        "-c",
        "--conll",
        action="store_true",
        help="Run the pipeline and output `.conllu` files",
    )
    parser.add_argument(
        "-s",
        "--ske",
        action="store_true",
        help="Convert `.conllu` output to Sketch Engine `.vert`",
    )
    parser.add_argument(
        "-u", "--uninorm", action="store_true", help="Clean docs with `uninorm`"
    )
    parser.add_argument(
        "-w", "--wrap", action="store_true", help="Remove hyphens in line-wrapped words"
    )
    parser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="Compare source files with output files",
    )
    parser.add_argument("-V", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("-D", "--debug", action="store_true", help="Debug logging")
    parser.add_argument("lang", help="Language code for Stanza, e.g. `en`")
    parser.add_argument("file", nargs="+", help="Text file(s) to process")
    args = parser.parse_args()

    if args.debug:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(format="%(asctime)s %(message)s", level=level)

    for arg in args.environ:
        environ = arg.split("=")
        os.environ[environ[0]] = environ[1]
        logging.info(f"{environ[0]}={os.environ[environ[0]]}")

    for file in args.file:
        file = Path(file)
        nlp = NLP(
            file,
            args.lang,
            args.nlp,
            args.uninorm,
            args.wrap,
            args.big,
            args.chunk,
            args.force,
        )

        if args.conll:
            nlp.to_conll()
        if args.ske:
            conll_to_vert(file.with_suffix(".conllu"))
        if args.verify:
            nlp.verify()
