# Corpus

This package contains code for building and maintaining Humanitarian Encyclopedia corpora.

Note that required Python packages and NLP models can take several GB of space. A fast CPU and/or dedicated GPU are also recommended, as generating a large corpus may take some time.

**Example usage**

```python
from corpus_maker.maker import Maker

# instantiate a Maker object
# this gets data from a sqlite database with ReliefWeb records
# loads the 'records' table into self.db
# and starts a stanza nlp pipeline
cm = Maker(
    db="data/reliefweb.db",
    resources="data/local-only/stanza_resources",
    processors='tokenize,pos,lemma')

# filter rows/manipulate the dataframe as needed to prepare data
cm.df = cm.df.head(20)

# process data and generate .vert files
cm.make_corpus()
```

## Source data

This package is designed to make corpora from sqlite databases of ReliefWeb API results. See the related data retrieval repository for details.

## Tokenization and lemmatization

The [Stanza NLP package](https://stanfordnlp.github.io/stanza/) is used to tokenize and lemmatize texts. In cases where lemmatization fails, the full token is passed instead and a warning is logged with more information. Lemmatization tends to fail for non-English words: many failures can indicate that a non-English text is part of the corpus.

## The EWT tagset

Stanza's default English treebank is [UD English EWT](https://universaldependencies.org/treebanks/en_ewt/index.html). See their documentation and this repo's `tagset.yml` file for more information.

To keep corpora more compatible with Sketch Engine, slight changes may be implemented when generating lempos tags from the EWT tagset. Currently, numbers expressed as digits are given a lempos of `[number]-m`, rather than `1,000-m`.

## Parsing HTML text

Before passing text to stanza, an HTML parser is run to prevent the corpus from being polluted by HTML code. This uses Python's standard html package and tends to work well, but keep in mind that parsing can change a corpus's content.

## Document attributes (text types)

### Parsing source data

Source data is processed to flatten nested lists and dictionaries and generate a column for each text attribute. Reliefweb's `country` field, for example, is flattened into `country__id`, `country__shortname`, etc. Two underscores are used to separate fields from subfields, and dashes are replaced with a single underscore (these characters break SkE corpus compilation).

### Adding attributes to SkE corpus config files

During corpus generation, attributes are tracked and saved to `<corpus-name>_attributes.txt`. The contents of this file should be added to a Sketch Engine configuration file before corpus compilation. By default, all attributes accept multiple values, with `|` as a separator. For example, a `year` attribute with multiple values might be `2003|2004|2005`.

### Excluding attributes

Each vertical file contains a `< doc >` tag with its attributes. Columns in the source data can be excluded from corpus attributes with the `drops` parameter for `make_corpus()`. It's best to avoid having many attributes, especially when values are uninformative.

### Watch for unexpected parsing behavior

Each value is parsed into JSON strings, which are generally compatible with Sketch Engine's compiler. Still, inspect results for unexpected behavior and unexpected `__None__` values in Sketch Engine text type analysis, which can indicate parsing issues.
