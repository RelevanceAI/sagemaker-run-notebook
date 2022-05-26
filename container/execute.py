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
PAPERMILL_PARAMS = f"""{
            "dataset_id": "test-vectorize",
            "model_id": "clip",
            "encode_type": "image_urls",
            "fields": ["product_image"],
            "authorizationToken":"{os.environ['TEST_REGINES_TOKEN']}"
}"""

ROOT_PATH = Path(__file__).parent


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

        if params.get("S3_PATH"):
            params_path = params.get("S3_PATH")
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
        ## Mask creds
        params_clean = params.copy()
        if params_clean.get("authorizationToken"):
            params_clean["authorizationToken"] = "*" * len(
                params_clean["authorizationToken"]
            )
        print(f"Notebook params = {json.dumps(params_clean, indent=2)}")
        print(params)

        papermill.execute_notebook(
            notebook_file, output_notebook, params, kernel_name="python3"
        )
        print("Execution complete")

    except Exception as e:

        trc = traceback.format_exc()

        error_message = "Exception during processing: " + str(e) + "\n" + trc
        # print(str(trc))

        trc_data = trc.splitlines()
        print(error_message)

        # Write out an error file. This will be returned as the ExitMessage in the DescribeProcessingJob result.
        if not os.getenv(params_var):
            FPATH = ROOT_PATH / "error"
        else:
            FPATH = "/opt/ml/output/message"

        # Dump as valid json
        err = trc_data[-2]
        try:
            err_s = err.split(": ")
            try:
                message = json.loads(err_s[1])
            except:
                message = err_s[1]
            err_dict = {"error": err_s[0], **{"message": message}}
            err = json.dumps(err_dict)
        except Exception as e:
            print(f"Error loading error message as dict: {e}")

        with open(FPATH, "w") as f:
            print(f"Writing failure message to file...")
            f.write(err)

        try:
            with open(FPATH, "r") as f:
                print(f"Reading failure message to file...")
                print(json.load(f))
        except Exception as e:
            print(f"Error reading failure message as dict {e} ...")

        # A non-zero exit code causes the training job to be marked as Failed logs in SM.
        print(f"Exiting Sagemaker job ...")
        sys.exit(1)

    if not os.path.exists(output_notebook):
        print("No output notebook was generated.")
    else:
        print(f"Output was written to {output_notebook}")


if __name__ == "__main__":
    run_notebook()
