#!/bin/bash

APPS=(
    "dna-visualization"
    "lightgbm"
    "spacy"
)

for APPNAME in "${APPS[@]}"; do
    TOPDIR=$(git rev-parse --show-toplevel)

    EXPERIMENTSDIR=${TOPDIR}/experiments/ablation

    echo "Running varying k experiments for ${APPNAME}"
    # $EXPERIMENTSDIR/run_k.sh ${APPNAME}

    echo "Running scoring_method experiments for ${APPNAME}"
    $EXPERIMENTSDIR/run_scoring.sh ${APPNAME}

done