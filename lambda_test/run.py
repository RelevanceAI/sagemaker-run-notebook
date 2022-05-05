#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#####
# Author: Charlene Leong charleneleong84@gmail.com
# Created Date: Wednesday, April 20th 2022, 2:51:50 pm
# Last Modified: Thursday, April 21st 2022,5:30:08 pm
#####

import argparse
import os
import sagemaker_run_notebook as run
from relevanceai import Client
import json

from pathlib import Path
import json
import time
import logging

from datetime import datetime

from lambda_test.poll import handler as poll_handler


tags_metadata = []


FILE_DIR = Path(__file__).parent
EVENT_PATH = f'{FILE_DIR}/event.json'
JOB_ID = f"workflow-cluster-{int(datetime.now().timestamp())}"

event = {
    "body": {
        "JOB_ID": JOB_ID,
        "JOB_TYPE": "sagemaker_processing",
        "WORKFLOW_NAME": "core-cluster",
        "CONFIG": {
            "authorizationToken": "3a4b969f4d5fae6f850e:NjJJRzEzNEI4VlFEeXpMVG42Z3Q6UldUeDYxUlJTVFdoNjRWaGVwM25Vdw:us-east-1:JBQRqahx3jgp7ZsIq6sp2jtUoZJ3",
            "dataset_id": "basic_subclustering",
            "vector_fields": ["product_title_clip_vector_"],
            "n_clusters": 20,
            "clusteringType": "kmeans"
        },
    }
}

json.dump(event, fp=open(EVENT_PATH, "w"), indent=4)


WORKFLOW_S3_URIS = {}

# logging = logging.getlogging()

###################################################w############################
#   Application object                                                        #
###############################################################################


def handler(event, context={}):
    
    # body = json.loads(event["body"])
    body = event['body']
    stage = event['stage']
    config = body["CONFIG"]

    NOTEBOOK_EXECUTION_ROLE = os.environ["NOTEBOOK_EXECUTION_ROLE"] = f"arn:aws:iam::701405094693:role/BasicExecuteNotebookRole-ap-southeast-2-{stage}"

    print(json.dumps(body, indent=2))

    # global SUPPORT_ACTIVATION_TOKEN
    # if not SUPPORT_ACTIVATION_TOKEN:
    #     SUPPORT_ACTIVATION_TOKEN = get_secret_value(
    #         secret_id=os.environ["SUPPORT_TOKEN_SECRET_ID"]
    #     )
    #     if "ERROR" in SUPPORT_ACTIVATION_TOKEN:
    #         body = {
    #             **{"message": SUPPORT_ACTIVATION_TOKEN},
    #             **body,
    #         }
    #         return return_response(response_code=500, body=body)
    SUPPORT_ACTIVATION_TOKEN = os.environ['SUPPORT_ACTIVATION_TOKEN']

    ## If not authToken in payload, load support
    if not config.get("authorizationToken"):
        config["authorizationToken"] = SUPPORT_ACTIVATION_TOKEN

    global WORKFLOW_S3_URIS
    if not WORKFLOW_S3_URIS:
        client = Client(SUPPORT_ACTIVATION_TOKEN)
        ds = client.Dataset("workflows-recipes")
        WORKFLOWS = ds.get_all_documents(filters=ds[f"s3_url"].exists())
        for w in WORKFLOWS:
            if w["s3_url"].get(stage):
                WORKFLOW_S3_URIS[w["_id"]] = w["s3_url"][stage] 
            else:
                WORKFLOW_S3_URIS[w["_id"]] = w["s3_url"]['dev'] 


    WORKFLOW_NAME = body.get("WORKFLOW_NAME")
    NOTEBOOK_PATH = WORKFLOW_S3_URIS.get(WORKFLOW_NAME)
    if not WORKFLOW_NAME or not NOTEBOOK_PATH:
        body = {
            **{"message": f"Workflow {WORKFLOW_NAME} not found or is not valid."},
            **body,
        }
        return return_response(response_code=500, body=body)

    print(f"WORKFLOW_NAME: {WORKFLOW_NAME}")
    # print(f"EXECUTION_ROLE: {EXECUTION_ROLE}")

    try:
        if body["JOB_TYPE"] == "sagemaker_processing":
            EXECUTION_ROLE = os.environ["NOTEBOOK_EXECUTION_ROLE"]
            print(
                f'Invoking Sagemaker processing job {body["JOB_ID"]} with {EXECUTION_ROLE}'
            )
            # print(NOTEBOOK_PATH)
            sm_job = run.invoke(
                input_path=NOTEBOOK_PATH,
                stage=stage,
                image=f'sagemaker-run-notebook-{stage}',
                role=EXECUTION_ROLE,
                parameters={**{"JOB_ID": body["JOB_ID"]}, **config},
                upload_parameters=True
            )
            if sm_job:
                response_code = 200
                body = {
                    **{
                        "message": f'Sagemaker Processing job created for {body["JOB_ID"]}.'
                    },
                    **body,
                }

        # print("Wait for job to complete ...")
        # start = time.time()
        # run.wait_for_complete(sm_job)
        # end = time.time()
        # print(f"{WORKFLOW_NAME} workflow took {end-start:.4}s ... ")

    except Exception as e:
        print(f"Error invoking job. {e}")
        response_code = 500
        body = {**{"message": str(e)}, **body}

    ## Masking creds
    if body["CONFIG"].get("authorizationToken"):
        body["CONFIG"]["authorizationToken"] = "*" * len(
            body["CONFIG"]["authorizationToken"]
        )

def return_response(response_code: int, body: dict) -> dict:
    response = {
        "statusCode": response_code,
        "headers": {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        },
        "body": body,
    }
    print(json.dumps(response, indent=2))
    response["body"] = json.dumps(body)
    return response

def main(args):
    event['stage'] = args.stage
    handler(event)
    poll_handler(event)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--stage", default='dev', type=str, choices={"dev", "stg", "prd"}, help="Run debug mode")
    args = parser.parse_args()
    main(args)