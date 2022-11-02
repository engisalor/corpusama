# Humanitarian Encyclopedia Corpus Maker

*Under construction*

This repo contains code for building and maintaining Humanitarian Encyclopedia corpora.

Note that required Python packages include stanza, which has dependencies, like torch, exceeding 1 GB. Downloading language resources for stanza can also add >1 GB of files. Using stanza with large data sets may require higher CPU/GPU/memory performance.

Usage:

```python
from corpus_maker.maker import Maker

# instantiate a Maker object
# this gets data from a sqlite database with ReliefWeb records
# loads the 'records' table into self.db
# and starts a stanza nlp pipeline
cm = Maker(
    db="data/reliefweb.db",
    resources="data/local-only/stanza_resources",
    processors='tokenize,mwt,pos,lemma')

# filter rows/manipulate the dataframe as needed to prepare data
cm.df = cm.df.head(20)

# run stanza on the 'body' column and export as files in a compressed tar.xz archive
cm.export_vert(tarname="data/he.tar.xz")

# next, compile this corpus using NoSketchEngine, etc.
```
