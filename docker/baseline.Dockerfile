# For 3.12 and up, use yum install. For 3.10 use yum install.
FROM public.ecr.aws/lambda/python:3.10

ARG APPNAME

COPY serverless-bench/examples/${APPNAME}/ ${LAMBDA_TASK_ROOT}/

# RUN yum update -y

# Get the EPEL repository
# RUN yum install -y https://archives.fedoraproject.org/pub/archive/epel/7/x86_64/Packages/e/epel-release-7-14.noarch.rpm \
#     && yum install -y epel-release \
#     && yum install -y git

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


CMD [ "lambda_function.handler" ]