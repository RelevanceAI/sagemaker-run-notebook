#!/usr/bin/env python

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from __future__ import print_function

import os
import json
from pathlib import Path
import sys
import traceback
from urllib.parse import urlparse

import boto3
import botocore

import papermill

input_var = "PAPERMILL_INPUT"
output_var = "PAPERMILL_OUTPUT"
params_var = "PAPERMILL_PARAMS"

## Local testing - 
PAPERMILL_PARAMS ="""{
                "dataset_id": "1341241234",
                "n_clusters": 10,
                "vector_fields": [
                    "review_a_vector_"
                ],
                "cutoff": 0.75,
                "clusteringType": "community-detection",
                "region": "us-east-1",
                "project": "452d7499c071ab48e4e5",
                "api_key": "WTBHYXJYNEJoeGxuNEFNVTVPNXg6VTc2UFVHUmtTMUd2MFMzb05HRUZFdw",
                "authorizationToken": "452d7499c071ab48e4e5:WTBHYXJYNEJoeGxuNEFNVTVPNXg6VTc2UFVHUmtTMUd2MFMzb05HRUZFdw:us-east-1:nZmokoHGVSRXtDXauVWrrbyEsBe2"
}"""
def run_notebook():
    try:
        if not os.getenv(input_var):
            from dotenv import load_dotenv
            load_dotenv()

        notebook_path = os.environ[input_var]
        output_notebook = os.environ[output_var]

        if not os.getenv(params_var):
            params = json.loads(PAPERMILL_PARAMS)
        else:
            params = json.loads(os.environ[params_var])

        notebook_dir = os.path.dirname(notebook_path)
        notebook_file = os.path.basename(notebook_path)

        # If the user specified notebook path in S3, run with that path.
        if notebook_path.startswith("s3://"):
            print("Downloading notebook {}".format(notebook_path))
            o = urlparse(notebook_path)
            bucket = o.netloc
            key = o.path[1:]

            s3 = boto3.resource("s3")

            try:
                s3.Bucket(bucket).download_file(key, "/tmp/" + notebook_file)
                notebook_dir = "/tmp"
            except botocore.exceptions.ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    print("The notebook {} does not exist.".format(notebook_path))
                raise
            print("Download complete")

        if params.get('S3_PATH'):
            params_path = params.get('S3_PATH')
            # params_dir = os.path.dirname(params_path)
            params_file = os.path.basename(params_path)

            print("Downloading params file {}".format(params_path))
            o = urlparse(params_path)
            bucket = o.netloc
            key = o.path[1:]

            s3 = boto3.resource("s3")
            try:
                s3.Bucket(bucket).download_file(key, "/tmp/" + params_file)
                params_dir = "/tmp"
            except botocore.exceptions.ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    print("The params {} does not exist.".format(params_path))
                raise
            print("Download complete")

            os.chdir(params_dir)
            params = json.loads(open(params_file).read())

        os.chdir(notebook_dir)

        print("Executing {} with output to {}".format(notebook_file, output_notebook))
        
        print(f"Notebook params = {json.dumps(params, indent=2)}")
        
        ## Mask creds
        if params.get("authorizationToken"):
           params["authorizationToken"] = "*" * len(
                params["authorizationToken"]
            )
        papermill.execute_notebook(
            notebook_file, output_notebook, params, kernel_name="python3"
        )
        print("Execution complete")

    except Exception as e:
        # Write out an error file. This will be returned as the failureReason in the
        # DescribeProcessingJob result.
        trc = traceback.format_exc()

        error_message = "Exception during processing: " + str(e) + "\n" + trc
        print(str(e))
        print(str(trc))

        ## Local
        with open("error", "w") as f:
            print(f"Writing failure message to file...")
            f.write(str(trc))

        # Sagemaker processing
        if Path("/opt/ml/output/message").exists():
            with open("/opt/ml/output/message", "w") as f:
                print(f"Writing failure message to file...")
                error = str(sys.exc_info()[1])
                f.write(str(error))     ## trc too large to be readable in error message

        # A non-zero exit code causes the training job to be marked as Failed.
        print(f"Exiting Sagemaker job ...")
        sys.exit(1)
        # output_notebook = "xyzzy"  # Dummy for print, below

    if not os.path.exists(output_notebook):
        print("No output notebook was generated")
    else:
        print("Output was written to {}".format(output_notebook))


if __name__ == "__main__":
    run_notebook()
