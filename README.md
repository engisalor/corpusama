# Corpusama

Corpusama is a Python-based language corpus creation tool supported by the [Humanitarian Encyclopedia](https://humanitarianencyclopedia.org/) and University of Granada [LexiCon research group](https://lexicon.ugr.es/). Its initial goal is to develop a semi-automated pipeline for creating corpora from the [ReliefWeb](https://reliefweb.int/) database of humanitarian texts.

## Installation

Clone this repo and install dependencies. Note that the [Stanza NLP package](https://github.com/stanfordnlp/stanza) and other dependencies can require several GB of space.

## Usage

Corpusama is currently designed for building corpora with texts from the ReliefWeb API. So far, it focuses on English HTML content. The project is still under development and can be expected to change significantly.

Researchers interested in humanitarian discourse can use Corpusama to reproduce ReliefWeb corpora and undertake linguistic analyses. The workflow will vary depending on the project, but looks something like this:

```python
from corpusama.corpus.corpus import Corpus

# Step 1: get new/modified ReliefWeb records
job = ReliefWeb("corpusama/source/params/rw-en.yml", "rw-en.db")
# check when the corpus was last updated
res = job.db.c.execute("""
SELECT
    MAX(json_extract(_raw.date, '$.changed'))
    FROM _raw""")
res.fetchall()
# get new/newly modified records
# (downloading API content can take hours)
job.new()

# Step 2: update corpus content
# define corpus settings
corpus = Corpus("rw-en.db")
# generate vertical content
# (requires a capable CPU/GPU; the first run may take days)
corpus.make_vertical("en")
# insert attributes
corpus.make_attribute(cores=6)
# check for attribute warnings
unique = corpus.unique_attribute()
# combine vertical content by year into compressed files
corpus.make_archive()
# generate a list of corpus attributes detected
corpus.export_attribute()
# export compressed corpus files from sqlite
corpus.export_archive()

# Step 3: load corpus and explore the data (done separately from Corpusama)
# develop a corpus configuration file
# compile the corpus with NoSketch Engine
# run NoSketch Engine and run queries
```
