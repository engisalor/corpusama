# Changelog

## [0.2.0](https://github.com/engisalor/corpusama/compare/v0.1.1...v0.2.0) (2023-07-07)

This release has various significant changes and is not backwards compatible with previous versions. See `README.md` for current workflow.

Version `0.2.0` has pipelines for building Spanish and French corpora with FreeLing. An English pipeline is currently being redesigned and will be integrated soon.

Corpora can now be built using both HTML and PDF content on ReliefWeb.

### Features

* added FreeLing NLP
* added language identification with fastText
* added PDF extraction module
* `pipeline/` is now used for the final steps of corpus creation

### Bug Fixes

* Various bug fixes and small improvements

## [0.1.1](https://github.com/Humanitarian-Encyclopedia/corpusama/compare/v0.1.0...v0.1.1) (2022-12-14)

Includes various bug fixes and incremental improvements for making/managing a corpus.

### Bug Fixes

* **corpus:** drop empty vert content before insert ([1c1a2c4](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/1c1a2c4939c75bfb2ba63fe646a3c6b9d508e952))
* **corpus:** export_attribute 'parameters' arg ([c908447](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/c9084479cfb576fe24ad08a4372dfbb56867e24c))
* **corpus:** remove drop_attr arg ([879b441](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/879b4419254efe0a11c6fef8f42bae3a29b0a99c))
* **corpus:** update vertical content when outdated ([2641324](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/2641324b440ec6e044f34e28458cc1629ed4348b))
* **corpus:** use quoteattr, fix sql query syntax ([70db0c6](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/70db0c6d2bb752c7e3c3afd9ad2051cb217d0047))
* **corpus:** vertical docstrings, 'update' arg ([866eddf](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/866eddf631019e7e04f3352b38f14dd99247e2f4))
* **db:** add _about table ([e437afd](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/e437afd3a759876ae1336735f1508e0a9f3bc5b0))
* **db:** add_missing_columns method ([b80181a](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/b80181ae547619d9fd195e5d721fa92d49279deb))
* **source:** add manual override to _set_wait ([56ca19c](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/56ca19cfb3332a6db06babca6d09b389ebfc3770))
* **source:** add_missing_cols & drop fields_id ([f64682e](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/f64682e06e009d2cd1f980402d16760081d31e01))
* **source:** date.changed:asc - he-alike params ([6481199](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/6481199ff88326963807d0886ef197e7c54d2420))
* **source:** rw - replace run method with one ([fc95364](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/fc9536442115eff03745da6755bbc022569ed8e1))
* **source:** rw, abort insert if empty df ([701fd38](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/701fd387b8e610ed833978545c6ced36b6ed8b56))
* **source:** rw, add all, new methods ([03f8ef6](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/03f8ef6d849d21bd9329ebbe81f77c82e8ebca25))
* **source:** rw, automatically set wait ([9bfc159](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/9bfc159d2e3a0904dec554c3168136d11a521b4b))
* **source:** rw, improve set limit behavior ([d2ab0fd](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/d2ab0fdb695f8392cf4e46deca84497842ec3895))
* **source:** rw, set default limit to 1000 ([526aacc](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/526aacc28a73aa4ab3e613acaec2d93e530ce905))
* **source:** update rw-en, rw-es API parameters ([93bbc38](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/93bbc3860e625a00db1643ae63f9e9dcc668c598))
* **source:** update variables ([06bdadf](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/06bdadff5ac19999c647da30c44b559895cc7cab))
* **source:** use SystemExit, fix if/else behavior ([26e99ab](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/26e99ab9358ca815cdd2fa76fe4287d9f4da8eba))
* **util:** add clean_xml and xml_quoteattr methods ([e835d66](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/e835d66b2635038e604d2f5c9825ba47ab9f9734))
* **util:** add logging to convert.py ([108b052](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/108b05283fd14ed9d6d3a71a95aee4ad4c68d1a5))
* **util:** nan_to_none return a series of [None] ([a37fa62](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/a37fa622d077bedf61e0698b990a86feb0e49641))
* **util:** use UTC time for timestamps ([9d1504e](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/9d1504ee3e0f4f4dc3af7c4b3ba8df84f6b6f6ab))


### Documentation

* **corpus:** standardize docstrings ([dfc2ad1](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/dfc2ad10f0ce7b5abf9f1b0263239f8dff99450b))
* **db:** standardize docstrings ([593c790](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/593c7903eed7ac98f77349be2956b98e3b855b0d))
* **source:** standardize docstrings ([511a1d1](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/511a1d16635a651b5d1897d49b9664bf1f391630))
* standardize docstrings ([e222e06](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/e222e065d2504951672465b611420568db48e62d))
* **util:** standardize docstrings ([9b172e6](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/9b172e6645ef2bb8e3525b7a227bd979663c7149))

## 0.1.0 (2022-11-29)

Initial release
