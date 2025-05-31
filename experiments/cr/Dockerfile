FROM spyrospav/criu-debloat:latest

ARG APPNAME
ARG DEBLOAT="off"
ARG CHECKPOINT="off"

ENV DEBLOAT_ENV=${DEBLOAT}
ENV CHECKPOINT_ENV=${CHECKPOINT}

ENV TZ=US/Eastern
# Set up the working directory
COPY serverless-bench/examples/${APPNAME}/ ${LAMBDA_TASK_ROOT}/

# Install app dependencies
RUN pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt

# if APPNAME="dna-visualization", copy gene1.txt and gene2.txt to dna-visualization/
RUN if [[ "$APPNAME" = "dna-visualization" ]]; then\ 
    mkdir dna-visualization \
    && cp gene1.txt gene2.txt dna-visualization/; fi

    # Specific installations for chdb-olap
RUN if [[ "$APPNAME" = "chdb-olap" ]]; then \
    echo "TZ=US/Eastern" >> /root/.bashrc; \
    fi
# Specific installations for lightgbm
RUN if [[ "$APPNAME" = "lightgbm" ]]; then \
    dnf install -y gcc gcc-c++; \
    fi

RUN if [[ "$APPNAME" = "spacy" ]]; then \
    python -m spacy download en_core_web_sm; \
    fi
# Run debloating
RUN if [[ "$DEBLOAT" = "on" ]]; then debloat -k 20 --no-pycg lambda.py; fi

# Create a new lambda function that checkpoints the original lambda function
RUN cp ${LAMBDA_TASK_ROOT}/lambda.py ${LAMBDA_TASK_ROOT}/lambda_criu.py \
    && echo $'\n' >> ${LAMBDA_TASK_ROOT}/lambda_criu.py \
    && echo "from criuwrap import checkpoint" >> ${LAMBDA_TASK_ROOT}/lambda_criu.py \
    && echo "handler = checkpoint(handler)" >> ${LAMBDA_TASK_ROOT}/lambda_criu.py

COPY experiments/cr/ ${LAMBDA_TASK_ROOT}/

RUN cat stub.py >> ${LAMBDA_TASK_ROOT}/lambda_function.py

RUN mkdir -p output

ENTRYPOINT [ "/bin/sh", "runtime.sh" ]