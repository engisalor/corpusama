"""Library dataclasses."""
import logging

from corpusama.util import util

logger = logging.getLogger(__name__)


class DocBundle:
    """A class for organizing text data during corpus preparation.

    Arguments:
        doc: List of documents to process.
        id: List of document ids.

    Attributes:
        date: The bundle creation date.
        token: The number of tokens counted in vertical content.
        xpos: Unique xpos values found in vertical content.

    Methods:
        check_len: Ensures that document and id list lengths are equal.

    Notes:
        The format of documents changes during corpus creation.
        Initially, DocBundles have sets of raw documents, which are
        replaced by stanza and vertical content as they are processed
        in other modules. ``token`` and ``xpos`` attributes are generated
        during this processing."""

    def check_len(self):
        if not len(self.doc) == len(self.id):
            m = f"Lengths for doc and id differ: {len(self.doc)} != {len(self.id)}"
            raise ValueError(m)

    def __repr__(self):
        return f"DocBundle: {str(self.__dict__)}"

    def __init__(self, doc: list, id: list, token=None, xpos=None):
        self.doc = doc
        self.id = id
        self.check_len()
        self.len = len(doc)
        self.token = token
        self.xpos = xpos
        self.date = util.now()
