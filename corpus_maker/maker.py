import io
import json
import logging
import math
import pathlib
import re
import sqlite3 as sql
import tarfile
import time

import pandas as pd
import stanza
import yaml

logger = logging.getLogger(__name__)
log_file = ".corpus-maker.log"


class Maker:
    """A class for managing corpus generation from an SQL database of data."""

    def import_db(self):
        """Opens a SQL connection and reads records into the self.df dataframe."""

        self.conn = sql.connect(self.db_name)
        self.c = self.conn.cursor()
        self.df = pd.read_sql("SELECT * FROM records", self.conn)
        logger.debug(f"{self.db_name}")

    def close_db(self):
        """Closes a SQL connection."""

        self.c.close()
        self.conn.close()
        logger.debug(f"{self.db_name}")

    def _filename(self, row):
        "Generates a filename for a record."

        return "".join([row["id"], ".vert"])

    def _stanza(self):
        """Runs stanza on batches of df rows and outputs self.batch."""

        t0 = time.perf_counter()
        # get dataframe slice
        self.batch = self.df.iloc[
            self.index_start : self.index_start + self.batch_size
        ].copy()
        self.batch["body"].fillna("", inplace=True)
        # make Document objects
        in_docs = [stanza.Document([], text=d) for d in self.batch["body"].values]
        # run nlp
        self.batch["stanza"] = self.nlp(in_docs)
        # convert empty str back to None
        self.batch["body"].replace("", None, inplace=True)
        # job details
        t1 = time.perf_counter()
        n_words = sum([doc.num_words for doc in self.batch["stanza"].values])
        self.words_total += n_words
        n_seconds = t1 - t0
        words_second = int(n_words / n_seconds)
        logger.debug(
            "".join(
                [
                    f"{n_seconds:0.0f}s - ",
                    f"{n_words:,} words - ",
                    f"{words_second:,}/s - ",
                    f"batch [{self.index_start}:{self.index_start + self.batch_size}]",
                ]
            )
        )

    def _vert_row(self, row):
        """Makes vertical formatted text for a row."""

        if not isinstance(row["body"], str):
            return None
        else:
            # make vert lines
            items = []
            for sent in row["stanza"].sentences:
                # set sentence id
                self.sentence_id += 1
                sentence = [f"<s id={self.sentence_id}>\n"]
                # warn if missing lemmas
                for word in sent.words:
                    if word.lemma is None:
                        logger.warning(f"{row['id']} lemmatize fail: {word.text}")
                # make vert lines
                words = [
                    "".join(
                        [
                            word.text,
                            "\t",
                            word.xpos,
                            "\t",
                            fix_lemma(word),
                            self.tagset[word.xpos]["lpos"],
                            "\n",
                        ]
                    )
                    for word in sent.words
                ]
                sentence.extend(words)
                sentence.append("</s>\n")
                items.extend(sentence)
            # make vert document
            doc_start = f'<doc id="{row["id"]}" filename="{row["filename"]}">\n'
            doc_content = "".join(items)
            doc_stop = "</doc>\n"
            return "".join([doc_start, doc_content, doc_stop])

    def _vert(self):
        """Makes vertical formatted text for self.batch."""

        self.batch["vert"] = self.batch.apply(self._vert_row, axis=1)

    def _export(self, archive_name=None):
        """Exports vertical text to a tar archive."""

        # make archive name
        if not archive_name:
            archive_name = pathlib.Path(self.db_name)
        else:
            archive_name = pathlib.Path(archive_name)
        self.archive_name = archive_name.with_suffix(".tar")

        # write data
        with tarfile.open(self.archive_name, "a") as tar:
            self._tar(tar)

    def _tar(self, tar):
        """Handles file insertion into a tar archive - skips existing/None."""

        existing = tar.getmembers()
        existing_names = [x.name for x in existing]

        for x in range(len(self.batch)):
            if self.batch.iloc[x]["vert"] is None:
                logger.warning(f'{self.batch.iloc[x]["id"]} skip (no content)')
            else:
                info = tarfile.TarInfo(name=self.batch.iloc[x]["filename"])
                if info.name in existing_names:
                    logger.warning(f'{self.batch.iloc[x]["id"]} skip (file exists)')
                else:
                    text_bytes = io.BytesIO(bytes(self.batch.iloc[x]["vert"].encode()))
                    info.size = len(text_bytes.getbuffer())
                    tar.addfile(tarinfo=info, fileobj=text_bytes)

    def make_corpus(self, index_start=0, batch_size=100):
        """Makes vertical files from self.df and appends to <db.name>.tar."""

        t0 = time.perf_counter()
        self.words_total = 0
        self.batch_size = batch_size
        if len(self.df) < self.batch_size:
            self.batch_size = len(self.df)
        self.index_start = index_start - self.batch_size
        batches = math.floor(len(self.df) / self.batch_size)

        for x in range(batches):
            self.index_start += self.batch_size
            self._stanza()
            self._vert()
            self._export()
            logger.debug(f"{self.archive_name} appended")

        t1 = time.perf_counter()
        n_seconds = t1 - t0
        words_second = int(self.words_total / n_seconds)
        logger.debug(
            "".join(
                [
                    f"{n_seconds/60:0.0f}m - ",
                    f"{self.words_total:,} words - ",
                    f"{words_second*60:,}/m",
                ]
            )
        )

    def _update_model(self):
        """Sets whether to look for stanza model updates based on logs."""

        self.nlp_runs = 0
        if pathlib.Path(self.log_file).exists():
            with open(pathlib.Path(self.log_file), "r") as f:
                daily_log = f.readlines()
            for x in daily_log:
                if "nlp ready" in x:
                    self.nlp_runs += 1
        if self.nlp_runs > 0:
            self.download_method = None
        else:
            self.download_method = True
        logger.debug(f"{self.download_method}")

    def _make_doc_tag(
        self,
        row,
        drops=[
            "disaster__type",
            "file",
            "headline",
            "image",
            "origin",
            "source__homepage",
            "url",
        ],
    ):
        """Creates a <doc> tag with associated attributes, except for dropped columns.

        (Automatically adds body, body_html and stanza columns to drops.)"""

        # convert df row to dict
        if not drops:
            drops = []
        drops.extend(["stanza", "body", "body_html"])
        row = {k: v for k, v in row.items() if not k.startswith(tuple(drops))}
        # order doc id first
        doc_tag = [f'<doc id="{row["id"]}" ']
        del row["id"]
        # add other attribute tags and store attrs
        self.attrs = set()
        for k, v in row.items():
            doc_tag.append(f"{k}={json.dumps(str(v),ensure_ascii=False)} ")
            self.attrs.update([k])
        doc_tag.append(">\n")
        return "".join(doc_tag)

    def _save_attributes(self):
        """Saves corpus doc attributes in self.attrs to a config file.

        Assumes all attributes are indexes with "|" for MULTISEP."""

        attrs_str = []
        for attr in sorted(self.attrs):
            item = "".join(
                [
                    '\tATTRIBUTE "' + attr + '" {\n',
                    '\t\tDYNTYPE "index"\n',
                    '\t\tMULTISEP "|"\n',
                    '\t\tMULTIVALUE "y"\n\t}\n',
                ]
            )
            attrs_str.append(item)

        file = f"data/{pathlib.Path(self.db_name).stem}_attributes.txt"
        with open(file, "w") as f:
            f.write("".join(attrs_str))
        logger.debug(f"{file}")

    def __init__(
        self,
        db,
        resources="data/local-only/stanza_resources",
        processors="tokenize,mwt,pos,lemma",
        tagset="corpus_maker/tagset.yml",
        log_level="debug",
    ):
        # variables
        self.sentence_id = 0
        self.log_file = log_file
        self.db_name = db

        # logging
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError("Invalid log level: %s" % log_level)
        logger.setLevel(numeric_level)

        # instantiate
        self._update_model()
        self.nlp = stanza.Pipeline(
            "en",
            resources,
            processors=processors,
            download_method=self.download_method,
        )
        logger.debug("nlp ready")
        self.import_db()
        self.df["filename"] = self.df.apply(self._filename, axis=1)
        self.tagset = load_tagset(tagset)


def load_tagset(file) -> dict:
    """Loads a tagset YML file containing a dict of dicts of xpos tags."""

    with open(file, "r") as stream:
        tagset = yaml.safe_load(stream)
    return tagset


def get_xpos(doc) -> list:
    """Returns a list of unique xpos strings from a stanza document."""

    xpos = set([word.xpos for sent in doc.sentences for word in sent.words])
    return sorted(xpos)


def fix_lemma(word):
    """Replaces lemmas containing digits with [number] for lempos values.

    Also manages bad lemma values: defaults to word.text if no word.lemma.

    Examples:
    - 35	CD	[number]-m # instead of 35-m
    - ii	CD	ii-m
    - five	CD	five-m"""

    # fix missing lemma
    if word.lemma is None:
        word.lemma = word.text
    # change lpos for numbers
    if word.xpos == "CD" and bool(re.search(r"\d", word.lemma)):
        return "[number]"
    else:
        return word.lemma
