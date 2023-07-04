#!/bin/bash
set -euo pipefail

THISDIR=$(readlink -f $(dirname ${BASH_SOURCE[0]}))
UNINORM="$THISDIR/french/uninorm_french"
BASE="$THISDIR/french/base_pipeline_v3.py"
GUESSER="$THISDIR/french/gennum_guess.py"

$UNINORM | $BASE | $GUESSER
