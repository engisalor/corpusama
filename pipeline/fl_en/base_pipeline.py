#! /usr/bin/python3
import io
import re
import sys

import pyfreeling as freeling

DATA = ".local-only/share/freeling/"
LANG = "en"
SENTENCE_BREAKER_RE = re.compile(
    r"</?(doc|p|align|s)(\s+[^\W\d][\w:\.-]*\s*=\s*('[^']*'|\"[^\"]*\"))*\s*/?\s*>",
    re.UNICODE,
)
TAG_RE = re.compile(
    r"<!--.*?-->|<[!?/]?[^\W\d][\w:\.-]*(\s+[^\W\d][\w:\.-]*\s*=\s*('[^']*'|\"[^\"]*\"))*\s*/?\s*>",  # noqa: E501
    re.UNICODE,
)
POS_MAPPING = {
    "Z": "m",
    "JJ": "j",
    "JJR": "j",
    "JJS": "j",
    "RB": "a",
    "RBR": "a",
    "RBS": "a",
    "CC": "c",
    "NNS": "n",
    "NN": "n",
    "NNP": "n",
    "NP00000": "n",
    "NP": "n",
    "NP00G00": "n",
    "NP00O00": "n",
    "NP00V00": "n",
    "NP00SP0": "n",
    "NPS": "n",
    "NNPS": "n",
    "IN": "i",
    "VBG": "v",
    "VB": "v",
    "VBN": "v",
    "VBD": "v",
    "VBP": "v",
    "VBZ": "v",
    "PRP": "d",
    "PRP$": "d",
}

freeling.util.init_locale("en_US.utf8")
splitter = freeling.splitter("pipeline/fl_en/splitter.dat")
tokenizer = freeling.tokenizer("pipeline/fl_en/tokenizer.dat")
op = freeling.analyzer_config()
op.config_opt.Lang = LANG
op.config_opt.MACO_PunctuationFile = DATA + "common/punct.dat"
op.config_opt.MACO_DictionaryFile = DATA + LANG + "/dicc.src"
op.config_opt.MACO_AffixFile = DATA + LANG + "/afixos.dat"
op.config_opt.MACO_CompoundFile = DATA + LANG + "/compounds.dat"
op.config_opt.MACO_LocutionsFile = DATA + LANG + "/locucions.dat"
op.config_opt.MACO_NPDataFile = "pipeline/fl_en/np.dat"
op.config_opt.MACO_QuantitiesFile = DATA + LANG + "/quantities.dat"
op.config_opt.MACO_ProbabilityFile = DATA + LANG + "/probabilitats.dat"
op.invoke_opt.MACO_AffixAnalysis = True
op.invoke_opt.MACO_CompoundAnalysis = False
op.invoke_opt.MACO_MultiwordsDetection = False
op.invoke_opt.MACO_NumbersDetection = True
op.invoke_opt.MACO_PunctuationDetection = True
op.invoke_opt.MACO_DatesDetection = False
op.invoke_opt.MACO_QuantitiesDetection = False
op.invoke_opt.MACO_DictionarySearch = True
op.invoke_opt.MACO_ProbabilityAssignment = True
op.invoke_opt.MACO_NERecognition = False
op.invoke_opt.MACO_RetokContractions = True
morpho = freeling.maco(op)
op.config_opt.TAGGER_HMMFile = DATA + LANG + "/tagger.dat"
op.invoke_opt.TAGGER_Retokenize = True
op.invoke_opt.TAGGER_ForceSelect = 2
tagger = freeling.hmm_tagger(op)


def analyze(plaintext, flush=False):
    global session, xmltags, current_xmltags
    xmltags_and_tokens = tokenizer.tokenize(plaintext)
    tokens = []
    for tag_or_token in xmltags_and_tokens:
        form = tag_or_token.get_form()
        if TAG_RE.match(form):
            current_xmltags.append(form)
        else:
            xmltags.append(current_xmltags)
            current_xmltags = []
            tokens.append(tag_or_token)
    sentences = splitter.split(session, tokens, flush)
    for sentence in sentences:
        sentence = morpho.analyze_sentence(sentence)
        if print_sent:
            sys.stdout.write("<s>\n")
        last_finish = -1
        initial = True
        for token in tagger.analyze_sentence(sentence).get_words():
            start = token.get_span_start()
            if start and start <= last_finish:
                sys.stdout.write("<g/>\n")
            print_token(token, initial)
            last_finish = token.get_span_finish()
            initial = False
        if print_sent:
            sys.stdout.write("</s>\n")
    if flush:
        for xmltag in current_xmltags:
            sys.stdout.write("%s\n" % xmltag)
        current_xmltags = []


def print_token(token, initial):
    # normal attributes
    word = token.get_form()
    tag = token.get_tag()
    lemma = token.get_lemma().lower()
    # simple proper noun detection
    if word[0].isupper():
        if initial and token.get_analyzed_by() & freeling.word.GUESSER:
            tag = "NP" + tag[2:] if tag.startswith("N") else "NP00000"
            lemma = word
        elif not initial and tag.startswith("N"):
            tag = "NP" + tag[2:]
            lemma = word
        elif not initial and not token.get_analyzed_by() & freeling.word.DICTIONARY:
            tag = "NP00000"
            lemma = word
    pos = POS_MAPPING.get(tag, "x")
    # print out
    sys.stdout.write(f"{word}\t{tag}\t{lemma}-{pos}\n")


if "-s" in sys.argv:
    print_sent = False
else:
    print_sent = True

session = splitter.open_session()
xmltags = []
current_xmltags = []
for line in io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace"):
    if SENTENCE_BREAKER_RE.search(line):
        pos = 0
        for mo in SENTENCE_BREAKER_RE.finditer(line):
            startpos, endpos = mo.span()
            beforetag = line[pos:startpos]
            analyze(beforetag, flush=True)
            tag = line[startpos:endpos]
            sys.stdout.write(tag + "\n")
            pos = endpos
        aftertag = line[pos:]
        analyze(aftertag)
    elif not line.strip():
        analyze("", flush=True)
    else:
        analyze(line)
analyze("", flush=True)
splitter.close_session(session)
