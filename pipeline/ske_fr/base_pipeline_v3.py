#!/usr/bin/python3
import io
import re
import sys

import freeling

DATA = "/usr/share/freeling/"
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
GENDER_DICT_PATH = "/opt/freeling_pipe/french/frtenten17_fl2_term_ref.gender_dict"

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
splitter = freeling.splitter("/opt/freeling_pipe/french/splitter.dat")
tokenizer = freeling.tokenizer("/opt/freeling_pipe/french/tokenizer.dat")
options = freeling.maco_options(LANG)
options.set_data_files(
    usr="",
    pun=DATA + "common/punct.dat",
    dic=DATA + LANG + "/dicc.src",
    aff=DATA + LANG + "/afixos.dat",
    comp="",
    loc="",
    nps="",
    qty="",
    prb=DATA + LANG + "/probabilitats.dat",
)
morpho = freeling.maco(options)
morpho.set_active_options(
    umap=False,
    num=True,
    pun=True,
    dat=False,
    dic=True,
    aff=True,
    comp=False,
    rtk=False,
    mw=False,
    ner=False,
    qt=False,
    prb=True,
)
tagger = freeling.hmm_tagger(DATA + LANG + "/tagger.dat", False, 2)


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
        sentence = morpho.analyze(sentence)
        if print_sent:
            sys.stdout.write("<s>\n")
        last_finish = -1
        initial = True
        for token in tagger.analyze(sentence).get_words():
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
