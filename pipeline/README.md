# Corpus creation pipelines

Pipelines to produce vertical content from text files.

## Execution

To process a text file, run `pipeline/run.sh` with the desired arguments, e.g.:

```bash
bash pipeline/run.sh ske_es t pipeline/ske_es/sample_es.txt
```

Positional arguments:

- $1 the pipeline to use (corresponds to a subdirectory in `pipeline/`)
- $2 whether to compress the output file: either `t` (for `.vert.xz`) or `f` (for `.vert`)
- $3 the text file to process (can include XML tags w/ corpus structure attributes)

## Batch execution

To process multiple text files in parallel, use:

```bash
# add a line for each additional file, up to the device's number of CPUs-1
(trap 'kill 0' SIGINT; \
bash pipeline/run.sh PIPELINE COMPRESS FILE0 &
bash pipeline/run.sh PIPELINE COMPRESS FILE1 &
wait)
```

## Licenses

Subdirectories with a `ske_` prefix are from [Sketch Engine](https://www.sketchengine.eu/) under [AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html), [MPL](https://www.mozilla.org/MPL/2.0), and/or other pertinent licenses. See their [bibliography](https://www.sketchengine.eu/bibliography-of-sketch-engine/) and [website](https://corpus.tools/) with open-source corpus tools.
