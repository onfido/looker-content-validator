# **Gitlab CI Pipeline for Looker Content Validator**
This repository contains a Python script and Jinja template for running the Looker Content Validator when Merge Requests are created on Gitlab, as well as the `.gitlab-ci.yml` for configuring the pipeline. These should be added to your LookML repository.

The script and template are in the `gitlab-ci` folder so as to keep your LookML repository tidy.

The python script `content_validator.py` and the isn't visible in the Looker IDE, but we shouldn't be working on anything here from the Looker IDE.

## **Content Validator script**
The script won't be visible in the Looker IDE.

The script uses environment variables to determine which repo/project, merge request and branch to look at, as well as API credentials for the Looker & Gitlab APIs. It runs the Content Validator for the MR branch via the API, then iterates the results in order to shape and format them, such that they can be displayed in a Markdown table in the same format as in the Looker UI. A summary of the results and the errors table is then posted to the Merge Request as a note/comment, rendered in the Jinja template `comment.template.md`. If there is a comment already it will be updated rather than duplicated - an existing comment is identified by the HTML comment `<!-- content_validator_ci_message -->` in its body.

### **Gitlab setup**
Running the script as a CI process when Merge Requests are created/updated is configured in the `.gitlab-ci.yml`  file. This sets the an environment variable for the base URL of the Looker API, installs the necessary Python packages, and invokes the `content_validator.py` script.

The environment variables starting `CI_` are predefined in the Gitlab CI context. The variables `LOOKERSDK_CLIENT_ID`, `LOOKERSDK_CLIENT_SECRET` and `GITLAB_API_TOKEN` must be set in the CI/CD settings of the Gitlab project.

### **Development/running locally**
The script can be run locally for testing & development purposes. Clone the repository to your machine, and set the required environment variables, with a command like `export VARIABLE_1=value1 VARIABLE_2=value2 ...`, before running the script with `python gitlab-ci/content_validator.py`.

The required variables are:

- `LOOKERSDK_BASE_URL` - e.g. `https://looker.bi.onfido.xyz:19999`
- `LOOKERSDK_CLIENT_ID` and `LOOKERSDK_CLIENT_SECRET` - Looker API credentials, which must have the `developer` permission in order to run the Content Validator
- `CI_PROJECT_ID` - Numeric Gitlab ID of the project/repository.
- `CI_MERGE_REQUEST_SOURCE_BRANCH_NAME` - which Git branch to use when running the validator.
- `CI_MERGE_REQUEST_IID` - Gitlab ID of the Merge Request. This can be found at the end of the MR's URL e.g. in  `/merge_requests/88` the ID is 88
- `GITLAB_API_TOKEN` - API token to allow the script to post a comment on the MR. You can generate one for yourself in your Gitlab settings