FROM public.ecr.aws/lambda/python:3.10

ARG APPNAME

ARG TOP_K="10"

ARG SCORING="cost"

ARG WITH_FALLBACK="False"

ARG FALLBACK_FUNCTION_NAME=${APPNAME}

COPY serverless-bench/examples/${APPNAME}/ ${LAMBDA_TASK_ROOT}/

# RUN yum update -y

# # Get the EPEL repository
# RUN yum install -y https://archives.fedoraproject.org/pub/archive/epel/7/x86_64/Packages/e/epel-release-7-14.noarch.rpm \
#     && yum install -y epel-release \
#     && yum install -y git

RUN yum install -y git

# Install ltrim
ARG LTRIM_PATH=${LAMBDA_TASK_ROOT}/lambda-trim
COPY lambda-trim ${LAMBDA_TASK_ROOT}/lambda-trim
RUN cd $LTRIM_PATH && \
    pip install -e . &&\
    cd ~

# Specific installations for image-resize
RUN if [ "${APPNAME}" = "image-resize" ]; then \
    yum install -y ImageMagick-devel; \
    fi

# Specific installations for lightgbm
RUN if [ "${APPNAME}" = "lightgbm" ]; then \
    yum install -y gcc gcc-c++ libgomp; \
    fi

# Specific installations for chdb-olap
RUN if [ "${APPNAME}" = "chdb-olap" ]; then \
    echo "TZ=US/Eastern" >> /root/.bashrc; \
    fi

# Specific installations for ffmpeg
RUN if [ "${APPNAME}" = "ffmpeg" ]; then \
    /var/task/install_ffmpeg_centos.sh; \
    fi

RUN pip install -r requirements.txt


# Specific installations for spaCy
RUN if [ "${APPNAME}" = "spacy" ]; then \
    python -m spacy download en_core_web_sm; \
    fi


# Run debloating
RUN debloat lambda.py -k ${TOP_K} --scoring ${SCORING}

# Clean up
RUN rm -rf __pycache__
RUN rm -rf tmp

RUN if [ "${APPNAME}" = "resnet" ]; then \
    rm resnet50.pth; \
    rm tesla.jpg; \
    rm imagenet_class_index.json; \
    rm -rf tmp; \
    fi

# Fall-back mechanism: if WITH_FALLBACK is True, FALLBACK_FUNCTION_NAME is required
COPY docker/lambda_to_replace.py ${LAMBDA_TASK_ROOT}/lambda_to_replace.py
RUN if [ ${WITH_FALLBACK} == True ]; then \
    mv ${LAMBDA_TASK_ROOT}/lambda_function.py ${LAMBDA_TASK_ROOT}/original_lambda_function.py; \
    mv ${LAMBDA_TASK_ROOT}/lambda_to_replace.py ${LAMBDA_TASK_ROOT}/lambda_function.py; \
    fi
    
CMD [ "lambda_function.handler" ]