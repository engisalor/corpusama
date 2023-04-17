# Corpusama usage notes

This document describes some of Corpusama's components and behaviors. It doesn't yet qualify as a user guide.

## Source

This package contains methods related to the data collection phase. Currently, it consists of a module for managing API calls to [ReliefWeb](https://reliefweb.int/). Interfaces for more data sources can be built from the methods in the `source.call` module.

### ReliefWeb

This module wraps the ReliefWeb API to simplify making queries and storing data.

[ReliefWeb's API guide](https://reliefweb.int/help/api) describes this service's features and offers a means to test calls directly in a browser. Also see [their GitHub page](https://github.com/reliefweb) and [OCHA's Humanitarian Data Exchange Project](https://github.com/OCHA-DAP) for related projects. JSON content is returned and its content is well-formatted, though some errors can be expected. The notes below offer some guidance on finer points.

**Basic guidelines**

- no login/access token required
- use the parameter `appname` (an HE URL/email) for tracking purposes
- max 1,000 entries per call
- max 1,000 calls per day


**Data retrieval features**

- accepts parameters in JSON, YML, or dict format
- data is organized by report ID
- handles retrieving multiple pages of results
- sets a wait time between calls
- tracks API usage and limits to daily quota
- see docstrings for details

**An example API call**

```python
from corpusama.source.reliefweb import ReliefWeb

# supply an input with call parameters and a database name
job = ReliefWeb(<input>, "<database.db>")
# execute the job
job.run()
```

### Using offset for large jobs

Any query with over 1,000 records requires using the `offset` parameter to download each page of results with successive API calls. This repo increases `offset` by 1,000 for each call, starting from 0.

### Duplicate results

Records have unique IDs and API results generally don't return duplicated content, but it does happen occasionally.

One job for 194,319 records indeed returned this many records, but 15 were duplicated in different pages of results, meaning the actual number of unique records was 194,304. This is contrary to the `total_count` field, particularly since content for the duplicates was exactly the same.

Importantly, `total_count` can't always be used as a reliable sum total. So far it appears safe to ignore duplicates, keeping either the original or repeat version of the record. If there is a slight possibility that records are updated retroactively, keeping the latest version may be the better choice.

### The `total_count` field is a moving goalpost

The `total_count` field can and does change often if queries include current content. A call can indicate N results are available and thirty seconds later another call can indicate N+1 results.

### Excluding fields can still return unwanted content

If a query excludes all languages but English, the API retrieves all records with English content, including whatever non-English content is part of that record. In the case of PDF attachments, this means a record will include URLs to the English version and the Arabic version and the French version, etc. When analyzing or downloading data, an extra step is needed to filter these unwanted documents.

There are sometimes `description` fields for PDFs indicating languages, short versions, appendices, and other kinds of attachments, but these strings are not fully standardized.

### Length limitations for spreadsheet software

Using Excel to view API results is possible, but not recommended. Users without SQL knowledge can try software like [DB Browser for SQLite](https://sqlitebrowser.org/).

Most rows in a SQL database of API results are made up of short strings. Most cells are actually string representations of objects, including a mix of lists and dictionaries, which requires further manipulation to extract individual data points. This might necessitate converting strings to JSON format, for example using Python's `ast.literal_eval` and `json.dumps` functions, and then parsing JSON strings into spreadsheet software.

Another concern is that while the `description` field is generally a brief text of around 500 words, it's sometimes many pages of content with more than the allowable number of characters for some spreadsheet software.

### Choosing between `body` and`body-html`

Perhaps counterintuitively, the `body-html` field may be a cleaner source of text than `body`. Although `body` is generally in plaintext format, it can also include HTML and markdown text, ultimately making it necessary to standardize them. Just parsing `body-html` to plaintext might be more reliable.

Keep in mind that choosing only one of these fields to download should nearly halve the final database size.

## Corpus

This package contains code for building and maintaining Humanitarian Encyclopedia corpora.

Note that required Python packages and NLP models can take several GB of space. A fast CPU and/or dedicated GPU are also recommended, as generating a large corpus may take some time.

### Tokenization and lemmatization

The [Stanza NLP package](https://stanfordnlp.github.io/stanza/) is used to tokenize and lemmatize texts. In cases where lemmatization fails, the full token is passed instead and a warning is logged with more information. Lemmatization tends to fail for foreign words: many failures can indicate that texts are in languages that differ from the chosen Stanza Pipeline language.

### Hyphenation

Some NLP models split hyphenated words such that each word and hyphen is a separate token: `oil-based` will be three tokens `oil` `-` `based`. Query languages in corpus management systems may not use this segmentation by default: queries may need to be modified to separate hyphens from their adjoining tokens.

### The EWT tagset

Stanza's default English treebank is [UD English EWT](https://universaldependencies.org/treebanks/en_ewt/index.html). See their documentation and tagset files in generated in `corpusama/corpus/`.

To keep corpora more compatible with Sketch Engine, slight changes may be implemented when generating lempos tags from the EWT tagset. Currently, numbers expressed as digits are given a lempos of `[number]-m`, rather than `1,000-m`.

### Parsing HTML text

Before passing text to stanza, an HTML parser is run to prevent the corpus from being polluted by HTML code. This uses Python's standard html package and tends to work well, but keep in mind that parsing changes text content.

### Document attributes (text types)

Source data is processed to flatten nested lists and dictionaries and generate a column for each text attribute. Reliefweb's `country` field, for example, is flattened into `country__id`, `country__shortname`, etc. Two underscores are used to separate fields from subfields, and dashes are replaced with a single underscore (these characters break SkE corpus compilation).

### Adding attributes to SkE corpus config files

During corpus generation, corpus attributes are tracked and can be exported (see usage example). previously undetected attributes should added to a Sketch Engine configuration file before corpus compilation. By default, all attributes accept multiple values, with `|` as a separator. For example, a `year` attribute with multiple values might be `2003|2004|2005`.

### Excluding attributes

Each vertical file contains a `< doc >` tag with its attributes. Metadata fields the source data can be excluded from corpus attributes with the `drops` parameter for `make_corpus()`. It's best to avoid having many attributes, especially when values are uninformative.

### Watch for unexpected parsing behavior

Each value is parsed into JSON strings, which are generally compatible with Sketch Engine's compiler. Still, inspect results for unexpected behavior and unexpected `__None__` values in Sketch Engine text type analysis, which can indicate parsing issues.
