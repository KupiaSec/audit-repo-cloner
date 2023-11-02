import os
import requests
from datetime import date
from typing import List, Optional, Tuple
from github import Github, GithubException, Repository, Organization
from dotenv import load_dotenv
from create_action import create_action
import click
import subprocess
import tempfile
import logging as log
import yaml
import re
from __version__ import __version__, __title__
from github_project_utils import clone_project

from constants import (
    ISSUE_TEMPLATE,
    DEFAULT_LABELS,
    SEVERITY_DATA,
)

log.basicConfig(level=log.INFO)

# Load env values
load_dotenv()

# Globals are shit. We should refactor again in the future...
MAIN_BRANCH_NAME = "main"


@click.command()
@click.version_option(
    version=__version__,
    prog_name=__title__,
)
@click.option("--source-url", default=os.getenv("SOURCE_REPO_URL"), help="Source repository URL.")
@click.option(
    "--target-repo-name",
    default=os.getenv("TARGET_REPO_NAME"),
    help="Target repository name (leave blank to use source repo name).",
)
@click.option("--commit-hash", default=os.getenv("COMMIT_HASH"), help="Audit commit hash.")
@click.option(
    "--github-token",
    default=os.getenv("GITHUB_ACCESS_TOKEN"),
    help="Your GitHub developer token to make API calls.",
)
@click.option(
    "--organization",
    default=os.getenv("GITHUB_ORGANIZATION"),
    help="Your GitHub organization name in which to clone the repo.",
)
@click.option(
    "--project-template-id",
    default=os.getenv("PROJECT_TEMPLATE_ID"),
    help="ID from the project template URL.",
)
@click.option(
    "--project-title",
    default=os.getenv("PROJECT_TITLE"),
    help="Title of the new project.",
)
def create_audit_repo(
    source_url: str,
    target_repo_name: str,
    commit_hash: str,
    github_token: str,
    organization: str,
    project_template_id: str,
    project_title: str
):
    """This function clones a target repository and prepares it for a Kupia audit using the provided arguments.
    Args:
        source_url (str): The URL of the source repository to be cloned and prepared for the Kupia audit.
        target_repo_name (str): The name of the target repository to be created.
        github_token (str): The GitHub developer token to make API calls.
        organization (str): The GitHub organization to create the audit repository in.

    Returns:
        None
    """
    # prompt if any mandatory info is not given
    (
        source_url,
        target_repo_name,
        commit_hash,
        organization,
    ) = prompt_for_details(
        source_url, target_repo_name, commit_hash, organization
    )
    if not source_url or not commit_hash or not organization:
        raise click.UsageError(
            "Source URL, commit hash, and organization must be provided either through --prompt, config, or as options."
        )
    if not github_token:
        raise click.UsageError(
            "GitHub token must be provided either through config or environment variable."
        )

    source_url = source_url.replace(".git", "")  # remove .git from the url
    url_parts = source_url.split("/")
    source_username = url_parts[-2]
    source_repo_name = url_parts[-1]

    # if target_repo_name is not provided, attempt to use the source repo name
    if not target_repo_name:
        target_repo_name = 'audit-' + source_repo_name

    with tempfile.TemporaryDirectory() as temp_dir:
        repo = try_clone_repo(
            github_token,
            organization,
            target_repo_name,
            source_repo_name,
            source_username,
            temp_dir,
            commit_hash,
        )

        repo = create_audit_tag(repo, temp_dir, commit_hash)
        repo = add_issue_template_to_repo(repo)
        repo = replace_labels_in_repo(repo)

    # create project board optionally
    if project_template_id and project_title:
        set_up_project_board(token=github_token, org_name=organization, project_template_id=project_template_id, project_title=project_title)

    print("Done!")

def prompt_for_details(
    source_url: str,
    target_repo_name: str,
    commit_hash: str,
    organization: str,
):
    while True:
        prompt_counter = 1

        if not source_url:
            source_url = input(
                f"Hello! This script will clone the source repository and prepare it for a Kupia audit. Please enter the following details:\n\n{prompt_counter}) Source repo url: "
            )
            prompt_counter += 1
        if not target_repo_name:
            target_repo_name = input(
                f"\n{prompt_counter}) Target repo name (leave blank to use source repo name): "
            )
            prompt_counter += 1
        if not commit_hash:
            commit_hash = input(
                f"\n{prompt_counter}) Audit commit hash (be sure to copy the full SHA): "
            )
            prompt_counter += 1
        if not organization:
            organization = input(
                f"\n{prompt_counter}) Enter the name of the organization to create the audit repository in: "
            )
            prompt_counter += 1

        if source_url and commit_hash and organization:
            break
        print("Please fill in all the details.")
    return source_url, target_repo_name, commit_hash, organization


def try_clone_repo(
    github_token: str,
    organization: str,
    target_repo_name: str,
    source_repo_name: str,
    source_username: str,
    repo_path: str,
    commit_hash: str,
) -> Repository:
    github_object = Github(github_token)
    github_org = github_object.get_organization(organization)
    repo = None
    try:
        print(f"Checking whether {target_repo_name} already exists...")
        git_command = [
            "git",
            "ls-remote",
            "-h",
            f"https://{github_token}@github.com/{organization}/{target_repo_name}",
        ]

        result = subprocess.run(
            git_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        if result.returncode == 0:
            log.error(f"{organization}/{target_repo_name} already exists.")
            exit()
        elif result.returncode == 128:
            repo = create_and_clone_repo(
                github_token,
                github_org,
                organization,
                target_repo_name,
                source_repo_name,
                source_username,
                repo_path,
                commit_hash,
            )
    except subprocess.CalledProcessError as e:
        if e.returncode == 128:
            repo = create_and_clone_repo(
                github_token,
                github_org,
                organization,
                target_repo_name,
                source_repo_name,
                source_username,
                repo_path,
                commit_hash,
            )
        else:
            # Handle other errors or exceptions as needed
            log.error(f"Error checking if repository exists: {e}")
            exit()

    if repo is None:
        log.error("Error creating repo.")
        exit()

    return repo


def create_and_clone_repo(
    github_token: str,
    github_org: Organization,
    organization: str,
    target_repo_name: str,
    source_repo_name: str,
    source_username: str,
    repo_path: str,
    commit_hash: str,
) -> Repository:
    try:
        repo = github_org.create_repo(target_repo_name, private=True)
    except GithubException as e:
        log.error(f"Error creating remote repository: {e}")

    try:
        print(f"Cloning {source_repo_name}...")
        subprocess.run(
            [
                "git",
                "clone",
                f"https://{github_token}@github.com/{source_username}/{source_repo_name}.git",
                repo_path,
            ]
        )

    except GithubException as e:
        log.error(f"Error cloning repository: {e}")
        repo.delete()
        exit()

    try:
        subprocess.run(["git", "-C", repo_path, "fetch", "origin"])

        # Identify the branch containing the commit using `git branch --contains`
        completed_process = subprocess.run(
            ["git", "-C", repo_path, "branch", "-r", "--contains", commit_hash],
            text=True,
            capture_output=True,
            check=True,
        )

        filtered_branches = [
            b
            for b in completed_process.stdout.strip().split("\n")
            if not "origin/HEAD ->" in b
        ]
        branches = [b.split("/", 1)[1] for b in filtered_branches]

        if not branches:
            raise Exception(f"Commit {commit_hash} not found in any branch")

        if len(branches) > 1:
            # Prompt the user to choose the branch
            print("The commit is found on multiple branches:")
            for i, branch in enumerate(branches):
                print(f"{i+1}. {branch}")

            while True:
                try:
                    branch_index = int(
                        input("Enter the number of the branch to create the tag: ")
                    )
                    if branch_index < 1 or branch_index > len(branches):
                        raise ValueError("Invalid branch index")
                    branch = branches[branch_index - 1]
                    break
                except ValueError:
                    print("Invalid branch index. Please enter a valid index.")
        else:
            branch = branches[0]

        # Fetch the branch containing the commit hash
        subprocess.run(
            [
                "git",
                "-C",
                repo_path,
                "fetch",
                "origin",
                branch + ":refs/remotes/origin/" + branch,
            ]
        )

        # Checkout the branch containing the commit hash
        subprocess.run(["git", "-C", repo_path, "checkout", branch])

        # Update the origin remote
        subprocess.run(
            [
                "git",
                "-C",
                repo_path,
                "remote",
                "set-url",
                "origin",
                f"https://{github_token}@github.com/{organization}/{target_repo_name}.git",
            ]
        )

        # Push the branch to the remote audit repository as 'main'
        # subprocess.run(f"git -C {repo_path} push -u origin {branch}:{MAIN_BRANCH_NAME}")
        subprocess.run(
            [
                "git",
                "-C",
                repo_path,
                "push",
                "-u",
                "origin",
                f"{branch}:{MAIN_BRANCH_NAME}",
            ]
        )

    except Exception as e:
        log.error(f"Error extracting branch of commit hash: {e}")
        repo.delete()
        exit()

    return repo


def create_audit_tag(repo, repo_path, commit_hash) -> Repository:
    log.info("Creating audit tag...")

    try:
        tag = repo.create_git_tag(
            tag="kupia-audit",
            message="Kupia audit tag",
            object=commit_hash,
            type="commit",
        )

        # Now create a reference to this tag in the repository
        repo.create_git_ref(ref=f"refs/tags/{tag.tag}", sha=tag.sha)
    except GithubException as e:
        log.error(f"Error creating audit tag: {e}")
        log.info("Attempting to create tag manually...")

        try:
            # Create the tag at the specific commit hash
            subprocess.run(["git", "-C", repo_path, "tag", "kupia-audit", commit_hash])

            # Push the tag to the remote repository
            subprocess.run(["git", "-C", repo_path, "push", "origin", "kupia-audit"])
        except GithubException as e:
            log.error(f"Error creating audit tag manually: {e}")
            repo.delete()
            exit()
    return repo


def add_issue_template_to_repo(repo) -> Repository:
    # Get the existing finding.md file, if it exists
    try:
        finding_file = repo.get_contents(".github/ISSUE_TEMPLATE/finding.md")
    except GithubException as e:
        finding_file = None

    # If finding.md already exists, leave it be. Otherwise, create the file.
    if finding_file is None:
        repo.create_file(
            ".github/ISSUE_TEMPLATE/finding.md", "finding.md", ISSUE_TEMPLATE
        )
    return repo


def delete_default_labels(repo) -> Repository:
    log.info("Deleting default labels...")
    for label_name in DEFAULT_LABELS:
        try:
            label = repo.get_label(label_name)
            log.info(f"Deleting {label}...")
            label.delete()
        except Exception as e:
            log.warn(f"Label {label} does not exist. Skipping...")
    log.info("Finished deleting default labels")
    return repo


def create_new_labels(repo) -> Repository:
    log.info("Creating new labels...")
    for data in SEVERITY_DATA:
        try:
            repo.create_label(**data)
        except:
            log.warn(f"Issue creating label with data: {data}. Skipping...")
    print("Finished creating new labels")
    return repo


def replace_labels_in_repo(repo) -> Repository:
    repo = delete_default_labels(repo)
    repo = create_new_labels(repo)
    return repo

# IMPORTANT: project creation via REST API is not supported anymore
# https://stackoverflow.com/questions/73268885/unable-to-create-project-in-repository-or-organisation-using-github-rest-api
# we use a non-standard way to access GitHub's GraphQL

def set_up_project_board(token:str, org_name:str, project_template_id:str, project_title:str):
    try:
        clone_project(token, org_name, project_template_id, project_title)
        print("Project board has been set up successfully!")
    except Exception as e:
        print(f"Error occurred while setting up project board: {str(e)}")
        print("Please set up project board manually.")
    return


if __name__ == "__main__":
    create_audit_repo()
