import io
import logging
import pathlib
import sqlite3 as sql
import tarfile

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

    def _vert(self, row):
        if isinstance(row["body"], str):
            doc = self.nlp(row["body"])
            # make lines w/ sentence tags
            vert = []
            for sent in doc.sentences:
                sentence = ["<s>\n"]
                words = [
                    f"{word.text}\t{word.xpos}\t{word.lemma}-{word.xpos[0].lower()}\n"
                    for word in sent.words
                ]
                sentence.extend(words)
                sentence.append("</s>\n")
                vert.extend(sentence)
            # make vert file
            doc_start = f'<doc id="{row["id"]}" filename="{row["filename"]}">\n'
            content = "".join(vert)
            doc_stop = "</doc>\n"
            text = "".join([doc_start, content, doc_stop])
            return text

    def export_vert(self, tarname: str = "data/he.tar.xz"):
        self.df["filename"] = self.df.apply(self._filename, axis=1)
        self.df["vert"] = self.df.apply(self._vert, axis=1)

        with tarfile.open(tarname, "w:xz") as tar:
            for x in range(len(self.df)):
                info = tarfile.TarInfo(name=self.df.iloc[x]["filename"])
                text_bytes = io.BytesIO(bytes(self.df.iloc[x]["vert"].encode()))
                info.size = len(text_bytes.getbuffer())
                tar.addfile(tarinfo=info, fileobj=text_bytes)

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
        db="data/reliefweb.db",
        resources="data/local-only/stanza_resources",
        processors="tokenize,mwt,pos,lemma",
        tagset="corpus_maker/tagset.yml",
        log_level="debug",
    ):
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
        self.tagset = load_tagset(tagset)


def load_tagset(file) -> dict:
    """Loads a tagset YML file containing a dict of dicts of xpos tags."""

    with open(file, "r") as stream:
        tagset = yaml.safe_load(stream)
    return tagset
