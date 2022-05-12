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
EVENT_PATH = f"{FILE_DIR}/event.json"
TIMESTAMP = int(datetime.now().timestamp())
JOB_ID = f"workflow-cluster-{TIMESTAMP}"


# event = {
#     "body": {
#         "JOB_ID": f"workflow-dev-core-vectorize-fail-pls-{TIMESTAMP}",
#         "JOB_TYPE": "sagemaker_processing",
#         "TIMESTAMP": TIMESTAMP,
#         "WORKFLOW_NAME": "core-vectorize",
#         "DEBUG": True,
#         "params": {
#             "dataset_id": "1341241234",
#             "n_clusters": 10,
#             "vector_fields": ["review_a_vector_"],
#             "cutoff": 0.75,
#             "clusteringType": "community-detection",
#             "authorizationToken": f"{os.environ["SUPPORT_ACTIVATION_TOKEN"]}",
#         },
#     }
# }

# event = {
#     "body": {
#         "JOB_ID": f"workflow-dev-mpnet-test-vectorize-{TIMESTAMP}",
#         "JOB_TYPE": "sagemaker_processing",
#         "TIMESTAMP": TIMESTAMP,
#         "WORKFLOW_NAME": "core-vectorize",
#         "DEBUG": True,
#         "params": {
#             "dataset_id": "test-vectorize",
#             "model_id": "clip",
#             "encode_type": "image",
#             "fields": ["product_image"],
#             "authorizationToken": f'{os.environ["SUPPORT_ACTIVATION_TOKEN"]}',
#         },
#     }
# }

event = {
    "body": {
        "job_type": "workflow",
        "compute_type": "sagemaker_processing",
        "compute_region": "ap-southeast-2",
        "workflow_name": "core-cluster",
        "dataset_id": "the-office-series",
        "authorizationToken": f'{os.environ["SUPPORT_ACTIVATION_TOKEN"]}',
        "params": {
            "n_clusters": 10,
            "vector_fields": ["episode_title_mpnet_vector_"],
            "cutoff": 0.75,
            "clusteringType": "community-detection",
        },
    }
}


WORKFLOW_S3_URIS = {}

# logging = logging.getlogging()

###################################################w############################
#   Application object                                                        #
###############################################################################


def handler(event, context={}):
    start = time.time()
    # body = json.loads(event["body"])
    body = event["body"]
    stage = event["stage"]
    region = event["region"]
    params = body["params"]

    NOTEBOOK_EXECUTION_ROLE = os.environ[
        "NOTEBOOK_EXECUTION_ROLE"
    ] = f"arn:aws:iam::701405094693:role/BasicExecuteNotebookRole-ap-southeast-2-{stage}"

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
    SUPPORT_ACTIVATION_TOKEN = os.environ["SUPPORT_ACTIVATION_TOKEN"]

    ## If not authToken in payload, load support
    if not params.get("authorizationToken"):
        params["authorizationToken"] = SUPPORT_ACTIVATION_TOKEN

    global WORKFLOW_S3_URIS
    if not WORKFLOW_S3_URIS:
        client = Client(SUPPORT_ACTIVATION_TOKEN)
        ds = client.Dataset("workflows-recipes")
        WORKFLOWS = ds.get_all_documents(filters=ds[f"s3_url"].exists())
        for w in WORKFLOWS:
            if w["s3_url"].get(stage):
                WORKFLOW_S3_URIS[w["_id"]] = w["s3_url"][stage]
            else:
                WORKFLOW_S3_URIS[w["_id"]] = w["s3_url"]["dev"]

    WORKFLOW_NAME = body.get("workflow_name")
    NOTEBOOK_PATH = WORKFLOW_S3_URIS.get(WORKFLOW_NAME)
    if not WORKFLOW_NAME or not NOTEBOOK_PATH:
        body = {
            **{"message": f"Workflow {WORKFLOW_NAME} not found or is not valid."},
            **body,
        }
        return return_response(response_code=500, body=body)

    if WORKFLOW_NAME not in [
        "core-vectorize",
        "core-cluster",
        "core-dr",
        "core-subclustering",
    ]:
        body = {
            **{
                "message": f"Workflow {WORKFLOW_NAME} not found or is not valid. Only core workflows supported atm, 'core-vectorize', 'core-cluster', 'core-dr', 'core-subclustering'"
            },
            **body,
        }
        return return_response(response_code=500, body=body)

    print(f"WORKFLOW_NAME: {WORKFLOW_NAME}")
    # print(f"EXECUTION_ROLE: {EXECUTION_ROLE}")

    try:
        if body["compute_type"] == "sagemaker_processing":
            EXECUTION_ROLE = os.environ["NOTEBOOK_EXECUTION_ROLE"]

            ## ProcessingName Cleaning
            dataset_id = body["dataset_id"]
            body[
                "job_id"
            ] = f"workflow-{stage}-{dataset_id}-{int(datetime.now().timestamp())}"
            JOB_ID_L = body["job_id"].replace("_", "-").split("-")
            WORKFLOW_DATASET_ID = "-".join(JOB_ID_L[1:-1])[:50]
            JOB_ID = "-".join([JOB_ID_L[0], WORKFLOW_DATASET_ID, JOB_ID_L[-1]])

            print(f"Invoking Sagemaker processing job {JOB_ID} with {EXECUTION_ROLE}")
            # print(NOTEBOOK_PATH)

            ## To overcome
            print(NOTEBOOK_PATH)
            sm_job = run.invoke(
                notebook=NOTEBOOK_PATH,
                stage=stage,
                region=region,
                image=f"sagemaker-run-notebook-{stage}",
                role=EXECUTION_ROLE,
                parameters={**{"JOB_ID": JOB_ID}, **params},
                upload_parameters=True,
            )
            if sm_job:
                response_code = 200
                body = {
                    **{"message": f"Sagemaker Processing job created for {JOB_ID}."},
                    **body,
                }

        # print("Wait for job to complete ...")

        # run.wait_for_complete(sm_job)
        end = time.time()
        print(f"{WORKFLOW_NAME} workflow took {end-start:.4}s ... ")

    except Exception as e:
        print(f"Error invoking job. {e}")
        response_code = 500
        body = {**{"message": str(e)}, **body}

    ## Masking creds
    # if body["params"].get("authorizationToken"):
    #     body["params"]["authorizationToken"] = "*" * len(
    #         body["params"]["authorizationToken"]
    #     )

    return return_response(response_code=response_code, body=body)


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
    global event
    event["stage"] = args.stage
    event["region"] = args.region
    if not args.poll:
        handler(event)
        json.dump(event, fp=open(EVENT_PATH, "w"), indent=4)

    event = json.loads(open(EVENT_PATH).read())
    if args.job_id:
        event["body"]["JOB_ID"] = args.job_id.strip()

    poll_handler(event)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--stage",
        default="dev",
        type=str,
        choices={"dev", "stg", "prd"},
        help="Stage Name",
    )
    parser.add_argument(
        "--region",
        help="AWS Region Name ",
        default="ap-southeast-2",
        choices=["ap-southeast-2", "us-east-1"],
    )
    parser.add_argument(
        "-p",
        "--poll",
        action="store_true",
        help="Run in poll mode - automatically polls status for last known job",
    )
    parser.add_argument(
        "-j", "--job-id", default=None, help="If you want to poll a specific job id"
    )
    args = parser.parse_args()
    main(args)
