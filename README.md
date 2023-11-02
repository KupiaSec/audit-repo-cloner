# Audit Repository Cloner

_Forked from [Cyfrin/audit-repo-cloner](https://github.com/Cyfrin/audit-repo-cloner)_

# What it does

It will take the following steps:
1. Take the `source` repository you want to set up for audit
2. Take the `target` repository name you want to use for the private --repo
3. Add an `issue_template` to the repo, so issues can be formatted as audit findings, like:

```
**Description:**
**Severity:**
**Proof of Concept:**
**Recommended Mitigation:**
**Client:**
**Kupia:**
```

4. Update labels to label issues based on severity and status
5. Create an audit tag at the given commit hash (full SHA)

# Getting Started

## Installation

1. Mac
```bash
git clone https://github.com/KupiaSec/audit-repo-cloner
cd audit-repo-cloner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
2. Windows
```bash
git clone https://github.com/KupiaSec/audit-repo-cloner
cd audit-repo-cloner
virtualenv venv
venv\scripts\activate
pip install -r requirements.txt
```

## Env

Duplicate `.env.example` and rename it to `.env` and set the values properly.
1. `GITHUB_ACCESS_TOKEN` - A [github personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) generated in the GitHub account that is allowed to create/update repositories in the organization.
2. `GITHUB_ORGANIZATION` - The name of the GitHub organization that the repositories will be created in.
3. `SOURCE_REPO_URL` - The URL of the source repository that will be cloned.
4. `TARGET_REPO_NAME` - The name of the target repository that will be created.
5. `COMMIT_HASH` - The commit hash of the source repository that will be cloned.
6. `PROJECT_TEMPLATE_ID` - The ID of the project template that will be used to create the project in the target repository. This can be retrieved by going to the project template in the target repository and copying the ID from the URL. For example, if the URL is `https://github.com/orgs/KupiaSec/projects/7/views/2`, the ID would be `7`.
7. `PROJECT_TITLE` - The title of the project that will be created.

# Usage
Make sure you have all values in the `.env` file set properly and then run the following command:
```bash
python audit_repo_cloner/create_audit_repo.py
```
