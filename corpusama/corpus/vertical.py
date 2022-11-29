"""Methods to create and manipulate vertical formatted text."""
import logging

import pandas as pd

from corpusama.corpus import stanza as _stanza
from corpusama.util import convert, decorator, util
from corpusama.util.dataclass import DocBundle

logger = logging.getLogger(__name__)


def stanza_to_vert(bundle: DocBundle, tagset) -> DocBundle:
    """Replaces a bundle of stanza documents with vertical content.

    - tagset, dict, defines how to create lempos tags"""

    def lemmatize_fail(sent, x) -> None:
        """Logs a warning when lemmatization fails."""

        for w in sent.words:
            if w.lemma is None:
                logger.warning(f"{bundle.id[x]}: {w.text}")

    def make_lines(sent):
        """Makes a list of vertical lines for a sentence."""

        return [
            f'{w.text}\t{w.xpos}\t{_stanza.fix_lemma(w)}{tagset[w.xpos]["lpos"]}\n'
            for w in sent.words
        ]

    def make_sentence(sent, x) -> list:
        "Makes a vertical sentence."

        sentence = ["<s>\n"]
        lemmatize_fail(sent, x)
        lines = make_lines(sent)
        sentence.extend(lines)
        sentence.append("</s>\n")
        return "".join(sentence)

    def make_docs(bundle: DocBundle) -> DocBundle:
        """Overwrites bundle documents with vertical equivalent."""

        for x in range(bundle.len):
            _list = [make_sentence(sent, x) for sent in bundle.doc[x].sentences]
            bundle.doc[x] = "".join(_list)
        return bundle

    return make_docs(bundle)


def make_vertical(self, size=10, runs=0):
    """Processes raw data and inserts vertical files into corpus.

    Destructive: replaces existing vertical content

    - size, int, documents to process at a time
    - runs, int, maximum batches to run"""

    @decorator.while_loop
    def batch(self):
        """Manages creation of vertical content in batches."""

        # FIXME debug and use 'AND NOT IN (SELECT id FROM _vert)'
        # instead of lines in # skip existing

        # get batch
        query = """SELECT * FROM _raw
        WHERE body_html IS NOT null
        LIMIT ?,?;"""
        batch, offset = self.db.fetch_batch(self.vert_run, self.vert_size, query)
        if not batch:
            return False
        # skip existing
        exists = self.db.c.execute("SELECT id FROM _vert").fetchall()
        exists = [x[0] for x in exists]
        batch = [x for x in batch if x[1] not in exists]
        if not batch:
            self.vert_run += 1
            return True
        # insert new
        cols = self.db.tables["_raw"]
        df = pd.DataFrame.from_records(batch, columns=cols)
        token, t = batch_run(self, df)
        self.vert_run += 1
        # limit runs or repeat
        repeat = util.limit_runs(self.vert_run, self.vert_runs)
        if not repeat:
            return False
        logger.debug(f"run  {self.vert_run:,} - {t:,}s - {int(token/t):,} tokens/s")
        return repeat

    @decorator.timer
    def batch_run(self, batch) -> int:
        """Runs stanza, converts to vertical, and inserts into database.

        Returns the number of tokens processed."""

        stan = _stanza.run(batch[self.text_column].values, batch["id"].values, self.nlp)
        vert = stanza_to_vert(stan, self.tagset)
        df = convert.docbundle_to_df(vert)
        self.db.insert(df, "_vert")
        return vert.token

    self.nlp = _stanza.load_nlp(self.resources, self.processors)
    self.vert_size = size
    self.vert_run = 0
    self.vert_runs = runs
    batch(self)
