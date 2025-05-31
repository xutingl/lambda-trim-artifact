#!/bin/bash

TOPDIR=$(git rev-parse --show-toplevel)

applications=(
    "dna-visualization" 
    "tensorflow" 
    "skimage" 
    "lxml"
    "epub-pdf"
    "scikit"
    "pandas"
    "spacy" 
    "lightgbm" 
    "markdown" 
    "chdb-olap" 
    "jsym"
    "textblob"
    "igraph"
    "resnet"
    "wine"
    "image-resize"
    "shapely-numpy" 
    "huggingface" 
    "qiskit-nature"
)

for app in "${applications[@]}"; do
    echo "Running experiment for $app"
    "${TOPDIR}"/experiments/cr/run.sh "${app}"
done