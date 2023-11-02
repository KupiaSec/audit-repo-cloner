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

To use this, you'll need a [github personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token).

Duplicate `.env.example` and rename it to `.env`. Then, add your access token to the `ACCESS_TOKEN` variable.

**NOTE**: The token owner must have access to the source repo.

# Usage

```bash
python audit_repo_cloner/create_audit_repo.py
```

You will be asked to input the following:
1) Source repo url
 Enter the link to the source repo URL (e.g. `https://github.com/Cyfrin/foundry-full-course-f23`).
2) Target repo name
 If leave blank, it will default to `audit-source repo name` with `audit` prefix (e.g. `audit-foundry-full-course-f23`).
3) Audit commit hash:
 Enter the commit hash provided by the client (e.g. `25d62b685857f5c1906675a3876d7d7773a8b3bd`).

After a few moments, you'll have a repo ready for audit!
