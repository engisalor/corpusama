# Changelog

## [0.2.0](https://github.com/engisalor/corpusama/compare/v0.1.1...v0.2.0) (2023-07-07)


### Features

* add FreeLing NLP ([9b7ad63](https://github.com/engisalor/corpusama/commit/9b7ad637e63e73fc1843e7ee06f56c2da69be232))
* add language identification ([7e17728](https://github.com/engisalor/corpusama/commit/7e17728083f5525e63f82f2638fb5b641f31ef94))
* add pdf module ([009a648](https://github.com/engisalor/corpusama/commit/009a6489ac6386473ee263201300f0c8f5b4c9a7))


### Bug Fixes

* __init__ use logging basicConfig ([15b7de2](https://github.com/engisalor/corpusama/commit/15b7de2c7c4e48cd5c74dccaa1da20e5404b6cf1))
* adapt sketchengine files to repo ([0079752](https://github.com/engisalor/corpusama/commit/007975287c150f3cd04e5f10678ccc613c6aa490))
* add export module ([3f1f725](https://github.com/engisalor/corpusama/commit/3f1f725a92a68962e3233e028854f253a6881e04))
* add LangID class to langid, other refinements ([bfcfed8](https://github.com/engisalor/corpusama/commit/bfcfed808099e4d404a1bb6a6f2cdc2f8356ecad))
* add reliefweb_2000+ config ([a0e45a4](https://github.com/engisalor/corpusama/commit/a0e45a4fbf509b8e77d363897dbad6f0a0cd07fc))
* add SkE dir, comply w/ flake8 ([10c9461](https://github.com/engisalor/corpusama/commit/10c9461cd24638dcb29359b5fe4fa8a816e7ea37))
* add strip() to util.convert funcs, docstrings ([5a44753](https://github.com/engisalor/corpusama/commit/5a44753a86e15b28a75f64e67edcbb4e73367e17))
* auto-gen .logs/ dir ([f180389](https://github.com/engisalor/corpusama/commit/f180389b1a8edf070bb0dde0868dc9e95567ab98))
* Call update config load ([63bbbd1](https://github.com/engisalor/corpusama/commit/63bbbd17d80793a225be282691f4191e644ced27))
* citation cff quoting ([682ddfa](https://github.com/engisalor/corpusama/commit/682ddfab8941b7392e4f9aed577c4b459d1d7a70))
* corpus.langid size = 5000, change cols ([a5c0aa2](https://github.com/engisalor/corpusama/commit/a5c0aa23b4dacd0e2a51ec5a46c0b58465e2326d))
* corpus/vertical add log msgs, self.changed ([c31c2c7](https://github.com/engisalor/corpusama/commit/c31c2c70a9139c8c8a444cab7393c0f392b58796))
* **corpus:** avoid blank lines in archives ([7bc9c89](https://github.com/engisalor/corpusama/commit/7bc9c89027bb0711da9e49c1d182dba74510cf64))
* **corpus:** correct vulnerable_groups spelling ([fcc2c22](https://github.com/engisalor/corpusama/commit/fcc2c227e2d352741938e6d1bedfc8131671e123))
* **corpus:** import unique_attribute in Corpus ([157f4cb](https://github.com/engisalor/corpusama/commit/157f4cb4f169aadcf85c3dcd31cb777aaafd14df))
* **corpus:** overhaul archive methods ([c8196ec](https://github.com/engisalor/corpusama/commit/c8196ecf038548a4e43aec01635c86cf1aebf050))
* **corpus:** overhaul attribute methods ([f408ec8](https://github.com/engisalor/corpusama/commit/f408ec8ae09d2fa0f711ddb76d79fcc922509caf))
* **corpus:** stanza.load_nlp - add language arg ([2c99eb4](https://github.com/engisalor/corpusama/commit/2c99eb40f1277b333a3d9a4293c560e6c1e4d513))
* **corpus:** update make_vertical args ([5daebd9](https://github.com/engisalor/corpusama/commit/5daebd924adcc5b502010b4e85ac34033e8b1d2e))
* **corpus:** use year, doc_count  in _archive cols ([a0d9302](https://github.com/engisalor/corpusama/commit/a0d930227ea5d62c4e22d6feebba8657c07d53df))
* **db:** add missing_columns detection ([1004538](https://github.com/engisalor/corpusama/commit/1004538358f862f3d73356ba2ddcd2d7a6aa6c12))
* **db:** update rw schema ([bdb5bc3](https://github.com/engisalor/corpusama/commit/bdb5bc3a145c3d7fcf81d9a2279edee713b0d711))
* **db:** wip make_langid ([ebf5267](https://github.com/engisalor/corpusama/commit/ebf52675d08686e2eae8e7edd4826df3d0978986))
* deprecate api_input for Reliefweb log ([07576da](https://github.com/engisalor/corpusama/commit/07576da028e6597ba838ab37487164be83e763db))
* deprecate Database.fetch_batch ([c15351d](https://github.com/engisalor/corpusama/commit/c15351d4aa8b0a6506760b94221a62678be4d51d))
* exclude more rw-attributes ([818f8c7](https://github.com/engisalor/corpusama/commit/818f8c7e214d0e326a0f4dc87f5fd33c49d2dcfb))
* fix ske_fr pipeline, update ske_es ([3bd8177](https://github.com/engisalor/corpusama/commit/3bd8177d40e3001e1b4b3daf72907f6e45d2a20c))
* flatten add commented line for debugging ([27f4e27](https://github.com/engisalor/corpusama/commit/27f4e27b0a25bbd547442c3802880f0e0d106ae4))
* get_xpos convert to str values ([4449234](https://github.com/engisalor/corpusama/commit/4449234e11ef756c9e99268ff90536e5b09b5120))
* gitignore large files section ([1b438c4](https://github.com/engisalor/corpusama/commit/1b438c43c32a7eda269b8daacba60540ac832e6e))
* handle secrets for config ([a1d6146](https://github.com/engisalor/corpusama/commit/a1d6146caa0460a65207d8480f5a02f6a3bb4e10))
* improve attribute methods, use _attr table ([8785afc](https://github.com/engisalor/corpusama/commit/8785afc70ec7bca2eb2f716ecbcb33d3f930ada7))
* improve langid module ([58b557e](https://github.com/engisalor/corpusama/commit/58b557eb7b9c2da004817971721df40e964260cd))
* improve langid module ([9f5d214](https://github.com/engisalor/corpusama/commit/9f5d2140b27c1e0cbf13d23416bfed4c46ac050c))
* langid load uninorm, docstring ([917e5a1](https://github.com/engisalor/corpusama/commit/917e5a17848bfc6fec295872be846e9fba296461))
* langid.clean_lines all-upper to lower, keep - ([58eb9d3](https://github.com/engisalor/corpusama/commit/58eb9d3e0efafa18297179f0b929c1480ca8507f))
* **langid:** pass texts or files to LI ([18af0b5](https://github.com/engisalor/corpusama/commit/18af0b56dc5064271a68a4b63cf0ac33d6163194))
* move stanza, vert modules to pipeline ([bd64f46](https://github.com/engisalor/corpusama/commit/bd64f465581f4e83cbd57986da3c69940f312ba5))
* **parallel:** add run_with_timeout ([68e83e9](https://github.com/engisalor/corpusama/commit/68e83e92141f89ad2866c0c802fee9cbada60b71))
* remove old  tables from schema, update _lang ([71dae59](https://github.com/engisalor/corpusama/commit/71dae5921bb4ef846b4f91a9443688649393fd81))
* remove old methods from Corpus ([8b9b152](https://github.com/engisalor/corpusama/commit/8b9b15237861c65c08340b77375cd5be21894dfb))
* remove pipeline readme ([a51995b](https://github.com/engisalor/corpusama/commit/a51995b65aa4b9fb22b7386ce1b1e9c091fcd5e2))
* reorganize ske pipelines ([cbb1cae](https://github.com/engisalor/corpusama/commit/cbb1cae99846031cb842de0161f7016b5e47ddec))
* rw schema, allow null filesize, add redirects ([4c3ca12](https://github.com/engisalor/corpusama/commit/4c3ca1285c8ee9e19f0124e61fbb1f7cadea7cb7))
* **source:** add rw-all call params ([26c034e](https://github.com/engisalor/corpusama/commit/26c034ec14d16b8b2244d32349c459b2e1bcd80f))
* **source:** add rw-attribute.yml ([4efb68f](https://github.com/engisalor/corpusama/commit/4efb68f84cfcae34fb5045b1bae93b8119f68acd))
* update fr/es pipeline comments, fr dicc.src ([a3a63d2](https://github.com/engisalor/corpusama/commit/a3a63d2df09d4ec288fc2a84b104a288169245ed))
* update gitignore ([6421a8f](https://github.com/engisalor/corpusama/commit/6421a8f67ba6917d09049121c6242ae816527a40))
* update gitignore ([0361135](https://github.com/engisalor/corpusama/commit/03611357ffb4ef152ca465465ee2034c5d5e5bff))
* update gitignore ([6ce33c7](https://github.com/engisalor/corpusama/commit/6ce33c70e355b479e747e21ac5dc75cc337d0203))
* update gitignore large files ([c13c1f7](https://github.com/engisalor/corpusama/commit/c13c1f7b7f4b3ef15a53d44d2aedddbea0ccb858))
* update reliefweb attributes ([481a438](https://github.com/engisalor/corpusama/commit/481a438537c3746e8f858503522d2c8f68f1a5ae))
* update requirements ([564d3d9](https://github.com/engisalor/corpusama/commit/564d3d9e145c56c22c234d123b5eaea8f8473c1f))
* update requirements ([505dac1](https://github.com/engisalor/corpusama/commit/505dac1c62d9e119e9d4eebfbb0393dca915e131))
* use `l1` in langid functions instead of `top` ([cfa4dfd](https://github.com/engisalor/corpusama/commit/cfa4dfdcf257981074edff06776782218bb29e03))
* util add clean_text func ([619fb5e](https://github.com/engisalor/corpusama/commit/619fb5e6008852988bab2c433860f11fe96b5f11))
* **util:** add convert.list_to_string_no_sep ([b188f26](https://github.com/engisalor/corpusama/commit/b188f260b8cc947db25d18483a755f883474e82c))
* **util:** add limit_cores to parallel, update run ([82fae2c](https://github.com/engisalor/corpusama/commit/82fae2ce07fc8c192de9cdea2a5863a23836dde7))
* **util:** add parallel processing module ([728db2a](https://github.com/engisalor/corpusama/commit/728db2af913fa256fe9dbfabe532a41578efb13c))
* **util:** fix clean_xml_tokens regex behavior ([82f29bf](https://github.com/engisalor/corpusama/commit/82f29bfacad5bbd58b202ae4561fff7b71816fd5))
* **util:** langid  refinements ([af4b771](https://github.com/engisalor/corpusama/commit/af4b771c49309482a57913d4c956a50cdec32e48))
* **util:** remove CorpusAttribute dataclass ([72d138d](https://github.com/engisalor/corpusama/commit/72d138dd6a532d878960d2d3a10353df0ce79bb5))
* **util:** remove increment_version ([7cbf240](https://github.com/engisalor/corpusama/commit/7cbf2400d5bbb42e269c3f2de74da85b374bd364))


### Performance Improvements

* **corpus:** make_archive parallel processing ([4524e98](https://github.com/engisalor/corpusama/commit/4524e98bb48dd9529df9f3602182ed2e3f121108))


### Documentation

* add mkdocs.yml ([300e5e9](https://github.com/engisalor/corpusama/commit/300e5e9dc9f3e0ef330bc0c9a95f7a108acf0244))
* **corpus:** add note about ADD tag ([dee2fd2](https://github.com/engisalor/corpusama/commit/dee2fd2441144598ff62a44bb40ba245fd66c464))
* update docs ([02ed0b4](https://github.com/engisalor/corpusama/commit/02ed0b43aac6c298a283856f2a94a9a7c8fcc379))
* update readme ([ef557be](https://github.com/engisalor/corpusama/commit/ef557bef14dde7c7441a59da5c5428de616badae))
* update readme ([2484ecf](https://github.com/engisalor/corpusama/commit/2484ecfe079a3ba8e15f45aa28ab66bc1057430a))
* update readme, add usage.md ([c9324c9](https://github.com/engisalor/corpusama/commit/c9324c915dcd5c8d6b1513cb87587952df2075eb))

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
