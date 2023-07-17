#!/usr/bin/python3
"""Script to compare vertical content produced by different pipelines.

Example:
    python -m pipeline.compare_vert \
        --mapping pipeline/en_tagsets.yml \
        --vert rw-ske.vert rw-freeling.vert rw-stanza.vert \
        --tagset ske-en-tt-2 fl-en ud-ewt

Note:
    Performed fairly during initial tests but may require further work.
"""
import argparse
import pathlib
import re
import subprocess  # nosec
from collections import Counter
from functools import reduce
from itertools import groupby

import pandas as pd

from corpusama.util import io as _io


class VertLine:
    """Class representing one line (token) in a vertical file."""

    def __repr__(self) -> str:
        return str(self.__dict__)

    def __init__(self, line: str) -> None:
        elem = line.split()
        self.word = elem[0]
        self.tag = elem[1]
        self.lemma = elem[2].split("-")[0]
        self.pos = elem[2].split("-")[-1]


def read_vert(file: str):
    """Reads a vertical file and returns a list of token lines (no XML tags)."""
    with open(file) as f:
        lines = f.readlines()
        lines = [x.strip() for x in lines if not x[0] == "<" and not x[-1] == ">"]
        return [VertLine(x) for x in lines]


if __name__ == "__main__":
    # get args
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", nargs=1, help="YAML file with tagset mapping")
    parser.add_argument("--vert", nargs="+", help="Vertical file(s)")
    parser.add_argument("--tagset", nargs="+", help="Tagset name for each vert")
    args = parser.parse_args()
    args = vars(args)
    mapping = _io.load_yaml(args["mapping"][0])
    vert = [
        {
            "file": pathlib.Path(args["vert"][x]),
            "lines": read_vert(args["vert"][x]),
            "tagset": args["tagset"][x],
        }
        for x in range(len(args["vert"]))
    ]

    # tag simplification
    tag_df = []
    ignored_df = []
    error_df = []
    for i in range(len(vert)):
        s = vert[i]["lines"]
        t = vert[i]["tagset"]
        file = vert[i]["file"].parent / ("vcompare.upos." + vert[i]["file"].name)
        # add .split(":")[0] after .get() to compare UPOS tags strictly
        upos = [f'{x.word}\t{mapping[t].get(x.tag, {}).get("upos", x.tag)}' for x in s]
        with open(file, "w") as f:
            f.write("\n".join(upos))
        print("... UPOS version for", file)
        # produce tag statistics
        tags = [mapping[t].get(x.tag, {}).get("upos", x.tag) for x in s]
        records = [
            {"tag": k, f'{vert[i]["file"].stem}': v} for k, v, in Counter(tags).items()
        ]
        tag_df.append(pd.DataFrame.from_records(records))

    # tag statistics
    # merge stats df
    tag_df = reduce(
        lambda left, right: pd.merge(left, right, on=["tag"], how="outer"), tag_df
    )
    tag_df.sort_values(["tag"], inplace=True)
    for i in range(len(vert)):
        tag_df[f'{vert[i]["file"].stem}'] = (
            tag_df[f'{vert[i]["file"].stem}'].fillna(0).astype(int)
        )
    # make stats sum df
    tag_df_sum = pd.DataFrame(tag_df.sum(axis=0, numeric_only=True))
    tag_df_sum["vert"] = [i for i in range(len(vert))]
    tag_df_sum.columns = ["sum", "vert"]
    tag_df_sum["sum"] = tag_df_sum["sum"].fillna(0).astype(int)
    print("... tag statistics")

    # compare vert files (vert[0] against each subsequent file)
    top_differences_df = []
    top_specific_df = []
    for i in range(1, len(vert)):
        # make diff file
        diff_file = vert[i]["file"].parent / ("vcompare.diff." + vert[i]["file"].name)
        cmd = [
            "diff",
            "--unchanged-line-format=0\t%L",
            "--old-line-format=1\t%L",
            "--new-line-format=2\t%L",
            f'{vert[0]["file"].parent / ("vcompare.upos." + vert[0]["file"].name)}',
            f'{vert[i]["file"].parent / ("vcompare.upos." + vert[i]["file"].name)}',
        ]
        with open(diff_file, "w") as f:
            subprocess.run(cmd, stdout=f)  # nosec
        print("... diff file", diff_file)

        # load diff file
        with open(diff_file) as f:
            lines = f.readlines()
        lines = [x.strip() for x in lines]

        # count errors
        numbers = "".join([x[0] for x in lines])
        error_spans = [x.span() for x in re.finditer("010|020", numbers)]
        errors = [
            {
                "file": vert[i]["file"].stem,
                "line#": x[0],
                "lines": "~~~".join(lines[x[0] : x[1]]).replace("\t", " "),
            }
            for x in error_spans
        ]
        error_df.append(pd.DataFrame.from_records(errors))
        vert[i]["errors"] = len(errors)

        # group by number: 0 (same) 1 (first .vert file) or 2 (second .vert file)
        groups = list(list(g) for k, g in groupby(lines, lambda item: item[0]))

        # splice/align vertical files
        new = []
        temp = []
        for group in groups:
            if group[0].startswith("0"):
                new.extend(group)
                temp = []
            else:
                temp.append(group)
            if len(temp) == 2:
                forward = []
                backward = []
                smallest = min([len(temp[0]), len(temp[1])])
                temp = [[y.split("\t") for y in x] for x in temp]
                for x in range(smallest):
                    # compare forwards
                    if temp[0][x][1] == temp[1][x][1]:
                        forward.append(
                            f"C\t{temp[0][x][1]}\t{temp[0][x][2]}\t{temp[1][x][2]}"
                        )
                        temp[0][x] = [""] * 3
                        temp[1][x] = [None] * 3
                    # compare backwards
                    if temp[0][-x][1] == temp[1][-x][1]:
                        backward.append(
                            f"C\t{temp[0][-x][1]}\t{temp[0][-x][2]}\t{temp[1][-x][2]}"
                        )
                        temp[0][-x] = [""] * 3
                        temp[1][-x] = [None] * 3
                # format remaining lines
                temp = [[[z for z in y if z] for y in x if y] for x in temp]
                temp = [[y for y in x if y] for x in temp if x]
                temp = [x for x in temp if x]
                temp = ["\t".join([" ".join(y[1:]) for y in x]) for x in temp]
                temp = "~~~|~~~".join(temp)
                if forward:
                    new.extend(forward)
                if temp:
                    new.append(f"I\t{str(temp)}")
                if backward:
                    new.extend(list(reversed(backward)))
                temp = []

        # save aligned diff file
        diff_file_align = vert[i]["file"].parent / (
            "vcompare.align." + vert[i]["file"].name
        )
        with open(diff_file_align, "w") as f:
            f.write("\n".join(new))
        print("... align diff file", diff_file_align)

        # extract token groups
        comparable = [x[2:] for x in new if x[0] == "C"]
        ignored = [x[2:] for x in new if x[0] == "I"]
        same = [x[2:] for x in new if x[0] == "0"]
        comp = Counter(comparable)
        ign = Counter(ignored)

        # get numbers
        vert[i]["tokens_total"] = len(vert[i]["lines"])
        total_compared = len(comparable) + len(same)
        vert[i]["tokens_compared"] = total_compared
        vert[i]["same"] = len(same)
        vert[i]["same%"] = len(same) / total_compared
        vert[i]["different"] = len(comparable)
        vert[i]["diff%"] = len(comparable) / total_compared
        vert[i]["ignored"] = len(ignored)

        # make comparable diff TSV file
        comparable_file = vert[i]["file"].parent / (
            "vcompare.comparable." + vert[i]["file"].stem + ".tsv"
        )
        ls = [
            {
                "token": k.split("\t")[0],
                vert[0]["file"].stem: k.split("\t")[-2],
                vert[i]["file"].stem: k.split("\t")[-1],
                "count": v,
            }
            for k, v in comp.items()
        ]
        df = pd.DataFrame.from_records(ls)
        df["diff%"] = (df["count"] / len(comparable)) * 100
        df["total%"] = (df["count"] / total_compared) * 100
        df.sort_values("count", ascending=False, inplace=True)
        df.to_csv(comparable_file, sep="\t", index=False)
        print("... comparable file", comparable_file)
        top_specific_df.append(df)

        # make comparable diff summary TSV file
        comparable_file_summary = vert[i]["file"].parent / (
            "vcompare.comparable.summary." + vert[i]["file"].stem + ".tsv"
        )
        sum_df = df.groupby([vert[0]["file"].stem, vert[i]["file"].stem]).sum()
        sum_df = sum_df[["count"]]
        sum_df.reset_index(inplace=True)
        sum_df["diff%"] = (sum_df["count"] / len(comparable)) * 100
        sum_df["diff%"] = sum_df["diff%"]
        sum_df["total%"] = (sum_df["count"] / total_compared) * 100
        sum_df["total%"] = sum_df["total%"]
        sum_df.to_csv(comparable_file_summary, sep="\t", index=False)
        print("... comparable file", comparable_file_summary)
        top_differences_df.append(sum_df)

        # make ignored tokens TSV file
        ignored_file = vert[i]["file"].parent / (
            "vcompare.ignored." + vert[i]["file"].stem + ".tsv"
        )
        ls2 = [
            {
                vert[0]["file"].stem: k.split("~~~|~~~")[0].replace("\t", " "),
                vert[i]["file"].stem: k.split("~~~|~~~")[1].replace("\t", " "),
                "count": v,
            }
            for k, v in ign.items()
            if "~~~|~~~" in k
        ]
        ign_df = pd.DataFrame.from_records(ls2)
        ign_df["ignored%"] = (ign_df["count"] / len(ignored)) * 100
        ign_df.sort_values("count", ascending=False, inplace=True)
        ign_df.to_csv(ignored_file, sep="\t", index=False)
        print("... ignored file", ignored_file)
        ignored_df.append(ign_df)

    # prepare report data
    vert[0]["tokens_total"] = float(len(vert[0]["lines"]))
    report_summary = vert[i]["file"].parent / ("vcompare.summary.tsv")

    for v in vert:
        v.pop("lines")

    vert_df = pd.DataFrame.from_records(vert)
    vert_df = vert_df.fillna(0)
    for col in ["same%", "diff%"]:
        vert_df[col] = vert_df[col].round(4) * 100

    col_order = [
        "file",
        "tagset",
        "tokens_total",
        "tokens_compared",
        "same",
        "different",
        "same%",
        "diff%",
        "ignored",
        "errors",
    ]
    vert_df = vert_df[col_order]
    vert_df.to_csv(report_summary, sep="\t", index=False)
    print("... report summary", report_summary)

    error_file = vert[0]["file"].parent / ("vcompare.errors.tsv")
    error_df = pd.concat(error_df)
    error_df.to_csv(error_file, index=False)

    vert_df.sample()

    def df_sample_to_html(df):
        ls = []
        for x in range(len(vert) - 1):
            ls.append(
                df[x]
                .nlargest(25, "count")
                .to_html(index=False, float_format="{:,.2f}".format)
            )
        return "\n\n".join(ls)

    top_differences_df = df_sample_to_html(top_differences_df)
    top_specific_df = df_sample_to_html(top_specific_df)
    ignored_df = df_sample_to_html(ignored_df)
    error_df = error_df.sample(25).sort_values("file").to_html(index=False)

    # make report MD file
    md = f"""# POS tagger vertical file comparison

This report shows the tagging differences between two or more vertical files (same
source text, different taggers). Structures like `<doc>` and `<s>` are ignored.

Vertical files are compared by simplifying their tagsets into a standardized
[UPOS](https://universaldependencies.org/u/pos/index.html)-like tagset.
Tokens across files are then aligned sequentially. Exact matches, comparable tokens,
and ignored tokens are identified; main tagging behaviors are then summarized.

## Date

{pd.Timestamp.now().round(freq='S').isoformat()}

## Summary

{vert_df.to_html(index=False, float_format='{:,.2f}'.format)}

### Notes

- first row is reference file that others are compared against
- `tokens_total` = lines excluding XML tags
- `tokens_compared` = lines successfully compared
- `same` = lines with identical UPOS values
- `same%` = percentage of matching lines
- `different` = lines with different UPOS values
- `diff%` = percentage of non-matching lines
- `ignored` = line groups not compared (sequences of 1+ lines)
- `errors` = line groups improperly aligned

## Tag statistics

{tag_df.to_html(index=False)}

{tag_df_sum.to_html()}

## Top types of tag differences

{top_differences_df}

### Notes

- `diff%` is a row's share of the total number of comparable differences
- `total%` is a row's share of the total number of comparable tokens

## Top specific tag differences

{top_specific_df}

## Top ignored token sequences

{ignored_df}

## Sample alignment errors

{error_df}

## Understanding the data

The UPOS-like tagset used to compare taggers is at times simplistic: it is often
unambiguous for some tags (PUNCT), but cases arise where differences identified
by this script correspond to more generalized ambiguities in a language. One example is
when "be" is tagged as VERB in one tagger and AUX in another: both may be correct, or
the difference may be caused by a loss of data richness when tagsets are standardized.

That said, some differences have meaningful implications for pattern-based data
extraction. For example, FreeLing more often labels tokens as past participles than
Sketch Engine's modified TreeTagger, which prefers adjectives (e.g, "limited").
Designing corpus querying techniques that work equally well for many corpus creation
pipelines should take such distinctions into account.

While the participle/adjective example is not novel, this script allows for precisely
quantifying such differences. Comparing ignored tokens is also helpful to understand
tokenization behavior (how each tagger decides to split a string into N tokens).
Still the summary here should not be used to extrapolate too much without viewing the
full `.diff` files this script produces.

Content is ignored when there's no 1:1 equivalence between tokens; i.e., characters are
kept as 1 token by one tagger but split into 3 by another. Ignored lines and errors
should be inspected manually, but generally a few are to be expected.

In rare cases, Stanza outputs tokens with spaces ("Sri Lanka"). Spaces have been
replaced with underscores to facilitate token comparison.

## About

See [Corpusama's](https://github.com/engisalor/corpusama) `pipeline.compare_vert` tool.
"""

    report_file = vert[i]["file"].parent / ("vcompare.report.md")

    with open(report_file, "w") as f:
        f.write(md)
    print("... report", report_file)
