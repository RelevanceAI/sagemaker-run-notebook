# Changelog


## v0.26.0 (2022-05-23)

This release supports -

- Changing stage to environment - limiting to 'development' and 'production' to align with main env


```python
sm_job = run.invoke(
                notebook=NOTEBOOK_PATH,
                environment=environment,
                region=region,
                image=f"sagemaker-run-notebook-{environment}",
                role=EXECUTION_ROLE,
                parameters={**{"JOB_ID": JOB_ID}, **params},
                upload_parameters=True,
            )
```


## v0.25.1 (2022-05-13)

This release supports -

- Fixing regional deploy on Sagemaker Processing execution container image


## v0.25.0 (2022-05-11)

This release supports -

- Ability to deploy sagemaker-run-notebook infra stack to different regions (currently just ap-southeast-1/us-east-1) 

```zsh
❯ make create-infra STAGE=dev REGION=us-east-1 
❯ make update-infra STAGE=dev REGION=us-east-1  
```

- Ability to deploy Processing Jobs to different regions from `run.invoke` and `run.schedule` etc


```python
sm_job = run.invoke(
                notebook=NOTEBOOK_PATH,
                stage=stage,
                region=region,
                image=f"sagemaker-run-notebook-{stage}",
                role=EXECUTION_ROLE,
                parameters={**{"JOB_ID": JOB_ID}, **params},
                upload_parameters=True,
            )
```

## v0.24.4 (2022-05-11)

This release supports -

- Fixing missing deps for DR (umap)

## v0.24.3 (2022-05-09)

This release supports -

- Fixing missing deps for clip vectorization (matplotlib)
  
## v0.24.2 (2022-05-09)

This release supports -

- Vectorizing over all models (inc clip/bit etc) - adding requried deps to run container
## v0.24.1 (2022-05-06)

This release supports -

- Error message dump formatted as JSON for API render 

error message returned on Job failure
eg. 
```json
{"APIError": {"message": "Dataset could not be found in project."}}
```

API response

```
{
	"JOB_STATUS": "Failed",
	"JOB_MESSAGE": {
		"message": "Job Failed 0 days, 0 hours, 5 min, 12.34 secs ago.",
		"exit_message": {
			"error": "APIError",
			"message": {
				"message": "Dataset could not be found in project."
			}
		}
	},
...
```



## v0.24.0 (2022-05-06)

This release supports -

- Filtering sagemaker-run-notebook traceback error for Sagemaker Processing ErrorMessage and API

## v0.23.0 (2022-05-05)

This release supports -

- Uploading param file to get around 256 char limit container

    ```python
    sm_job = run.invoke(
                    input_path=NOTEBOOK_PATH,
                    stage=stage,
                    image=f'sagemaker-run-notebook-{stage}',
                    role=EXECUTION_ROLE,
                    parameters={**{"JOB_ID": body["JOB_ID"]}, **config},
                    upload_parameters=True
                )
    ```

## v0.22.1 (2022-05-04)

Fixing Makefile
## v0.22.0 (2022-05-04)

This release supports -

- Ability to deploy in stages (dev, stg, prd). All resources are appended with stage name. Default is dev.
    ```zsh
    make create-infra --stage stg       ## Deploying new sagemaker-run-notebook stack
    make create-infra --stage stg --update   ## Updating the stack
    make build-and-push --stage stg     ## Updating the Sagemaker container execution image
    ```


## v0.21.4 (2022-05-03)

This release supports -

- Sagemaker Processing Job fails if notebook fail.

## v0.21.3 (2022-04-29)

This release supports -

- Removing "JOB_ID" from params to reduce chance of hitting [265 char limit on Sagemaker Processing container](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ProcessingJob.html)

## v0.21.0 (2022-04-29)

This release supports -

- S3 URL input upon invoke.
- changing Processing job name to param "JOB_ID" of format "workflow-cluster-<datetime.now().timestamp()>" - from incoming request payload

## v0.20.0 (2021-12-09)

This release provides support for JupyterLab 2.x.

As of this release, the JupyterLab extension is *no longer compatible with JupyterLab 1.x*. If you're using JupyterLab 1.x, please use [release v0.19.0](#v0190-2021-12-07).

## v0.19.0 (2021-12-07)

This release has a number of small improvements and bug fixes.

After upgrading to this release, we recommend that you delete and recreate your infrastructure with the following commands:

1. `aws cloudformation delete-stack --stack-name sagemaker-run-notebook`
2. `run-notebook create-infrastructure`

This will pick up the new managed policies (see under [Bug Fixes])(#bug-fixes) below) which can not be updated with the `--update` option.

### Bug fixes

* Fixed an install failure on versions >= 3.10. (Fixes [issue #35](https://github.com/aws-samples/sagemaker-run-notebook/issues/35))
* Use managed policies so that we can include the policies in other roles (See [Change policies to managed policies](https://github.com/aws-samples/sagemaker-run-notebook/pull/14) by @dmoser04).
* Use a single permission statement on the Lambda function for all EventBridge rules. This prevents us overflowing the number of separate permissions when we have many scheduled notebook runs. This also means that we're not creating permissions at schedule time. (Fixes [issue #9](https://github.com/aws-samples/sagemaker-run-notebook/issues/9))
* Correctly handle scheduled runs with no supplied parameters. (Fixes [issue #25](https://github.com/aws-samples/sagemaker-run-notebook/issues/25))
* Update various JS dependencies for security fixes.

## v0.18.0 (2020-11-06)

This is a documentation only release:

* It adds the documentation tarball (`docs.tar.gz`) to the release.
* It adds reasonable docstrings to all the exported functions in `sagemaker_run_notebook`.

## v0.17.0 (2020-11-05)

Ignore. Not actually released.

## v0.16.0 (2020-10-23)

Users moving to this version should update their Lambda function and permissions by running:

```shell
$ run-notebook create-infrastructure --update
```

### Features

* Added the ability to run notebooks connected to an EMR cluster using SparkMagic. See the [EMR examples][EMR example] for more information on using this feature.
* Add the permissions to the default execution policy and role that allow notebook executions to attach to user VPCs via the `--extra` option.

[EMR example]: https://github.com/aws-samples/sagemaker-run-notebook/tree/master/examples/EMR

### Bug fixes

* Pass environment variables specified in `--extra` parameters through to the notebook execution.
* Restrict S3 permissions in the default role to buckets whose name contains the word "SageMaker".
* Unpin the version of the Python "requests" library because it is (a) no longer necessary and (b) cause a dependency error with the latest version of boto3.

## v0.15.0 (2020-09-23)

### Bugs

* Fixed [Issue #4](https://github.com/aws-samples/sagemaker-run-notebook/issues/4), a regression where the invocation of papermill would fail with "No such kernel". (Note that any containers built under v0.14.0, should be rebuilt with `run-notebook )

### Features

Two small changes:

* Added a `-v` option to run-notebook to display the current installed version of the library.
* Changed the install scripts for SageMaker notebooks to install directly from the release on GitHub so users don't need to copy to an S3 bucket first.

## v0.14.0 (2020-09-14)

### Features

* Run notebooks written in R or other languages. See the newly added [R example][example] for information.
* When using the CLI or Library, you can supply extra arguments to the SageMaker Processing Job used to execute the notebook. For example to allow your notebook to run for up to a full day, invoke your notebook with `run-notebook run foo.ipynb --extra '{"StoppingCondition":{"MaxRuntimeInSeconds":86400}}'`. Using this mechanism, you can add extra inputs and outputs, connect to a VPC, add environment variables, expand disk space, add the run to a specific experiment, etc. See the [documentation for SageMaker Processing Jobs][processing-jobs] for more.

[example]: https://github.com/aws-samples/sagemaker-run-notebook/tree/master/examples/R
[processing-jobs]: https://docs.aws.amazon.com/cli/latest/reference/sagemaker/create-processing-job.html

### Running Notebooks

* Add an option to pass extra parameters to SageMaker Processing jobs from the CLI/Library (not yet supported in the JupyterLab extension).
* Add the ability to use the CLI to run the notebook using local Docker containers (`run-notebook local`).

### Container building (`run-notebook create-container`)

* Support base containers from ECR repos in other AWS accounts (to enable using [AWS Deep Learning Containers][dlc]).
* Add the `-k` option to allow alternate Jupyter kernels
* Add the `--script` option for running arbitrary shell scripts as part of building the container.
* Tail the build logs when running the build so you can see any errors that happen inline.
* Automatically install Python if the base image doesn't already have it.

[dlc]: https://docs.aws.amazon.com/deep-learning-containers/latest/devguide/deep-learning-containers-images.html

### JupyterLab Extension

* Fixes for running in Safari

## v0.13.0 (2020-06-15)

Initial release.
