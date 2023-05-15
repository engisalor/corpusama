# Corpusama

Corpusama is a Python-based language corpus management tool. Its initial goal is to develop a semi-automated pipeline for creating corpora from the [ReliefWeb](https://reliefweb.int/) database of humanitarian texts.

## Usage

Corpusama is currently designed for building corpora with texts from the ReliefWeb API. The project is still under development and can be expected to change significantly during its beta phase.

Clone this repo and install dependencies. Note that the [Stanza NLP package](https://github.com/stanfordnlp/stanza) can require several GB of space.

Example workflow:

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


## Acknowledgements

Corpusama has received support from the [Humanitarian Encyclopedia](https://humanitarianencyclopedia.org/) and the [LexiCon research group](https://lexicon.ugr.es/) at the University of Granada. Its dependencies include the [Stanza NLP package](https://github.com/stanfordnlp/stanza), [PyMuPDF](https://github.com/pymupdf/PyMuPDF), and [fastText](https://github.com/facebookresearch/fastText).
