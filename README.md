# API-scripts

This repository is for storing code that utilizes API-based data sources. This can include scripts for one-off tasks, testing, and related needs. Use this README to document details for each API and the activities developed for HE operations.

Reminder: when using these scripts, keep access tokens and the like private and out of git's history.

## ReliefWeb

Their [API guide](https://reliefweb.int/help/api) is simple and making calls can be tested in a browser.

JSON content is returned and its content is well-formatted.

[Their GitHub page](https://github.com/reliefweb) has some projects.

- no login/access token required
- use the parameter `appname` (an HE URL/email) for tracking purposes
- max 1,000 entries per call
- max 1,000 calls per day
- intellectual property rights must be assessed by document source, e.g. checking organization policies

### The `rwapi` package

This package wraps the ReliefWeb API to simplify making queries and storing data.

- accepts parameters in JSON, YML, or dict format
- existing reports are overwritten (determined by the `"id"` field)
- can make sets of calls to retrieve multiple pages of results
- waits between calls
- tracks API usage and limits to daily quota
- see the docstrings in `manager.py` for details

**Installation**

Clone this repository and run `pip install requests pandas pyyaml`

**Usage**

See example below for making a call.

- make a parameters dictionary (see `example.json` and `example.yml`)
- use an `appname` as per RW guidelines
- explore data via terminal or a GUI application, e.g. [sqlitebrowser](https://sqlitebrowser.org/)

```python
import rwapi

# make a rw Manager object to start working
rw = rwapi.Manager()

# execute a call
rw.call("rwapi/calls/<parameters_file>.json", "<appname>")
```
