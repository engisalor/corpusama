#!/bin/bash
# Usage example (run from repo base directory):
# cat text.txt | sketchengine/freeling_spanish_v6.sh > text.vert
set -euo pipefail

THISDIR=$(readlink -f $(dirname ${BASH_SOURCE[0]}))
UNINORM="$THISDIR/uninorm_4"
BASE="$THISDIR/base_pipeline_v6.py"
GUESSER="$THISDIR/gennum_guess.py"

$UNINORM | $BASE | $GUESSER
