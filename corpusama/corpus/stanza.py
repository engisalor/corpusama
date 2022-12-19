"""Methods to execute stanza pipelines and process results."""
import logging
import re

from stanza import Document, Pipeline

from corpusama import log_file
from corpusama.util import convert, util
from corpusama.util.dataclass import DocBundle

logger = logging.getLogger(__name__)


def load_nlp(resources, processors, language) -> Pipeline:
    """Returns a stanza ``Pipeline`` object, updating models once a day.

    Args:
        resources: Stanza resources.
        processors: Stanza processors.
        language: Current language.

    Notes:
        - Uses ``util.count_log_lines`` to check if the model has been updated.
        - Keep in mind that as stanza models are updated, segmentation,
            lemmatization, etc., may differ over time.

    See Also:
        https://stanfordnlp.github.io/stanza/"""

    nlp_runs = util.count_log_lines("load_nlp", log_file)
    if nlp_runs > 0:
        nlp = Pipeline(language, resources, processors=processors, download_method=None)
    else:
        nlp = Pipeline(language, resources, processors=processors)
    logger.debug("done")
    return nlp


def get_xpos(processed: list) -> list:
    """Returns a list of unique xpos strings from a list of processed documents."""

    xpos = set()
    for doc in processed:
        xpos.update([word.xpos for sent in doc.sentences for word in sent.words])
    return sorted(xpos)


def fix_lemma(word):
    """Replaces lemmas containing digits with ``[number]`` for lempos values.

    Args:
        word: A stanza ``Word`` object.

    Notes:
        Also manages bad lemma values: defaults to ``word.text`` if no ``word.lemma``.

    Examples:
        - ``35	CD	[number]-m`` instead of ``35	CD	35-m``
        - ``ii	CD	ii-m`` no change for Roman numerals
        - ``five	CD	five-m``  no change for words"""

    # fix missing lemma
    if word.lemma is None:
        word.lemma = word.text
    # change lpos for numbers
    if word.xpos == "CD" and bool(re.search(r"\d", word.lemma)):
        return "[number]"
    else:
        return word.lemma


def run(
    docs: list, ids: list, pipeline: Pipeline, parse_html: bool = True
) -> DocBundle:
    """Runs stanza on a list of strings and returns a ``DocBundle`` object.

    Args:
        docs: A list of strings to process.
        ids: A list of unique IDs corresponding to ``docs``.
        pipeline: A stanza ``Pipeline``.
        parse_html: Whether to run docs through an XML parser.

    See also:
        - ``util.dataclass.DocBundle``
        - ``util.convert.html_to_text``"""

    if parse_html:
        docs = [convert.html_to_text(x) for x in docs]
    docs = [Document([], text=d) for d in docs]
    processed = pipeline(docs)
    tokens = sum([doc.num_words for doc in docs])
    xpos = get_xpos(processed)
    return DocBundle(processed, ids, tokens, xpos)
