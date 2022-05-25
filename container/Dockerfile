ARG BASE_IMAGE="python:3.7-slim-buster"
FROM $BASE_IMAGE

# ENV JUPYTER_ENABLE_LAB yes
ENV PYTHONUNBUFFERED=TRUE
VOLUME [ "/root/.aws" ]

COPY requirements.txt /tmp/requirements.txt
RUN pip install -U pip
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN ipython kernel install --name "python3" --user

# VOLUME [ "/opt/app" ]

# ENV PATH="/opt/program:${PATH}"

# # Set up the program in the image
# COPY run_notebook execute.py /opt/program/
# ENTRYPOINT ["/bin/bash"]
ADD execute.py /
ENTRYPOINT ["python3", "/execute.py"]

# because there is a bug where you have to be root to access the directories
USER root

 
