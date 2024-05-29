"""A pipeline to process texts with Stanza and output a SkE-conll format.

`SkE-conll` here refers to a format used by Sketch Engine based on conll. Primary
differences include reshaping `# key = value` comments into XML attributes; collapsing
multiword-terms (e.g., `del` in Spanish) from multiple lines in conll to one in SkE).

On SkE's SkE-conll format, see:
    https://www.sketchengine.eu/documentation/building-sketches-from-parsed-corpora

On CONLL-U format, see:
    https://universaldependencies.org/format.html
"""

import datetime
import logging

# import os
# import tracemalloc
import math
import re
from pathlib import Path
from time import perf_counter

import stanza
from defusedxml.ElementTree import fromstring
from stanza import DownloadMethod
from stanza.utils.conll import CoNLL


def convert_size(size_bytes) -> tuple:
    """See https://stackoverflow.com/questions/5194057/"""
    if size_bytes == 0:
        return (0, "B")
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return (s, size_name[i])


def vert_to_conll(file: str) -> None:
    """Converts a SkE-conll-formatted `.vert` file to .conll"""
    pass


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
                        d.write(re.sub(r"# sent_id = (\d+)", r'>\n<s id="\1">', line))
                        new_doc = False
                    else:
                        d.write(re.sub(r"# sent_id = (\d+)", r'\n<s id="\1">', line))
                elif line.startswith("# text"):
                    pass
                elif line.startswith("#"):
                    line = re.sub(r"# (\S+) = (.*)\n", r' \1="\2"', line)
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

    @staticmethod
    def calculate_rate(run, _bytes, t0):
        t1 = perf_counter()
        secs = t1 - t0
        _time = str(datetime.timedelta(seconds=secs, microseconds=0))
        # _size, _peak = tracemalloc.get_traced_memory()
        # tracemalloc.reset_peak()
        # tot_m, used_m, free_m = map(
        # int, os.popen('free -t -m').readlines()[-1].split()[1:])
        # _peak, _unit = convert_size(_peak)
        size, unit = convert_size(_bytes)
        msg = " - ".join(
            [
                f"run {run}",
                f"{_time}",
                f"{size:,.2f} {unit}",
                f"{size/secs:,.3f} {unit}/s",
                # f"{_peak:,.2f} {_unit} RAM",
                # f"{free_m:,.0f} MB free RAM",
            ]
        )
        logging.info(msg)

    def to_conll_inner(self) -> None:
        # tracemalloc.start()
        self.run_current += 1
        # if self.run_current % 4 == 0:
        #     logging.info(f"run {self.run_current} - reload stanza pipeline")
        #     self.nlp = stanza.Pipeline(
        #         self.language,
        #         processors=self.processors,
        #         download_method=self.download_method,
        #         logging_level='WARN')
        t0 = perf_counter()
        bytes_batch = sum([len(x[1].encode()) for x in self.docs])
        self.xml_headers = [x[0] for x in self.docs]
        self.docs = self.nlp.bulk_process([x[1] for x in self.docs])
        for x in range(len(self.docs)):
            self.docs[x].xml_header = self.xml_headers[x]
            self.docs[x].xml_footer = "</doc>\n"
        for doc in self.docs:
            xml = fromstring(doc.xml_header + doc.xml_footer)
            with open(self.dest, "a") as f:
                f.write(
                    "# newdoc\n"
                    + "\n".join([f"# {x[0]} = {x[1]}" for x in xml.items()])
                    + "\n"
                )
            CoNLL.write_doc2conll(doc, self.dest, "a")
        self.docs = []
        self.bytes_processed += bytes_batch
        self.calculate_rate(self.run_current, bytes_batch, t0)

    def to_conll(self) -> None:
        t0 = perf_counter()
        self.dest.unlink(missing_ok=True)
        with open(self.source) as f:
            for i, line in enumerate(f):
                if line.startswith('<doc id="'):
                    self.meta = line
                    self.doc = ""
                elif line.startswith("</doc>"):
                    self.docs.append((self.meta, self.doc))
                    _bytes = sum([len(doc[1].encode()) for doc in self.docs])
                    if _bytes >= self.chunksize:
                        self.to_conll_inner()
                else:
                    self.doc += line
            if self.docs:
                self.to_conll_inner()
        self.calculate_rate("TOTAL", self.bytes_processed, t0)

    def verify(self) -> None:
        def inner(file: Path) -> int:
            if not file.exists() or file.suffix not in [".txt", ".conllu"]:
                raise ValueError(f"{file.suffix} not implemented or no documents found")
            docs = 0
            with open(file) as f:
                for line in f:
                    if file.suffix in [".txt"] and line.startswith("<doc id="):
                        docs += 1
                    elif file.suffix in file.suffix in [".conllu"] and line.startswith(
                        "# newdoc"
                    ):
                        docs += 1
            msg = f"verify: {docs:,} docs in {file}"
            logging.info(msg)
            return docs

        source_docs = inner(self.source)
        dest_docs = inner(self.dest)

        msg = f"source & dest have unequal doc counts {source_docs} != {dest_docs}"
        if not source_docs == dest_docs:
            logging.warning(f"verify: {msg}")
        else:
            logging.info("verify: source & dest have same number of docs")

    def __init__(
        self,
        file: str,
        language: str,
        processors: str,
        chunksize: float = 1,
        download_method: DownloadMethod | None = None,
    ) -> None:
        self.file = file
        self.source = Path(self.file)
        self.dest = self.source.with_suffix(".conllu")
        self.docs = []
        self.doc = ""
        self.meta = ""
        self.chunksize = (1024**2) * chunksize
        self.run_current = 0
        self.bytes_processed = 0
        self.language = language
        self.processors = processors
        self.download_method = download_method
        self.nlp = stanza.Pipeline(
            language,
            processors=processors,
            download_method=download_method,
            logging_level="WARN",
        )
        # tot_m, used_m, free_m = map(
        #     int, os.popen('free -t -m').readlines()[-1].split()[1:])
        msg = " ".join(
            [
                f"{self.file} ({language}) -> Stanza (~{chunksize} MB chunks)",
                # f" -> CoNLL ({free_m:,.0f} MB free RAM)",
            ]
        )

        logging.info(msg)
        self.to_conll()
        self.verify()
