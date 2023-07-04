#!/usr/bin/python3
# Keep a copy of pyfreeling.py and _pyfreeling.so in the same parent directory.
# FreeLing installation (update DATA = "<install_dir>" as needed):
# https://freeling-user-manual.readthedocs.io/en/latest/installation/installation-linux
# dicc.src file generated w/ "cat DATA + LANG + /dictionary/entries/* >> dicc.src"
# (manually add header/footer lines)
import io
import re
import sys

import pyfreeling as freeling

DATA = ".local-only/share/freeling/"
LANG = "fr"
SENTENCE_BREAKER_RE = re.compile(
    r"</?(doc|p|align|s)(\s+[^\W\d][\w:\.-]*\s*=\s*('[^']*'|\"[^\"]*\"))*\s*/?\s*>"
)
TAG_RE = re.compile(
    r"<!--.*?-->|<[!?/]?[^\W\d][\w:\.-]*(\s+[^\W\d][\w:\.-]*\s*=\s*('[^']*'|\"[^\"]*\"))*\s*/?\s*>"  # noqa: E501
)
POS_MAPPING = {
    "A": "j",
    "R": "r",
    "C": "c",
    "N": "n",
    "Z": "m",
    "S": "i",
    "P": "p",
    "V": "v",
}
GENDER_DICT_PATH = "pipeline/ske_fr/frtenten17_fl2_term_ref.gender_dict"

gender_dict = {}
for line in open(GENDER_DICT_PATH):
    lemma, tag, gender_lemma = line.rstrip().split("\t")
    try:
        gender_dict[lemma][tag] = gender_lemma
    except KeyError:
        gender_dict[lemma] = {tag: gender_lemma}


def get_gender_lemma(tag, lemma):
    if tag.startswith("N"):  # noun
        base_tag = tag[:3] + "S" + tag[4:]
    elif tag.startswith("A"):  # adjective
        base_tag = tag[:4] + "S" + tag[5:]
    elif tag.startswith("VMP"):  # participle
        base_tag = tag[:5] + "S" + tag[6:]
    elif tag.startswith("D"):  # determiner
        base_tag = tag[:4] + "S" + tag[5:]
    else:
        return lemma
    try:
        return gender_dict[lemma][base_tag]
    except KeyError:
        return lemma


freeling.util_init_locale("fr_FR.utf8")
splitter = freeling.splitter("pipeline/ske_fr/splitter.dat")
tokenizer = freeling.tokenizer("pipeline/ske_fr/tokenizer.dat")
op = freeling.analyzer_config()
op.config_opt.Lang = LANG
op.config_opt.MACO_PunctuationFile = DATA + "common/punct.dat"
op.config_opt.MACO_DictionaryFile = "pipeline/ske_fr/dicc.src"
op.config_opt.MACO_AffixFile = DATA + LANG + "/afixos.dat"
op.config_opt.MACO_CompoundFile = ""
op.config_opt.MACO_LocutionsFile = DATA + LANG + "/locucions.dat"
op.config_opt.MACO_NPDataFile = "pipeline/ske_fr/np.dat"
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
op.invoke_opt.MACO_RetokContractions = False
morpho = freeling.maco(op)
op.config_opt.TAGGER_HMMFile = DATA + LANG + "/tagger.dat"
op.invoke_opt.TAGGER_Retokenize = False
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
            for xmltag in xmltags.pop(0):
                sys.stdout.write(f"{xmltag}\n")
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
            sys.stdout.write(f"{xmltag}\n")
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
    pos = POS_MAPPING.get(tag[0], "x")
    gender_lemma = get_gender_lemma(tag, lemma).lower()
    # multivalue attributes
    tags = tag
    morphemes = lemma
    if token.has_retokenizable():
        subtokens = token.get_analysis()[0].get_retokenizable()
        if len(subtokens) > 0:
            tags = ",".join(st.get_tag() for st in subtokens)
            morphemes = ",".join(st.get_lemma().lower() for st in subtokens)
    # print out
    sys.stdout.write(
        f"{word}\t{tag}\t{lemma}-{pos}\t{gender_lemma}\t{tags}\t{morphemes}\n"
    )


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
