ARG BASE_IMAGE=need_an_image
FROM $BASE_IMAGE

# ENV JUPYTER_ENABLE_LAB yes
ENV PYTHONUNBUFFERED=TRUE
VOLUME [ "/root/.aws" ]

COPY requirements.txt /tmp/requirements.txt
RUN pip install -U pip
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# VOLUME [ "/opt/app" ]

# ENV PATH="/opt/program:${PATH}"

# # Set up the program in the image
# COPY run_notebook execute.py /opt/program/
# ENTRYPOINT ["/bin/bash"]
ADD execute.py /
ENTRYPOINT ["python3", "/execute.py"]

# because there is a bug where you have to be root to access the directories
USER root

 