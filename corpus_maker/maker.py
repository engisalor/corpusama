import io
import logging
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

    def stanza_df(self):
        """Runs stanza on self.df["body"] and outputs a new column."""

        t0 = time.perf_counter()
        # replace None w/ empty string
        self.df["body"].fillna("", inplace=True)
        # make Document objects
        in_docs = [stanza.Document([], text=d) for d in self.df["body"].values]
        # run nlp
        self.df["stanza"] = self.nlp(in_docs)
        t1 = time.perf_counter()
        # convert empty str back to None
        self.df["body"].replace("", None, inplace=True)
        # job details
        n_words = sum([doc.num_words for doc in self.df["stanza"].values])
        n_seconds = t1 - t0
        words_second = int(n_words / n_seconds)
        logger.debug(f"{n_seconds:0.2f}s - {n_words:,} words - {words_second:,}/s")

    def _vert_row(self, row):
        """Makes vertical formatted text for a df row."""

        if not isinstance(row["body"], str):
            return None
        else:
            # make vert lines
            items = []
            for sent in row["stanza"].sentences:
                self.sentence_id += 1
                sentence = [f"<s id={self.sentence_id}>\n"]
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

    def vert_df(self):
        """Makes vertical formatted text for rows in self.df."""

        self.df["vert"] = self.df.apply(self._vert_row, axis=1)

    def vert_export(self, archive_name=None):
        """Exports df["vert"] to a tar archive with one file per row."""

        # make archive name
        if not archive_name:
            archive_name = pathlib.Path(self.db_name)
        else:
            archive_name = pathlib.Path(archive_name)
        archive_name = archive_name.with_suffix(".tar")

        # write data
        with tarfile.open(archive_name, "a") as tar:
            self._vert_tar(tar)
        logger.debug(f"{archive_name}")

    def _vert_tar(self, tar):
        """Handles file insertion into a tar archive - skips existing/None."""

        existing = tar.getmembers()
        existing_names = [x.name for x in existing]

        for x in range(len(self.df)):
            if self.df.iloc[x]["vert"] is None:
                logger.warning(f'{self.df.iloc[x]["id"]} skipped (no content)')
            else:
                info = tarfile.TarInfo(name=self.df.iloc[x]["filename"])
                if info.name in existing_names:
                    logger.warning(f'{self.df.iloc[x]["id"]} skipped (exists)')
                else:
                    text_bytes = io.BytesIO(bytes(self.df.iloc[x]["vert"].encode()))
                    info.size = len(text_bytes.getbuffer())
                    tar.addfile(tarinfo=info, fileobj=text_bytes)

    def make_corpus(self):
        """Makes a corpus from self.df["body"] content and exports to an archive."""

        self.stanza_df()
        self.vert_df()
        self.vert_export()

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
