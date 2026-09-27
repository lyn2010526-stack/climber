# Dependency and Supply-Chain Audit

- Audit date: 2026-09-26
- Scope: Python manifests at repository root and the `frontend-react` npm manifest/lockfile
- Task: Second-round task 5
- Change boundary: documentation only; no production code, dependency manifest, or lockfile was modified
- Credential handling: no secrets, environment values, or credential files were read

## Manifests Reviewed

### Python

- `pyproject.toml`
- `requirements.txt`
- No `poetry.lock`, `Pipfile.lock`, `uv.lock`, `setup.py`, or `setup.cfg` was found.

The Python dependency declarations use lower bounds in `requirements.txt`; the repository has no Python lockfile for reproducible version resolution.

### JavaScript

- `frontend-react/package.json`
- `frontend-react/package-lock.json` (lockfile version 3)

No root-level npm manifest was found. The frontend manifest defines the npm dependency graph for this audit.

## Tool Availability and Executed Checks

### Local `pip-audit` availability

Commands:

```text
command -v pip-audit
python3 -m pip_audit --local
python3 -m pip show pip-audit
command -v uv
command -v pipx
```

Exact output:

```text
zsh:1: command not found: pip-audit
/usr/bin/python3: No module named pip_audit
WARNING: Package(s) not found: pip-audit
```

The `uv` and `pipx` checks produced no output, so neither alternate runner is available on `PATH`. `pip-audit` cannot be run from the packages or tooling already available in this environment.

No package was installed. The checks did not read environment variables, credential files, or secret values.

### Python: `pip-audit`

Command:

```text
python3 -m pip_audit --local
```

Result: not executed successfully. The tool is unavailable in the current environment.

Real output:

```text
/usr/bin/python3: No module named pip_audit
```

The audit did not install `pip-audit`, because no installation was strictly necessary and the task requires avoiding unrelated dependency changes. A vulnerability database-backed Python package audit is therefore unavailable in this run.

### Reproducible Python audit command

The repository CI security job provides the reproducible execution path. It installs the audit tool in the ephemeral CI environment, audits the declared requirements file, and uploads the JSON report:

```bash
python -m pip install --upgrade pip
pip install bandit safety pip-audit
pip install -r requirements.txt
pip-audit -r requirements.txt --format json --output pip-audit-report.json
```

This command audits `requirements.txt` and does not require project credentials. The current CI workflow uses the same command with `|| true`, so report generation does not currently fail the job when findings or an audit error occurs. The CI report artifact must be inspected to obtain vulnerability results.

### Python: installed-environment consistency substitute

Command:

```text
python3 -m pip check
```

Result: passed, exit status 0.

Real output:

```text
No broken requirements found.
```

This verifies metadata consistency for packages already installed in the environment. It does not identify known vulnerabilities and does not prove that every package declared in `requirements.txt` is installed.

### npm: offline vulnerability audit

Command:

```text
npm audit --offline --json
```

Result: passed, exit status 0.

Real output:

```json
{
  "auditReportVersion": 2,
  "vulnerabilities": {},
  "metadata": {
    "vulnerabilities": {
      "info": 0,
      "low": 0,
      "moderate": 0,
      "high": 0,
      "critical": 0,
      "total": 0
    },
    "dependencies": {
      "prod": 275,
      "dev": 238,
      "optional": 76,
      "peer": 13,
      "peerOptional": 0,
      "total": 572
    }
  }
}
```

The result is based on npm's locally available audit data and the frontend lockfile. Network freshness of the advisory database was not verified.

### npm: manifest and lockfile consistency

Command:

```text
npm install --package-lock-only --ignore-scripts --offline --dry-run
```

Result: passed, exit status 0.

Real output:

```text
up to date in 422ms

169 packages are looking for funding
  run `npm fund` for details
```

The command completed in offline dry-run mode and did not change the lockfile.

## Findings and Limits

- npm's offline audit reported zero vulnerabilities across 572 dependency entries.
- Python installed-package metadata passed `pip check`.
- Python known-vulnerability coverage is incomplete because `pip-audit` is unavailable and no equivalent offline vulnerability database tool was installed.
- A reproducible CI command exists at `.github/workflows/ci.yml:193-204`; this run did not install or execute it locally.
- Python reproducibility coverage is incomplete because the project has no Python lockfile and `requirements.txt` specifies lower bounds.
- npm advisory freshness and transitive package provenance were not independently verified against a current online registry.
- This audit is evidence for the commands above at the audit date; it is not a release approval or a guarantee that future advisory databases will produce the same result.

## Worktree Safety Check

The existing worktree contains unrelated user/agent modifications, including an existing `pyproject.toml` modification. This audit update is limited to `docs/DEPENDENCY_AUDIT.md`; production code and dependency manifests were left unchanged by this task. No commit or push was performed.
