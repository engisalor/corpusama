import io
import logging
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

    def save_xpos(self, doc):
        xpos = set([word.xpos for sent in doc.sentences for word in sent.words])
        xpos = sorted(xpos)
        xpos = [x + "\n" for x in xpos]
        with open("xpos_stanza.txt", "w") as f:
            f.writelines(xpos)

    def __init__(
        self,
        db="data/reliefweb.db",
        resources="data/local-only/stanza_resources",
        processors="tokenize,mwt,pos,lemma",
        tagset="corpus_maker/tagset.yml",
    ):
        self.db_name = db
        self.nlp = stanza.Pipeline("en", resources, processors=processors)
        self.import_db()
        self.tagset = load_tagset(tagset)


def load_tagset(file) -> dict:
    """Loads a tagset YML file containing a dict of dicts of xpos tags."""

    with open(file, "r") as stream:
        tagset = yaml.safe_load(stream)
    return tagset
