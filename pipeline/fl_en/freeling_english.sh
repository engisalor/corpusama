#!/bin/bash
set -euo pipefail

THISDIR=$(readlink -f $(dirname ${BASH_SOURCE[0]}))
UNINORM="$THISDIR/uninorm_4.py"
BASE="$THISDIR/base_pipeline.py"

$UNINORM | $BASE
