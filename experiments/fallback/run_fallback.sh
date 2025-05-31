#!/bin/bash

TOPDIR=$(git rev-parse --show-toplevel)

applications=(
    "dna-visualization" 
    # "lightgbm"
    # "spacy"
    # "huggingface"
)

for APPNAME in "${applications[@]}"; do
    echo "Replacing function handler for $APPNAME (in order to trigger fallback with specific input event)"
    mv $TOPDIR/serverless-bench/examples/$APPNAME/lambda_function.py $TOPDIR/experiments/fallback/$APPNAME/lambda_function.py.bak
    cp $TOPDIR/experiments/fallback/lambda_function.py $TOPDIR/serverless-bench/examples/$APPNAME/lambda_function.py

    echo "Create debloated function with fallback for $APPNAME"
    cd $TOPDIR
    python experiments/fallback.py --action create-debloat-with-fallback --single-app $APPNAME

    echo "Recover function handler for $APPNAME"
    mv $TOPDIR/serverless-bench/examples/$APPNAME/lambda_function.py.bak $TOPDIR/serverless-bench/examples/$APPNAME/lambda_function.py

    echo "Running experiment for $APPNAME"
    python experiments/fallback.py --action run-cold-cold --single-app $APPNAME
    python experiments/fallback.py --action run-cold-warm --single-app $APPNAME
    python experiments/fallback.py --action run-warm-cold --single-app $APPNAME
    python experiments/fallback.py --action run-warm-warm --single-app $APPNAME

    echo "Done with $APPNAME"
    echo "--------------------------------------------------"
done
echo "All fallback experiments completed."
