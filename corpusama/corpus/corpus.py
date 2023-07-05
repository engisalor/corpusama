"""Stores the Corpus class, for executing operations on corpora."""
from corpusama.database.database import Database
from corpusama.util import io as _io


class Corpus:
    """Class to make and maintain a corpus of vertical files.

    Args:
        config: YAML configuration file.

    Notes:
        Combines methods from other modules needed preparing a corpus.
    """

    from corpusama.corpus.attribute import make_attribute
    from corpusama.corpus.export import export_text
    from corpusama.corpus.langid import make_langid

    def __init__(
        self,
        config: str,
    ):
        self.config = _io.load_yaml(config)
        self.changed = []
        self.db = Database(config)
        if self.config.get("source") == "reliefweb":
            from corpusama.source.reliefweb import ReliefWeb

            self.rw = ReliefWeb(config, self.db)
