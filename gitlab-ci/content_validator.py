import datetime
import gitlab
import jinja2
import looker_sdk
from looker_sdk.sdk.api31.models import WriteApiSession, WriteGitBranch
import os
from pathlib import Path
import re
import sys

# initialise sdk & get env vars
sdk = looker_sdk.init31()
branch_name = os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME")
base_url = os.environ.get("LOOKERSDK_BASE_URL")
gitlab_api_token = os.environ.get("GITLAB_API_TOKEN")
merge_request_id = os.environ.get("CI_MERGE_REQUEST_IID")
project_id = os.environ.get("CI_PROJECT_ID")
looker_project_name = "reports"
looker_model_name = "reports"

def validation():
    """Runs Content Validator and posts results in note on merge request"""
    if not branch_name:
        sys.exit('no branch name found. set CI_MERGE_REQUEST_SOURCE_BRANCH_NAME')

    # switch to dev mode & relevant branch
    sdk.update_session(WriteApiSession(workspace_id="dev"))
    sdk.update_git_branch(looker_project_name, WriteGitBranch(name=branch_name))
    
    # make sure we have the latest code
    sdk.reset_project_to_remote(looker_project_name)

    # pull from upstream

    # run validator
    result = sdk.content_validation()
  
    # get errors and group by error text
    grouped = group_errors(result.content_with_errors)

    # reshape to list of lists (and get total error count)
    (rows, total_errors) = format_rows(grouped)

    if total_errors == 0:
        table = "**✅ No errors found! 🎉 Go and have a nice cup of tea or something ☕️ 😁**"
    else:
        # get table markdown
        headers = ["Error", "Content", "Folder", "Model", "Explore"]
        table = tabulater(rows, headers)

    # render full comment body
    template = jinja2.Template(Path("gitlab-ci/comment.template.md").read_text())
    comment_body = template.render(
        branch_name = branch_name,
        time_s = f'{round(float(result.computation_time),1):,}',
        looks = f'{result.total_looks_validated:,}',
        dash_elems = f'{result.total_dashboard_elements_validated:,}',
        dash_filters = f'{result.total_dashboard_filters_validated:,}',
        schedules = f'{result.total_scheduled_plans_validated:,}',
        explores = f'{result.total_explores_validated:,}',
        errors_table = table,
        total_errors = f'{total_errors:,}',
        run_at = datetime.datetime.now().isoformat()
    )

    # connect to gitlab
    gl = gitlab.Gitlab("https://gitlab.eu-west-1.mgmt.onfido.xyz/", private_token=gitlab_api_token)
    mr = gl.projects.get(project_id).mergerequests.get(merge_request_id)
    
    # check for existing message
    pattern  = re.compile('<!-- content_validator_ci_message -->')
    notes = mr.notes.list()
    existing_note = False
    for note in notes:
        if pattern.match(note.body):
            existing_note = note

    if existing_note:
        # update existing message
        existing_note.body = comment_body
        existing_note.save()            
    else:
        # post new message
        mr.notes.create({"body": comment_body})
    
def tabulater(rows, headers):
    """turn list of headers & list of rows into markdown table"""
    md = f"|{'|'.join(headers)}|\n"
    md = md + f"|{'|'.join(list(map(lambda x: '-', headers)))}|\n"
    for row in rows:
        md = md + f"|{'|'.join(row)}|\n"
    return md

def formatted_row(instances):
    """hyperlink markup and <br>s for multi-line table cells"""
    # hyperlinks
    html = list(map(lambda row: [
                    f'<a href="{row[4]}" title="{row[6]}">{row[0]}</a>',
                    f'<a href="{row[5]}">{row[1]}</a>',
                    row[2],
                    row[3]
                ], instances
            ))
    # transpose
    transposed = list(zip(*html))
    return map(lambda t: "<br>".join(t), transposed)

def format_rows(errors):
    """Sort the grouped errors and make nice table rows arrays"""
    total_errors = 0
    rows = []
    for error, instances in sorted(errors.items()):
        # print("instances:")
        # print(instances)
        sorted_instances = sorted(instances)
        rows.append([f"**{str(len(sorted_instances))}  x {error}**"] + list(formatted_row(sorted_instances)))
        total_errors += len(sorted_instances)
    return (rows, total_errors)

def group_errors(broken_content):
    """Return dict of error_text: [error_instances] """
    grouped_errors = {}

    # strip port
    base_url_no_port = base_url[:-6]

    for item in broken_content:
        if item.dashboard:
            content_type = "dashboard"
        else:
            content_type = "look"
        item_content_type = getattr(item, content_type)
        id = item_content_type.id
        name = item_content_type.title
        folder_id = item_content_type.folder.id
        folder_name = item_content_type.folder.name
        errors = item.errors
        url = f"{base_url_no_port}/{content_type}s/{id}"
        folder_url = f"{base_url_no_port}/folders/{folder_id}"
        tooltip = ""
        if item.scheduled_plan:
            tooltip = f"Schedule for Look: {item.look.title}"
            name = item.scheduled_plan.name + " 📅"
        elif item.dashboard_filter:
            tooltip = f"Filter on Dashboard: {item.dashboard.title}"
            name = item.dashboard_filter.name + " 🔍"
        elif item.dashboard:
            tooltip = f"Tile on Dashboard: {item.dashboard.title}"
            if item.dashboard_element.title:
                title = item.dashboard_element.title
            else:
                title = '<no title title>'
            name = title + " 📊"


        for e in errors:
            model = e.model_name or ''
            if model == looker_model_name: 
                explore = e.explore_name or ''
                error_text = e.message
                new_details = [
                    name,
                    folder_name,
                    model,
                    explore,                
                    url,
                    folder_url,
                    tooltip
                ]
                if error_text in grouped_errors.keys():
                    details = grouped_errors[error_text]
                    details.append(new_details)
                else:
                    details = [new_details]
                grouped_errors[error_text] = details

    return grouped_errors

if __name__ == "__main__":
    validation()
