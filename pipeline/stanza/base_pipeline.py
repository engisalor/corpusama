"""A pipeline to process texts with Stanza and output a SkE-conll format.

`SkE-conll` here refers to a format used by Sketch Engine based on conll. Primary
differences include reshaping `# key = value` comments into XML attributes; collapsing
multiword-terms (e.g., `del` in Spanish) from multiple lines in conll to one in SkE).

On SkE's SkE-conll format, see:
    https://www.sketchengine.eu/documentation/building-sketches-from-parsed-corpora

On CONLL-U format, see:
    https://universaldependencies.org/format.html
"""

import argparse
import logging
import lzma
import re
from math import ceil
from pathlib import Path
from time import perf_counter
from xml.sax.saxutils import quoteattr  # nosec

import stanza
from defusedxml.ElementTree import fromstring
from numpy import array_split
from stanza import DownloadMethod
from stanza.utils.conll import CoNLL


def conll_to_vert(file: str) -> None:
    """Converts a `.conll` file to a SkE-compatible vertical format."""
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
                if line.startswith("# newdoc"):
                    if first_doc:
                        d.write("<doc")
                        first_doc = False
                    else:
                        d.write("\n</doc>\n<doc")
                    new_doc = True
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
                elif line.startswith("# text"):
                    pass
                elif line.startswith("#"):
                    tup = re.search(r"# (\S+) = (.*)\n", line).groups()
                    line = f" {tup[0]}={quoteattr(tup[1])}"
                    d.write(line)
                elif line.startswith(
                    ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
                ):
                    if re.match(r"\d+-\d+", line):
                        ids = [int(x) for x in line.split("\t")[0].split("-")]
                        mwt_ids = [str(x) for x in range(ids[0], ids[1] + 1)]
                    if mwt_ids:
                        id = re.match(r"\d+", line).group()
                        if id in mwt_ids:
                            mwt_parts.append([x.strip() for x in line.split("\t")])
                        else:
                            new = list(
                                map(
                                    ",".join,
                                    zip(
                                        *[
                                            mwt_parts[x]
                                            for x in range(len(mwt_parts))
                                            if x > 0
                                        ]
                                    ),
                                )
                            )
                            new = [
                                (
                                    x
                                    if not len(set(x.split(","))) == 1
                                    else x.split(",")[0]
                                )
                                for x in new
                            ]
                            new[1] = mwt_parts[0][1]
                            new[-1] = mwt_parts[0][-1]
                            d.write("\t".join(new) + "\n")
                            d.write(line)
                            mwt_parts = []
                            mwt_ids = []
                    else:
                        d.write(line)
                else:
                    d.write("</s>")
            d.write("\n</doc>")


class NLP:
    """Runs Stanza NLP on files generated from Corpusama."""

    def _to_conll_inner(self) -> None:
        t0 = perf_counter()
        xml = fromstring(self.meta + "</doc>\n")
        with open(self.dest, "a") as f:
            f.write(
                "# newdoc\n"
                + "\n".join([f"# {x[0]} = {x[1]}" for x in xml.items()])
                + "\n"
            )

        _bytes = len(self.doc.encode())
        n_chunks = ceil(_bytes / self.batch)
        lines = self.doc.split("\n\n")
        arrays = array_split(lines, n_chunks)
        for chunk in arrays:
            docs = self.nlp.bulk_process(chunk)
            for doc in docs:
                CoNLL.write_doc2conll(doc, self.dest, "a")

        t1 = perf_counter()
        secs = t1 - t0
        id = xml.items()[0][1]
        file_id = xml.items()[1][1]
        msg = "".join(
            [
                f"{self.n} - {_bytes:,} - {len(arrays):,}/{n_chunks} chunk(s)",
                f"- {_bytes/secs:,.0f} bytes/s - id={id} file_id={file_id}",
            ]
        )
        logging.info(msg)
        self.doc = ""
        self.n += 1

    def _process_file(self, f):
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

    def to_conll(self) -> None:
        self.dest.unlink(missing_ok=True)
        self.nlp = stanza.Pipeline(
            self.language,
            processors=self.processors,
            download_method=self.download_method,
            logging_level="WARN",
        )
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
        batch: float = 1024,
        download_method: DownloadMethod = DownloadMethod.REUSE_RESOURCES,
    ) -> None:
        self.file = file
        self.source = Path(self.file)
        self.dest = self.source.with_suffix(".conllu")
        self.doc = ""
        self.meta = ""
        self.n = 0
        self.batch = batch
        self.language = language
        self.processors = processors
        self.download_method = download_method


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument(
        "-b",
        "--batch",
        type=int,
        help="Bytes to process per file chunk, default `1024`",
        default=1024,
    )
    parser.add_argument(
        "-n",
        "--nlp",
        help="Stanza processors, e.g. `tokenize,mwt,pos,lemma,depparse`",
        default="tokenize,mwt,pos,lemma,depparse",
    )
    parser.add_argument(
        "-c",
        "--conll",
        action="store_true",
        help="Run the pipeline and output .conllu files",
    )
    parser.add_argument(
        "-s", "--ske", action="store_true", help="Language code for Stanza, e.g. `en`"
    )
    parser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="Compare source files with output files",
    )
    parser.add_argument(
        "-V", "--verbose", action="store_true", help="Verbose logging (`logging.INFO`)"
    )
    parser.add_argument("lang", help="Language code for Stanza, e.g. `en`")
    parser.add_argument("file", nargs="+", help="Text file(s) to process")
    args = parser.parse_args()

    if args.verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(format="%(asctime)s %(message)s", level=level)

    for file in args.file:
        file = Path(file)
        nlp = NLP(file, args.lang, args.nlp, args.batch)

        if args.conll:
            nlp.to_conll()
        if args.ske:
            conll_to_vert(file.with_suffix(".conllu"))
        if args.verify:
            nlp.verify()
