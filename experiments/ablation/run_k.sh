#!/bin/bash

APPNAME=$1

TOPDIR=$(git rev-parse --show-toplevel)

EXPERIMENTSDIR=${TOPDIR}/experiments

mkdir -p ${EXPERIMENTSDIR}/ablation/results/debloated
mkdir -p ${EXPERIMENTSDIR}/ablation/results/baseline
cp ${EXPERIMENTSDIR}/debloat/results/baseline/${APPNAME}.csv ${EXPERIMENTSDIR}/ablation/results/baseline/${APPNAME}.csv

k=(1 5 10 15 20 30 40 50)

for i in "${k[@]}"; do
    echo "Varying k: ${i} - running experiment for ${APPNAME}"
    python ${EXPERIMENTSDIR}/ablation.py --single-app ${APPNAME} -k ${i}
done