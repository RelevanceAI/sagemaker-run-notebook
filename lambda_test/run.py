#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#####
# Author: Charlene Leong charleneleong84@gmail.com
# Created Date: Wednesday, April 20th 2022, 2:51:50 pm
# Last Modified: Thursday, April 21st 2022,5:30:08 pm
#####

import os
import sagemaker_run_notebook as run
from relevanceai import Client

from pathlib import Path
import json
import time
import logging

from datetime import datetime


tags_metadata = []

event = {
    "body": {
        "JOB_ID": f"workflow-cluster-{int(datetime.now().timestamp())}",
        "JOB_TYPE": "sagemaker_processing",
        "WORKFLOW_NAME": "core-cluster",
        "CONFIG": {
            "authorizationToken": "3a4b969f4d5fae6f850e:NjJJRzEzNEI4VlFEeXpMVG42Z3Q6UldUeDYxUlJTVFdoNjRWaGVwM25Vdw:us-east-1:JBQRqahx3jgp7ZsIq6sp2jtUoZJ3",
            "dataset_id": "basic_subclustering",
        },
    }
}


NOTEBOOK_EXECUTION_ROLE = os.environ[
    "NOTEBOOK_EXECUTION_ROLE"
] = "arn:aws:iam::701405094693:role/BasicExecuteNotebookRole-ap-southeast-2"
WORKFLOW_S3_URIS = {}

# logging = logging.getlogging()

###################################################w############################
#   Application object                                                        #
###############################################################################


def handler(event, context: dict = {}):
    # body = json.loads(event["body"])
    body = event["body"]
    config = body["CONFIG"]
    json.dumps(body, indent=2)
    logging_level = logging.DEBUG if config.get("DEBUG") else logging.INFO
    # logging.setLevel(level=logging_level)
    logging.basicConfig(level=logging_level)

    if os.getenv("SUPPORT_ACTIVATION_TOKEN"):
        client = Client(os.getenv("SUPPORT_ACTIVATION_TOKEN"))
        ds = client.Dataset("workflows-recipes")
        WORKFLOWS = ds.get_all_documents()
        WORKFLOW_S3_URIS = {w["_id"]: w["s3_url"] for w in WORKFLOWS if w.get("s3_url")}

    WORKFLOW_NAME = body["WORKFLOW_NAME"]
    EXECUTION_ROLE = os.environ["NOTEBOOK_EXECUTION_ROLE"]
    NOTEBOOK_PATH = WORKFLOW_S3_URIS.get(WORKFLOW_NAME)

    logging.info(f"WORKFLOW_NAME: {WORKFLOW_NAME}")
    logging.info(f"EXECUTION_ROLE: {EXECUTION_ROLE}")

    try:
        if body["JOB_TYPE"] == "sagemaker_processing":
            print()
            logging.info(f'Invoking Sagemaker processing job {body["JOB_ID"]}')
            print({**{"JOB_ID": body["JOB_ID"]}, **config})
            sm_job = run.invoke(
                # notebook="",
                input_path=NOTEBOOK_PATH,
                role=EXECUTION_ROLE,
                parameters={**{"JOB_ID": body["JOB_ID"]}, **config},
            )
            print(f"Invoked")
            if sm_job:
                response_code = 200

            logging.info("Wait for job to complete ...")
            start = time.time()
            run.wait_for_complete(sm_job)
            end = time.time()

            logging.info(f"{WORKFLOW_NAME} workflow took {end-start:.4}s ... ")
    except Exception as e:
        response_code = 500
        raise ValueError(f"{e}")
    response = {
        "statusCode": response_code,
        # "headers": {
        #     "x-custom-header" : "my custom header value"
        # },
        "body": body,
    }
    json.dumps(response, indent=2)
    return response


handler(event)
