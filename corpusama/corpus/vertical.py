"""Methods to create and manipulate vertical formatted text."""
import logging

import pandas as pd

from corpusama.corpus import stanza as _stanza
from corpusama.util import convert, decorator, util
from corpusama.util.dataclass import DocBundle

logger = logging.getLogger(__name__)


def stanza_to_vert(bundle: DocBundle, tagset: dict) -> DocBundle:
    """Replaces a bundle of stanza documents with vertical content.

    Args:
        bundle: A ``DocBundle`` to process.
        tagset: Rules defining how to create lempos tags from xpos values."""

    def lemmatize_fail(sent, x: int) -> None:
        """Logs a warning when lemmatization fails."""

        for w in sent.words:
            if w.lemma is None:
                logger.warning(f"{bundle.id[x]}: {w.text}")

    def make_lines(sent) -> list:
        """Makes a list of vertical lines for a sentence."""

        return [
            f'{w.text}\t{w.xpos}\t{_stanza.fix_lemma(w)}{tagset[w.xpos]["lpos"]}\n'
            for w in sent.words
        ]

    def make_sentence(sent, x: int) -> list:
        """Makes a list of vertical-formatted sentence segments."""

        sentence = ["<s>\n"]
        lemmatize_fail(sent, x)
        lines = make_lines(sent)
        sentence.extend(lines)
        sentence.append("</s>\n")
        return "".join(sentence)

    def make_docs(bundle: DocBundle) -> DocBundle:
        """Overwrites bundle documents with their vertical equivalent."""

        for x in range(bundle.len):
            _list = [make_sentence(sent, x) for sent in bundle.doc[x].sentences]
            bundle.doc[x] = "".join(_list)
        return bundle

    return make_docs(bundle)


def make_vertical(
    self, language: str, size: int = 1000, runs: int = 0, update: bool = True
) -> None:
    """Processes raw data and inserts vertical files into the ``_vert`` table.

    Args:
        self: A ``Corpus`` object.
        language: The ``stanza.Pipeline`` language.
        size: Number of documents to process at a time (larger batches
            can improve overall performance).
        runs: The maximum number of batches to run (for testing).
        update: Whether to update newly modified records.

    See also:
        - ``outdated_vert``"""

    @decorator.while_loop
    def batch(self, update) -> bool:
        """Manages creation of vertical content in batches."""

        # get batch
        query = """SELECT * FROM _raw
        WHERE body_html IS NOT null
        LIMIT ?,?;"""
        batch, offset = self.db.fetch_batch(self.vert_run, self.vert_size, query)
        if not batch:
            return False
        # skip records
        exists = self.db.c.execute("SELECT id FROM _vert").fetchall()
        exists = [x[0] for x in exists]
        if update:
            changed = outdated_vert(self)
            exists = [x for x in exists if x not in changed]
            logger.debug(f"existing vert content to update: {changed}")
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
        """Runs stanza, converts to vertical, and inserts records.

        Returns:
            The number of tokens processed."""

        stan = _stanza.run(batch[self.text_column].values, batch["id"].values, self.nlp)
        vert = stanza_to_vert(stan, self.tagset)
        df = convert.docbundle_to_df(vert)
        df = drop_empty_vert(df)
        self.db.insert(df, "_vert")
        return vert.token

    self.nlp = _stanza.load_nlp(self.resources, self.processors, language)
    self.vert_size = size
    self.vert_run = 0
    self.vert_runs = runs
    batch(self, update)


def drop_empty_vert(df: pd.DataFrame) -> pd.DataFrame:
    """Drops DataFrame rows without vertical content.

    Args:
        df: A DataFrame to insert into the ``_vert`` table.

    Note:
        Null content should already be filtered out earlier in data processing,
        but empty strings can still occur, e.g., when XML content only contains
        images or other non-text."""

    drops = df.query("vert.str.len() == 0")
    if not drops.empty:
        logger.warning(f'{drops["id"].values}')
    return df.query("vert.str.len() > 0")


def outdated_vert(self) -> list:
    """Returns a list of out-of-date vertical files.

    Args:
        self: A ``Corpus`` object.

    Note:
        Compares ``vert_date`` values with ``date_changed`` values."""

    query = """SELECT _vert.id, json_extract(_raw.date,'$.changed'), vert_date
        FROM _vert LEFT JOIN _raw ON _vert.id = _raw.id"""
    df = pd.read_sql(query, self.db.conn)
    df.columns = ["id", "date_changed", "vert_date"]
    for col in ["date_changed", "vert_date"]:
        df[col] = df[col].apply(pd.Timestamp)
    df = df.query("date_changed > vert_date")
    changed = df["id"].tolist()
    return changed
