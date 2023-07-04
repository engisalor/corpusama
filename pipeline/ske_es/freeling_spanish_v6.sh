#!/bin/bash
# Usage examples: (always run from repo base directory)
### SINGLE FILE
# cat reliefweb_es.1.txt | pipeline/ske_es/freeling_spanish_v6.sh | xz -z > reliefweb_es.1.vert.xz


set -euo pipefail

THISDIR=$(readlink -f $(dirname ${BASH_SOURCE[0]}))
UNINORM="$THISDIR/uninorm_4.py"
BASE="$THISDIR/base_pipeline_v6.py"
GUESSER="$THISDIR/gennum_guess.py"

$UNINORM | $BASE | $GUESSER
