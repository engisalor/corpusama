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
- `Manager` will execute a call and save data to a SQLite database
- new reports are added and existing reports are overwritten (determined by the `"id"` field)
- see the docstrings in `manager.py` for details

**Installation**

Clone this repository and run `pip install requests pandas pyyaml`

**Usage**

See example below for making a call.

- make a parameters dictionary (see `example.json` and `example.yml`)
- use an `appname` as per RW guidelines
- run `rwapi.Manager()`
- explore data via terminal or a GUI application, e.g. [sqlitebrowser](https://sqlitebrowser.org/)
- `Manager` objects can optionally be inspected for troubleshooting

```python
manager_object = rwapi.Manager("rwapi/example.yml", "<appname>")
```
