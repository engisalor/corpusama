#!/usr/bin/python3

# by Marek Blahuš (2021-2022)
# this script tries to guess the actual gender and number of French
# noun-phrase constituents by looking at their context
# expects a vertical file tagged by FreeLing tagger with the following
# order of columns: word, tag, [..]
# the guessed gender and number are output as new columns at the end of
# each token line

import re
import sys

MAX_SENTENCE_LENGTH = 10000

# regular expressions for recognized token classes, each containing:
# - class code, as:  capture group P<class>, or 3rd character from the end in the
# last group's name
# - gender, as:  capture group P<gen>, or 2nd character from the end in the last
# group's name
# - number, as:  capture group P<num>, or 1st character from the end in the last
# group's name
TOKEN_CLASS_RE_DICT = {
    "determiner": re.compile(
        r"""^  # start
    [^\t]*  # word
    \t  # tab
    (?P<class>D)[^\t]{2}(?P<gen>[^\t])(?P<num>[^\t])  # tag
    """,
        re.X,
    ),
    "preposition_MS": re.compile(
        r"""^  # start
    (?i:du|au|jusqu'au)  # word
    \t  # tab
    (?P<class>S)P  # tag
    (?P<x_MS>)  # hardcoded values
    """,
        re.X,
    ),
    "preposition_P": re.compile(
        r"""^  # start
    (?i:des|aux|jusqu'aux|ès)  # word
    \t  # tab
    (?P<class>S)P  # tag
    (?P<x_CP>)  # hardcoded gender and number
    """,
        re.X,
    ),
    "pronoun": re.compile(
        r"""^  # start
    (?i:l'|la|le|les|aucun|aucune|aucunes|aucuns|autre|autres|certaines|certains|même|mêmes|nul|nulle|plusieurs|tel|telle|telles|tels|tous|tout|toute|toutes|un|une|quel|quelle|quelles|quels)  # word # noqa: E501
    \t  # tab
    (?P<class>P)[PIT][^\t](?P<gen>[^\t])(?P<num>[^\t])  # tag
    """,
        re.X,
    ),
    "adjective": re.compile(
        r"""^  # start
    [^\t]*  # word
    \t  # tab
    (?P<class>A)[^\t]{2}(?P<gen>[^\t])(?P<num>[^\t])  # tag
    """,
        re.X,
    ),
    "noun": re.compile(
        r"""^  # start
    [^\t]*  # word
    \t  # tab
    (?P<class>N)[^\t](?P<gen>[^\t])(?P<num>[^\t])  # tag
    """,
        re.X,
    ),
    "participle": re.compile(
        r"""^  # start
    [^\t]*  # word
    \t  # tab
    (?P<class>V)[^\t]P[^\t]{2}(?P<num>[^\t])(?P<gen>[^\t])  # tag
    """,
        re.X,
    ),
    "negation": re.compile(
        r"""^  # start
    (?i:non)\t  # word
    (?P<xO00>)  # hardcoded class, gender and number
    """,
        re.X,
    ),
}

STRUCT_RE = re.compile(r"^<[^\t]*>\n?$")

# uses token classes
PHRASE_RE = re.compile("(D|S|P|DD|SD|DP|PP)?[ANVO]{0,9}[ANV]")

DEFINITE_GEN_RE = re.compile(r"[MF]")
DEFINITE_NUM_RE = re.compile(r"[SP]")


# split iterator into lists of elements by separator (included as list's last element),
# limiting maximal list size
def splitby(seq, sep, maxsize):
    group = []
    for el in seq:
        group.append(el)
        if el == sep or len(group) >= maxsize:
            yield group
            group = []
    yield group


def classify(line):
    # tries to classify the given token into one of allowed classes
    mo = next(
        filter(
            bool, (class_re.match(line) for class_re in TOKEN_CLASS_RE_DICT.values())
        ),
        None,
    )
    if mo:
        return {
            "class": mo.groupdict().get("class") or mo.lastgroup[-3],
            "gen": mo.groupdict().get("gen") or mo.lastgroup[-2],
            "num": mo.groupdict().get("num") or mo.lastgroup[-1],
        }
    else:
        return {"class": "X", "gen": "0", "num": "0"}


def appendtoline(line, gen, num):
    return (
        line.rstrip("\n")
        + "\t{}\t{}".format(gen if gen != "C" else "M,F", num if num != "N" else "S,P")
        + "\n"
    )


for sentence in splitby(sys.stdin, "</s>\n", MAX_SENTENCE_LENGTH):
    tokens = [
        {"idx": idx, **classify(line)}
        for idx, line in enumerate(sentence)
        if not STRUCT_RE.match(line)
    ]
    for mo in PHRASE_RE.finditer("".join([t["class"] for t in tokens])):
        if len(mo.group(0)) < 2:
            continue
        curgen = next(
            (
                t["gen"]
                for t in tokens[mo.start(0) : mo.end(0)]
                if DEFINITE_GEN_RE.fullmatch(t["gen"])
            ),
            "C",
        )
        curnum = next(
            (
                t["num"]
                for t in tokens[mo.start(0) : mo.end(0)]
                if DEFINITE_NUM_RE.fullmatch(t["num"])
            ),
            "N",
        )
        for curpos in range(mo.start(0), mo.end(0)):
            if DEFINITE_GEN_RE.match(tokens[curpos]["gen"]):
                curgen = tokens[curpos]["gen"]
            else:
                tokens[curpos]["gen"] = curgen
            if DEFINITE_NUM_RE.match(tokens[curpos]["num"]):
                curnum = tokens[curpos]["num"]
            else:
                tokens[curpos]["num"] = curnum
    for token in tokens:
        sentence[token["idx"]] = appendtoline(
            sentence[token["idx"]], token["gen"], token["num"]
        )
    sys.stdout.write("".join(sentence))
