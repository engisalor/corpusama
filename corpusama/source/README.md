# Source

This package contains methods related to the data collection phase. Currently, it consists of a module for managing API calls to [ReliefWeb](https://reliefweb.int/). Interfaces for more data sources can be built from the methods in the `source.call` module.

## ReliefWeb

[ReliefWeb's API guide](https://reliefweb.int/help/api) describes this service's features and offers a means to test calls directly in a browser. Also see [their GitHub page](https://github.com/reliefweb) and [OCHA's Humanitarian Data Exchange Project](https://github.com/OCHA-DAP) for related projects. JSON content is returned and its content is well-formatted. The notes below offer some guidance on finer points.

**Basic guidelines**

- no login/access token required
- use the parameter `appname` (an HE URL/email) for tracking purposes
- max 1,000 entries per call
- max 1,000 calls per day

### The `reliefweb` module

This module wraps the ReliefWeb API to simplify making queries and storing data.

- requirements `pip install requests pandas pyyaml`
- accepts parameters in JSON, YML, or dict format
- data is organized by report ID (see the `source` package for database details)
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
