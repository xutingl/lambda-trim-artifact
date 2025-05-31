#!/bin/bash

# get TOPDIR with git rev-parse

TOPDIR=$(git rev-parse --show-toplevel)
CR_EXPERIMENTS_DIR="$TOPDIR/experiments/cr"

mkdir -p $CR_EXPERIMENTS_DIR/output

for DEBLOAT in "off" "on"; do
    for CHECKPOINT in "off" "on"; do
        sudo docker build -t debloat --build-arg APPNAME=$1 --build-arg DEBLOAT=$DEBLOAT --build-arg CHECKPOINT=$CHECKPOINT -f $CR_EXPERIMENTS_DIR/Dockerfile .

        echo "Running with DEBLOAT=$DEBLOAT and CHECKPOINT=$CHECKPOINT"

        for _ in $(seq 1 100); do
            sudo docker run --rm -v $(pwd)/experiments/cr/$1:/var/task/output --privileged debloat
        done

    done
done