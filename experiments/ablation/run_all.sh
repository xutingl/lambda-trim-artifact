#!/bin/bash

EXPERIMENT=$1

APPS=(
    "dna-visualization"
    "lightgbm"
    "spacy"
)

for APPNAME in "${APPS[@]}"; do
    TOPDIR=$(git rev-parse --show-toplevel)

    EXPERIMENTSDIR=${TOPDIR}/experiments/ablation

    if [ "$EXPERIMENT" == "k" ]; then
        echo "Running varying k experiments for ${APPNAME}"
        "$EXPERIMENTSDIR"/run_k.sh "${APPNAME}"
    elif [ "$EXPERIMENT" == "scoring" ]; then
        echo "Running scoring_method experiments for ${APPNAME}"
        "$EXPERIMENTSDIR"/run_scoring.sh "${APPNAME}"
    else 
        echo "Unknown experiment type: ${EXPERIMENT}"
        exit 1
    fi

done