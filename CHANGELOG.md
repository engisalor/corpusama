# Changelog

## 0.1.0 (2022-11-29)


### ⚠ BREAKING CHANGES

* rename library
* begin merge of api tools a corpus tools

### Features

* add make_corpus method + related ([36b259e](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/36b259e2840fffa1004afb437c4f36faa5eceaa6))
* add utils module ([143133e](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/143133e96f113637a1639c0386a83b77906100de))
* begin merge of api tools a corpus tools ([b069e04](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/b069e04d66a2a4cea96a797b6443a484ddf14091))
* load tagsets from yml files ([4f66eb2](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/4f66eb270ff02dcccf93f96dcdd4d87609abd92e))
* merge corpus package ([e53a2e4](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/e53a2e4e34bbde686641f89dc8c35cb5107f1fee))
* methods for doc_tags, save attrs to file ([ff0fa57](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/ff0fa57d7f4a1e643935c801c5575153176ca1dc))
* run nlp in batches and append to .tar ([3b8ada2](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/3b8ada22c549c1e428460dc910280c7c83032767))


### Bug Fixes

* _insert_records replace - with _ in col names ([e957267](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/e9572673d85a64e2c669028f3691446f829b895b))
* activate & conform to bandit pre-commit rules ([6bfd230](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/6bfd2303d56b1ea39e843383c9cc05069ae3a80c))
* add db module, Database class, key methods ([b2ed6ee](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/b2ed6eed182b7e93363e43986cb9d4199e72b6ec))
* add get_xpos  and number_lemma methods ([2eb12a4](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/2eb12a41cf1e89a10c2ad84f6bb863e021ebb94d))
* add maker module ([0425a16](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/0425a1618c4c6c6696fd207e8261b5ccfe0a0a4a))
* add params_hash and pop pdf methods ([257d39e](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/257d39ea031fa9e8277603165e22c9c305b392e8))
* append to tar, no compression ([7504aca](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/7504acadfe58f160d64e968aa987e448bb43336c))
* closes Implement pre-commit hooks [#10](https://github.com/Humanitarian-Encyclopedia/corpusama/issues/10) ([cf0fba9](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/cf0fba90d1cd33c643323c65c4d3f50b1ca4629e))
* control update nlp model settings ([a740337](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/a7403373665b4ec63e67b1d8b8cc1b095d747538))
* **database:** add update_column, fetch_batch ([0532783](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/05327838855bc68ab0783d9b11e682c77ee82b51))
* **database:** update schema/methods, pop get_df ([12d7c48](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/12d7c48bbb078ef21f92f47b9ceeaeb1094e93bf))
* deprecate _tar, save .vert to filesystem ([ddded50](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/ddded502ca287e811b1d3ab8f403c5440d6c13ba))
* doc_tag empty attrs, append attrs w/ batches ([9315a1f](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/9315a1fa27722801ad0082f10f53bf545fc61912))
* extra spaces in tagset ([6a96714](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/6a96714dae189f739ebad523f097e9ad5842af28))
* get version from __init__ ([af167be](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/af167be027baea35c00f62ca58e957e176c0e60e))
* html_to_text handle non-strings ([38b184c](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/38b184cc51585666a0e1e14e354e2e946b1bea41))
* improve prepare_df and flatten_df ([a577673](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/a577673f9d6676259713276d4b4dcf57f5c64bcc))
* improve tar & export methods ([4a4809e](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/4a4809ec01e3036515df9cbf55c771efa7d9d81a))
* insert_log data types ([a78f16c](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/a78f16c98e4ecfdd46d354594752d9b875f04f31))
* manage missing lemmas from stanza ([95bedaf](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/95bedafc8b7ccb9920748bb69b162777cc900fa1))
* merge database package ([b4b9ebd](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/b4b9ebd93e93b85a445ccfdba425fc2ad5d7631e))
* merge source module ([76e650a](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/76e650a16bc45f2d941105fdd1a4184dabab2c2c))
* merge util package ([6fa300b](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/6fa300bdccc1eacab55d299a18e50ba25785ef6a))
* move orphaned id detection to db.py ([7e337d7](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/7e337d7a05766a0496126433edc49d7404c3b6a5))
* pop old manager methods ([9719c01](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/9719c01cc01770e71197560e6bb75bb79deec812))
* refactor maker, set make_corpus defaults ([bfc350c](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/bfc350c00f215a95a3485341dcaed4dc9b6f143b))
* refactor orphan_ids, add test ([c575144](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/c575144f8887102687b17209b49668765909d837))
* remove orphan column from pdfs table ([f5cd424](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/f5cd42459161edd03b84ac875c1ff81d95b18ce8))
* rename library ([66a7760](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/66a776074721532a342f3f1051cd4076981d9acc))
* reset df index for each batch ([c12c8af](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/c12c8afdcfc2db5ddccffc62d66c4a82e2bcaa61))
* revise insert records method, pop old methods ([084c237](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/084c2374188b174841a8f42bfbf0b5d74724497a))
* revise insert_pdfs method, add _insert method ([a58f633](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/a58f6337c4dd2a6f9014c63ea74d2bb111b2701d))
* set datatypes for sql tables ([e3dc377](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/e3dc377cc47f9aca1d9da3ecaddcc358f4bbfe02))
* set up logging ([4a9ea77](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/4a9ea77a8f91607e8dcf19559df8d94f36857ab2))
* sql default action is insert or replace ([e2c3309](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/e2c33091ab3c8301cb500142bb9c3e50991da0e2))
* update db.py ([c0f9cf5](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/c0f9cf577d986763e2a26f9f95bf93d4903e8333))
* update he-alike params ([6571e1c](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/6571e1c16fc6cb567d4f2fe9072bed39a0e40e6a))
* update init, filename generation ([2b14767](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/2b14767037d303bcb3de9daa10944bdd01ba7833))
* update logging, docstrings ([b78cbb6](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/b78cbb6da45044a1a7e306e718d91ecf7dd9c584))
* use body_html for corpus content ([0e988bc](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/0e988bc8f54806cd1c589a4dc30bae7dc02c0669))
* use new utils, doc_tag methods ([26b28a6](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/26b28a649ee24ad81edfc293011cf519280ccee4))
* **util:** add convert methods ([86bfb91](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/86bfb91ecab85b8bed78a638878b84e81f2d74f3))
* **util:** add new modules ([326dc31](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/326dc3114f7941787d42f6d6768d0f9621da46d0))
* **util:** str_to_obj returns bytes ([0695be3](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/0695be317d5b25b7133e7f2529c6a72427981620))
* vert sentence id must be str ([328b82e](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/328b82e4a68e8c742e3a50c2508a6d0b0719fc77))


### Documentation

* add _version ([dc23e13](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/dc23e137a1e622e8d19697c9149dc85ec8bf9167))
* add release-please comment ([3368c0b](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/3368c0bd803484b47e74ba5b8d63ef41f11be2b3))
* fix Standardize versioning and releases [#8](https://github.com/Humanitarian-Encyclopedia/corpusama/issues/8) ([ee3a72c](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/ee3a72ced5d4c948382b4e291c02db9b29f2b573))
* readme ([41a2a50](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/41a2a50b2e9d04d67e1d7a8dea78bc194f4f7cf4))
* update docs ([5f32e0b](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/5f32e0bf012a305045f387f148ea289294193b50))
* update readme ([9009131](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/900913118df53849f82a58ede4ae3c74a953975e))
* update readme ([d523991](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/d52399124e62c456a05ca8297257cf2322534632))
* update readme ([0e9990e](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/0e9990e82e403e2a51fdb78cda79cdcdb4dd3d33))
* update readme, pyproject.toml ([aab7f82](https://github.com/Humanitarian-Encyclopedia/corpusama/commit/aab7f82306de3edf93c6a6da34724c84461c15a3))
