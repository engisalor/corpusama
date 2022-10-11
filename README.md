# API-scripts

This repository is for storing code that utilizes API-based data sources. This can include scripts for one-off tasks, testing, and related needs. Use this README to document details for each API and the activities developed for HE operations.

Reminder: when using these scripts, keep access tokens and the like private and out of git's history.

## ReliefWeb

[API guide](https://reliefweb.int/help/api)

JSON content is returned and its content is well-formatted.

[Their GitHub page](https://github.com/reliefweb) has some projects.

- no login/access token required
- use the parameter `appname` (an HE URL/email) for tracking purposes
- max 1,000 entries per call
- max 1,000 calls per day
- intellectual property rights must be assessed by document source, e.g. checking organization policies
