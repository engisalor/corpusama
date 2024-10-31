#!/bin/bash

source $PWD/.venv/bin/activate

if [ $# -ne 2 ]; then
    echo "Usage: $0 <START_DATE> <END_DATE> (both in YYYY-MM-DD format)"
    exit 1
fi

echo "... get and process source data"
python3 rw_corpora_update.py "${1}" "${2}"
echo "... convert source files to .conllu (run Stanza NLP)"
ES_FILES=$(find -name "reliefweb_es*.txt")
FR_FILES=$(find -name "reliefweb_fr*.txt")
EN_FILES=$(find -name "reliefweb_en*.txt")
python3 ./pipeline/stanza/base_pipeline.py to-conll -l es $ES_FILES
python3 ./pipeline/stanza/base_pipeline.py to-conll -l fr $FR_FILES
python3 ./pipeline/stanza/base_pipeline.py to-conll -l en $EN_FILES
echo "... convert files to .vert and compress"
CONLLU_FILES=$(find -name "reliefweb_*.txt.conllu")
python3 ./pipeline/stanza/base_pipeline.py conll-to-vert --no-compress $CONLLU_FILES
EN_VERT_FILES=$(find -name "reliefweb_en*.vert")
FR_VERT_FILES=$(find -name "reliefweb_fr*.vert")
ES_VERT_FILES=$(find -name "reliefweb_es*.vert")
echo "... base_pipeline completed"
echo "... start secondary pipeline"
# NOTE: the secondary pipeline is optional but adds more information
# to the corpora: language identification and more detailed corpus
# structures (s.lang, doc.ref, docx).
echo "... run sentence-level language identification"
python3 ./pipeline/stanza/secondary_pipeline.py langid $ES_VERT_FILES
python3 ./pipeline/stanza/secondary_pipeline.py langid $FR_VERT_FILES
python3 ./pipeline/stanza/secondary_pipeline.py langid $EN_VERT_FILES
# WARNING: the following cmds are destructive with the --clear flag:
# create a backup of the vertical files if success is uncertain.
echo "... update structures"
python3 ./pipeline/stanza/secondary_pipeline.py main $ES_VERT_FILES --uuid --clear --langid
python3 ./pipeline/stanza/secondary_pipeline.py main $FR_VERT_FILES --uuid --clear --langid
python3 ./pipeline/stanza/secondary_pipeline.py main $EN_VERT_FILES --uuid --clear --langid
echo "... rw_corpora_update.sh completed"
