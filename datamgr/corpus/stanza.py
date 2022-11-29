"""Methods to execute stanza pipelines and modify results."""
import logging
import re

from stanza import Document, Pipeline

from datamgr import log_file
from datamgr.util import convert, util
from datamgr.util.dataclass import DocBundle

logger = logging.getLogger(__name__)


def load_nlp(resources, processors):
    """Loads a stanza Processor object, updating models once a day."""

    nlp_runs = util.count_log_lines("load_nlp", log_file)
    if nlp_runs > 0:
        nlp = Pipeline("en", resources, processors=processors, download_method=None)
    else:
        nlp = Pipeline("en", resources, processors=processors)
    logger.debug("done")
    return nlp


def get_xpos(processed) -> list:
    """Returns a list of unique xpos strings from a list of processed documents."""

    xpos = set()
    for doc in processed:
        xpos.update([word.xpos for sent in doc.sentences for word in sent.words])
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


def run(docs: list, ids: list, pipeline: Pipeline, parse_html=True) -> DocBundle:
    """Runs stanza on [str] and returns a DocBundle object.

    - docs, list, documents
    - ids, list, unique identified for each doc
    - pipeline, stanza.Pipeline for running nlp
    - parse_html, bool, extract text from HTML content"""

    if parse_html:
        docs = [convert.html_to_text(x) for x in docs]
    docs = [Document([], text=d) for d in docs]
    processed = pipeline(docs)
    tokens = sum([doc.num_words for doc in docs])
    xpos = get_xpos(processed)
    return DocBundle(processed, ids, tokens, xpos)
