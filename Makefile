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

.PHONY: clean artifacts release link install test run cfntemplate docs

ENVIRONMENT ?= sandbox ## sandbox/dev/prod
AWS_REGION ?= ap-southeast-2  	## ap-southeast-2, us-east-1
TAG ?= $(date +%Y%m%d%H%M%S)
AWS_PROFILE ?= Relevance-AI.WorkflowsAdminAccess

release: install test docs
	make artifacts

install: clean
	# Use the -e option to allow the code to be instrumented for code coverage
	pip install -e "." 

install-dev: clean
	# Use the -e[dev] option to allow the code to be instrumented for code coverage
	pip install -e ".[dev]"
	pre-commit install
	jupyter serverextension enable --py sagemaker_run_notebook --sys-prefix

clean:
	rm -f sagemaker_run_notebook/cloudformation.yml
	rm -rf build/dist
	rm -rf docs/build/html/*

clean-python:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	find . -type f -name "*.temp" -delete
	find . -type d -name "*.egg-info" -exec rm -rf "{}" \;
	find . -type d -name ".pytest_cache" -exec rm -rf "{}" \;
	find . -type f -name "*.coverage" -delete

cfntemplate: sagemaker_run_notebook/cloudformation.yml

sagemaker_run_notebook/cloudformation.yml: sagemaker_run_notebook/cloudformation-base.yml sagemaker_run_notebook/lambda_function.py
	pyminify sagemaker_run_notebook/lambda_function.py | sed 's/^/          /' > /tmp/minified.py
	cat sagemaker_run_notebook/cloudformation-base.yml /tmp/minified.py > sagemaker_run_notebook/cloudformation.yml

create-infra: sagemaker_run_notebook/cloudformation.yml
	run-notebook create-infrastructure --environment $(ENVIRONMENT) --region $(AWS_REGION)

build-and-push:
	cd container && ./build_and_push.sh sagemaker-run-notebook $(ENVIRONMENT) $(AWS_REGION) $(AWS_PROFILE) $(TAG) 

update-infra: sagemaker_run_notebook/cloudformation.yml 
	run-notebook create-infrastructure --update --environment $(ENVIRONMENT) --region $(AWS_REGION)

artifacts: clean cfntemplate
	python setup.py sdist --dist-dir build/dist

test:
  # No python tests implemented yet
	# pytest -v .
	black .
	# python lambda_test.run.py

test-lambda:
	python lambda_test/run.py --environment $(ENVIRONMENT)

test-execute: build-and-push
	cd container && docker run --rm -it -v ~/.aws:/root/.aws -v $(shell pwd)/container:/container/  --platform linux/amd64 -p 8080:8080 --env-file .env  sagemaker-run-notebook-$(ENVIRONMENT)

docs:
	(cd docs; make html)
