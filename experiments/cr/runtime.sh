#!/bin/bash

if [ "$CHECKPOINT_ENV" = "off" ]; then
    python lambda_function.py
else
    python slambda.py
    python restore.py
    CHECKPOINT_SIZE=$(du -sh /var/task/checkpoint | awk '{print $1}')
    echo "Checkpoint size: $CHECKPOINT_SIZE"
    echo "$CHECKPOINT_SIZE" >> "/var/task/output/checkpoint_size_debloat_${DEBLOAT_ENV}.txt"
fi