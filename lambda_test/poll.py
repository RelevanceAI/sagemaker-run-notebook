#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#####
# Author: Charlene Leong charleneleong84@gmail.com
# Created Date: Wednesday, April 20th 2022, 2:51:50 pm
# Last Modified: Thursday, April 21st 2022,5:30:08 pm
#####

import argparse
import os

from pathlib import Path
from pprint import pprint
import json


from datetime import datetime, timedelta, timezone
import json
import pytz

utc = pytz.UTC

# import sagemaker
import boto3
import uuid
import logging

# SM client
sm_client = boto3.client("sagemaker")
JOB_LIMIT = 100
###################################################w############################
#   Application object                                                        #
###############################################################################

FILE_DIR = Path(__file__).parent
EVENT_PATH = f"{FILE_DIR}/event.json"


def handler(event, context={}):

    #
    body = event["body"]
    config = body["CONFIG"]

    logging_level = logging.DEBUG if config.get("DEBUG") else logging.INFO
    # logging.setLevel(level=logging_level)
    logging.basicConfig(level=logging_level)

    logging.info(json.dumps(body, indent=2))

    if body["JOB_TYPE"] == "sagemaker_processing":
        ## ProcessingName Cleaning
        JOB_ID_L = body["JOB_ID"].replace("_", "-").split("-")
        WORKFLOW_DATASET_ID = "-".join(JOB_ID_L[1:-1])[:50]
        JOB_ID = "-".join([JOB_ID_L[0], WORKFLOW_DATASET_ID, JOB_ID_L[-1]])
        print(JOB_ID)

        job_status, job_message = check_sm_job_status(
            job_id=JOB_ID, timestamp=body["TIMESTAMP"]
        )
        if not job_status:
            response_code = 500
            job_message = {
                "message": f"Job Id {body['JOB_ID']} does not exist in Sagemaker Processing jobs."
            }
            body = {**job_message, **body}
        if job_status == "Failed":
            response_code = 500
            body = {**job_message, **body}
        else:
            response_code = 200
            body = {**job_message, **body}

    # response = sm_client.describe_processing_job(
    #     NameContains="workflows",
    #     CreationTimeAfter=dt_last_half_hour,
    #     MaxResults=JOB_LIMIT,
    #     StatusEquals="InProgress",
    # )

    response = {
        "statusCode": response_code,
        # "headers": {
        #     "x-custom-header" : "my custom header value"
        # },
        "body": body,
    }
    if body["CONFIG"].get("authorizationToken"):
        body["CONFIG"]["authorizationToken"] = "*" * len(
            body["CONFIG"]["authorizationToken"]
        )
    logging.info(json.dumps(response, indent=2))

    return response


def days_hours_minutes_seconds(td):
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    seconds += td.microseconds / 1e6
    return td.days, hours, minutes, round(seconds, 2)


def check_sm_job_status(job_id: str, timestamp: str):
    # aest = dateutil.tz.gettz("Australia/Sydney")
    # dt_last_half_hour = datetime.now(timezone.utc) - timedelta(minutes=30)

    # response = sm_client.list_processing_jobs(
    #     NameContains=str(timestamp),
    #     # CreationTimeAfter=dt_last_half_hour,
    #     MaxResults=JOB_LIMIT,
    #     # StatusEquals='InProgress'
    # )["ProcessingJobSummaries"]
    try:
        job = sm_client.describe_processing_job(ProcessingJobName=str(job_id))
    except Exception as e:
        print(e)
        print(f"Job Id {job_id} does not exist in Sagemaker Processing jobs.")
        job = None

    if job:
        created_time = job["CreationTime"].replace(tzinfo=utc)
        td = datetime.now(timezone.utc) - created_time
        d, h, m, s = days_hours_minutes_seconds(td)

        job_message = {
            "JOB_STATUS": job["ProcessingJobStatus"],
            "JOB_MESSAGE": f'Job {job["ProcessingJobStatus"]} {d} days, {h} hours, {m} min, {s} secs ago.',
        }
        if job["ProcessingJobStatus"] == "Failed":
            job_message["JOB_MESSAGE"] += f'\n{job.get("ExitMessage")}'
        return job["ProcessingJobStatus"], job_message
    else:

        # job_messages = []
        # for job in response:
        #     job_messages.append( {
        #         "JOB_STATUS": job["ProcessingJobStatus"],
        #         "JOB_MESSAGE": f'Job {job["ProcessingJobStatus"]} {d} days, {h} hours, {m} min, {s} secs ago.',
        #     })

        # job_message = {
        #     "JOB_STATUS": f"{len(response)} jobs found",
        #     "JOB_MESSAGE": job_messages,
        # }
        # return (None, job_message)
        return (None, None)


def main(args):
    event = json.loads(open(EVENT_PATH).read())
    event["stage"] = args.stage
    handler(event)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--stage",
        default="dev",
        type=str,
        choices={"dev", "stg", "prd"},
        help="Run debug mode",
    )
    args = parser.parse_args()
    main(args)
