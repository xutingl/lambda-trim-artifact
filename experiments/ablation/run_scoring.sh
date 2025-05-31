#!/bin/bash

APPNAME=$1

TOPDIR=$(git rev-parse --show-toplevel)

EXPERIMENTSDIR=${TOPDIR}/experiments

mkdir -p ${EXPERIMENTSDIR}/ablation/results/debloated
mkdir -p ${EXPERIMENTSDIR}/ablation/results/baseline
cp ${EXPERIMENTSDIR}/debloat/results/baseline/${APPNAME}.csv ${EXPERIMENTSDIR}/ablation/results/baseline/${APPNAME}.csv

METHODS=(
    "cost"
    "time"
    "random"
    "memory"
)

for m in "${METHODS[@]}"; do
    echo "Scoring: ${m} - running experiment for ${APPNAME}"
    python ${EXPERIMENTSDIR}/ablation.py --single-app ${APPNAME} --scoring ${m}
done