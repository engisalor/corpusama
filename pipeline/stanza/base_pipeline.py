"""A pipeline to process texts with Stanza and output a SkE-conll format.

`SkE-conll` here refers to a format used by Sketch Engine based on conll. Primary
differences include reshaping `# key = value` comments into XML attributes; collapsing
multiword-terms (e.g., `del` in Spanish) from multiple lines in conll to one in SkE).

On SkE's SkE-conll format, see:
    https://www.sketchengine.eu/documentation/building-sketches-from-parsed-corpora

On CONLL-U format, see:
    https://universaldependencies.org/format.html
"""

import re
from pathlib import Path
from time import perf_counter

import stanza
from defusedxml.ElementTree import fromstring
from stanza.utils.conll import CoNLL

processors = "tokenize,mwt,pos,lemma,depparse"
language = "es"
chunksize = 1  # MB
nlp = stanza.Pipeline(language, processors=processors, download_method=None)


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

    def to_conll_inner(self) -> None:
        self.xml_headers = [x[0] for x in self.docs]
        self.docs = nlp.bulk_process([x[1] for x in self.docs])
        for x in range(len(self.docs)):
            self.docs[x].xml_header = self.xml_headers[x]
            self.docs[x].xml_footer = "</doc>\n"
        self.dest.unlink(missing_ok=True)
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
        self.batch_current += 1
        if self.max_batches and self.batch_current <= self.max_batches:
            return True
        else:
            return False

    def to_conll(self) -> None:
        while True:
            with open(self.source) as f:
                for i, line in enumerate(f):
                    if line.startswith('<doc id="'):
                        self.meta = line
                        self.doc = ""
                    elif line.startswith("</doc>"):
                        self.docs.append((self.meta, self.doc))
                        if (
                            sum([len(doc[1].encode()) for doc in self.docs])
                            >= self.chunksize
                        ):
                            return self.to_conll_inner()
                    else:
                        self.doc += line
                if self.docs:
                    return self.to_conll_inner()

    def __init__(
        self, file: str, chunksize: float = chunksize, max_batches: int = 0
    ) -> None:
        self.file = file
        self.chunksize = chunksize
        self.max_batches = max_batches
        self.source = Path(self.file)
        self.dest = self.source.with_suffix(".conllu")
        self.docs = []
        self.doc = ""
        self.meta = ""
        self.chunksize = (1024**2) * self.chunksize
        self.batch_current = 1
        self.t0 = perf_counter()
        self.to_conll()
        self.t1 = perf_counter()
        print(f"{self.t1-self.t0:.2f} secs")
