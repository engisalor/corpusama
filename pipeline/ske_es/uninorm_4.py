#!/usr/bin/python3

__version__ = "4.0"

import html
import io
import re
from unicodedata import category, normalize

TAG_RE = re.compile(
    r"""<!--.*?-->|<[!?/]?[^\W\d][\w:\.-]*(\s+[^\W\d][\w:\.-]*\s*=\s*('[^']*'|"[^"]*"))*\s*/?\s*>""",  # noqa: E501
    re.UNICODE,
)
CHARREF = re.compile(
    r"&(#[0-9]+;|#[xX][0-9a-fA-F]+;|[^\t\n\f <&#;]{1,32};)"
)  # html._charref, but with compulsory semicolon
BASIC_XML_ENTITIES = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&apos;",
}


def replace_charref(s):
    replacement = html._replace_charref(s)
    if replacement in BASIC_XML_ENTITIES:
        return BASIC_XML_ENTITIES[replacement]
    return replacement


def replace_html_entities(text):
    if "&" not in text:
        return text
    return CHARREF.sub(replace_charref, text)


def remove_control_chars(text, exceptions=[]):
    return "".join(
        [c for c in text if c in exceptions or not category(c).startswith("C")]
    )


def normalize_spaces(text):
    return "".join([(" " if category(c) == "Zs" else c) for c in text])


SINGLE_QUOTE_RE = re.compile(
    "[\u0027\u0060\u00b4\u02bc\u055a\u07f4\u07f5\uff07\u2018\u2019\u201a\u201b\u2039\u203a\u275b\u275c\u02b9\u2032\u2035]"  # noqa: E501
)
DOUBLE_QUOTE_RE = re.compile(
    "[\u0022\u276e\u276f\uff02\u201c\u201d\u201e\u201f\u00ab\u00bb\u301d\u301e\u301f\u275d\u275e\u2033\u2036\u02ba\u02ee]"  # noqa: E501
)


def normalize_quotes(text):
    text = SINGLE_QUOTE_RE.sub("'", text)
    text = DOUBLE_QUOTE_RE.sub('"', text)
    return text


HYPHEN_RE = re.compile(
    "[\u002d\u058a\u05be\u1400\u1806\u2010\u2011\u2e17\u2e1a\u30a0\ufe63\uff0d]"
)
DASH_RE = re.compile(
    "[\u2012\u2013\u2014\u2015\u2e3a\u2e3b\u2e40\u301c\u3030\ufe31\ufe32\ufe58]"
)


def normalize_dashes(text):
    text = HYPHEN_RE.sub("-", text)
    text = DASH_RE.sub("\u2013", text)
    return text


NEWLINE = {"unix": "\n", "dos": "\r\n"}


def normalize_line(
    line,
    normal_form="NFKC",
    tab="space",
    keep_chars=["200D"],
    new_line="unix",
    keep_quotes=False,
    keep_dashes=False,
    dont_strip=False,
    keep_empty=False,
):
    line = replace_html_entities(line)
    line = normalize_spaces(line)
    # don't break tags
    parts = []
    pos = 0
    for mo in TAG_RE.finditer(line):
        startpos, endpos = mo.span()
        if startpos > pos:
            betweentags = line[pos:startpos]
            betweentags = normalize(normal_form, betweentags)
            if not keep_quotes:
                betweentags = normalize_quotes(betweentags)
            if not keep_dashes:
                betweentags = normalize_dashes(betweentags)
            parts.append(betweentags)
        tag = line[startpos:endpos]
        tag = normalize("".join([c for c in normal_form if c != "K"]), tag)
        parts.append(tag)
        pos = endpos
    if pos < len(line):
        betweentags = line[pos:]
        betweentags = normalize(normal_form, betweentags)
        if not keep_quotes:
            betweentags = normalize_quotes(betweentags)
        if not keep_dashes:
            betweentags = normalize_dashes(betweentags)
        parts.append(betweentags)
    line = "".join(parts)
    # control characters
    if tab == "space":
        line = line.replace("\t", " ")
    elif tab == "none":
        line = line.replace("\t", "")
    elif tab == "tab":
        keep_chars.append("9")  # force keeping tabs
    line = remove_control_chars(line, exceptions=[chr(int(c, 16)) for c in keep_chars])
    lines = line.replace("\u2028", "\n").replace("\u2029", "\n").split("\n")
    # print out
    result = ""
    for line in lines:
        if not dont_strip:
            line = line.strip()
        if keep_empty or len(line) > 0:
            result += line
            result += NEWLINE[new_line]
    return result


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Universal text normalizer for linguistic research. Output is always UTF-8."  # noqa: E501
    )
    parser.add_argument(
        "-e", "--encoding", help="input encoding (default:'utf_8')", default="utf_8"
    )
    parser.add_argument(
        "-d",
        "--decoding-errors",
        help="treatment of decoding errors (default:'replace', 'ignore' or 'strict')",
        default="replace",
    )
    parser.add_argument(
        "-f",
        "--normal-form",
        help="Unicode normal form (default:'NFKC', 'NFC', 'NFKD' or 'NFD')",
        default="NFKC",
    )
    parser.add_argument(
        "-t",
        "--tab",
        help="tab replacement (default:'space', 'tab' or 'none')",
        default="space",
    )
    parser.add_argument(
        "-c",
        "--keep-chars",
        help="control characters to keep, space-separated hexadecimal numbers (default:200D)",  # noqa: E501
        nargs="*",
        default=["200D"],
    )
    parser.add_argument(
        "-n",
        "--new-line",
        help="new line character (default:'unix' or 'dos')",
        default="unix",
    )
    parser.add_argument(
        "-q",
        "--keep-quotes",
        help="keep various quotes and apostrophes (default:off)",
        action="store_true",
    )
    parser.add_argument(
        "-a",
        "--keep-dashes",
        help="keep various dashes and hyphens (default:off)",
        action="store_true",
    )
    parser.add_argument(
        "-s",
        "--dont-strip",
        help="keep leading and trailing whitespace (default:off)",
        action="store_true",
    )
    parser.add_argument(
        "-z", "--keep-empty", help="keep empty lines (default:off)", action="store_true"
    )
    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + __version__
    )
    args = parser.parse_args()
    kwargs = vars(args).copy()
    del kwargs["encoding"]
    del kwargs["decoding_errors"]

    stdin = io.TextIOWrapper(
        sys.stdin.buffer, encoding=args.encoding, errors=args.decoding_errors
    )
    stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    for line in stdin:
        normalized = normalize_line(line, **kwargs)
        stdout.write(normalized)
