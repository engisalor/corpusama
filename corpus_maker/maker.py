import io
import json
import logging
import math
import pathlib
import re
import sqlite3 as sql
import tarfile
import time

import numpy as np
import pandas as pd
import stanza
import yaml

from corpus_maker import utils

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

        return f'{row["id"]}.vert'

    def _stanza(self):
        """Runs stanza on batches of df rows and outputs self.batch."""

        t0 = time.perf_counter()
        # run nlp
        docs = [stanza.Document([], text=d) for d in self.batch[self.text_row].values]
        self.batch["stanza"] = self.nlp(docs)
        # logging
        t1 = time.perf_counter()
        n_words = sum([doc.num_words for doc in self.batch["stanza"].values])
        self.words += n_words
        n_seconds = t1 - t0
        words_s = int(n_words / n_seconds)
        logger.debug(
            " ".join(
                [
                    f"{n_seconds:0.0f}s - {n_words:,} words - {words_s:,}/s -",
                    f"batch [{self.index_start}:{self.index_start + self.batch_size}]",
                ]
            )
        )

    def to_vertical(self, row):
        """Makes vertical formatted text from a df row/dict."""

        row = dict(row)
        if not isinstance(row[self.text_row], str):
            return None
        else:
            # make vert lines
            items = []
            for sent in row["stanza"].sentences:
                # set sentence id
                self.sentence_id += 1
                sentence = [f"<s id={self.sentence_id}>\n"]
                # warn if missing lemmas
                for w in sent.words:
                    if w.lemma is None:
                        logger.warning(f"{row['id']} lemmatize fail: {w.text}")
                # make vert lines
                words = [
                    f'{w.text}\t{w.xpos}\t{fix_lemma(w)}{self.tagset[w.xpos]["lpos"]}\n'
                    for w in sent.words
                ]
                sentence.extend(words)
                sentence.append("</s>\n")
                items.extend(sentence)

            # make vert document
            doc_tag = self._doc_tag(row)
            doc_content = "".join(items)
            doc_stop = "</doc>\n"
            return "".join([doc_tag, doc_content, doc_stop])

    def _tar(self, tar):
        """Handles file insertion into an archive (appends or overwrites existing)."""

        now = pd.Timestamp.now(tz="UTC").timestamp()
        for x in range(len(self.batch)):
            if self.batch.iloc[x]["vert"] is None:
                logger.warning(f'{self.batch.iloc[x]["id"]} skip (no content)')
            else:
                info = tarfile.TarInfo(name=self.batch.iloc[x]["filename"])
                text_bytes = io.BytesIO(bytes(self.batch.iloc[x]["vert"].encode()))
                info.size = len(text_bytes.getbuffer())
                info.mtime = now
                tar.addfile(tarinfo=info, fileobj=text_bytes)

    def make_corpus(
        self,
        text_row="body_html",
        drops=None,
        index_start=0,
        batch_size=100,
    ):
        """Makes vertical files from self.df and appends to data/<db.name>.tar.

        Overwrites previous tar archive.

        Options
        - text_row, str, the row containing text to be converted to vertical
        - drops, str or [str], user-defined columns to exclude from text attributes
        - index_start, int, the starting row for processing data
        - batch_size, int, the max number of rows processed at once"""

        t0 = time.perf_counter()
        self.attrs = set()
        self.text_row = text_row
        if not drops:
            drops = []
        elif isinstance(drops, str):
            drops = [drops]
        self.drops = set(drops + ["stanza", "body", "body_html"])
        self.words = 0
        self.batch_size = batch_size
        if len(self.df) < self.batch_size:
            self.batch_size = len(self.df)
        self.index_start = index_start - self.batch_size
        batches = math.floor(len(self.df) / self.batch_size)
        # process batches
        for x in range(batches):
            self._process_batch()
        # compress tar and save attrs config file
        utils.compress_tar(self.archive_name)
        self._save_attributes()
        # logging
        t1 = time.perf_counter()
        n_seconds = t1 - t0
        words_s = int(self.words / n_seconds)
        m0 = f"{n_seconds/60:0.0f}m - {self.words:,} words - {words_s*60:,}/m"
        m1 = f"- {self.archive_name} - drops - {self.drops}"
        logger.debug(" ".join([m0, m1]))

    def _process_batch(self):
        self.index_start += self.batch_size
        # get df slice and prepare
        self.batch = self.df.iloc[
            self.index_start : self.index_start + self.batch_size
        ].copy()
        self.batch = utils.flatten_df(self.batch)
        self.batch = utils.prepare_df(self.batch)
        # process texts
        self.batch[self.text_row] = self.batch[self.text_row].apply(utils.html_to_text)
        self._stanza()
        self.batch["vert"] = self.batch.apply(self.to_vertical, axis=1)
        with tarfile.open(self.archive_name, "a") as tar:
            self._tar(tar)

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

    def _doc_tag(self, row):
        """Creates a <doc> tag with attributes in df, except for dropped columns."""

        # convert df row to dict
        row = {k: v for k, v in row.items() if not k.startswith(tuple(self.drops))}
        # order doc id first
        doc_tag = [f'<doc id="{row["id"]}" ']
        del row["id"]
        # add other attribute tags and store attrs
        for k, v in row.items():
            if not isinstance(v, type(np.nan)) and not str(v).strip() == "":
                doc_tag.append(f"{k}={json.dumps(str(v),ensure_ascii=False)} ")
                self.attrs.update([k])
        doc_tag.append(">\n")
        return "".join(doc_tag)

    def _save_attributes(self):
        """Saves corpus doc attributes to a config file.

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
        processors="tokenize,pos,lemma",
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
