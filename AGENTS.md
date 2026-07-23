# McStasScript — Project Notes

## Project Overview

McStasScript is a Python API for creating, running, and analyzing McStas/McXtrace neutron and X-ray instrument simulations. It provides a programmatic interface to build instruments, execute simulations via `mcrun`/`mxrun`, and plot results — usable from scripts, terminals, or Jupyter notebooks.

### Package Structure

```
mcstasscript/
├── __init__.py              # Public API: McStas_instr, load_data, Configurator, plotter, etc.
├── _version.py              # Package version
├── configuration.yaml       # Default paths to McStas/McXtrace executables
├── data/                    # Data model: McStasData, McStasMetaData, McStasPlotOptions, MCPL adapters
├── helper/                  # Internal utilities: Component objects, mcrun wrapper, formatting, plotting helpers
├── instr_reader/            # .instr file parser: reads McStas instrument files into Python objects
├── instrument_diagnostics/  # Beam and intensity diagnostics: inserts monitors, collects event data
├── instrument_diagram/      # Visual instrument layout diagrams via matplotlib
├── integration_tests/       # End-to-end tests that run actual McStas simulations
├── interface/               # Core API: McStas_instr builder, data loading, plotting, Configurator
├── jb_interface/            # Jupyter widget interface: interactive simulation control and plotting
├── tests/                   # Unit tests (20+ modules) with fixtures
└── tools/                   # Specialized tools: Cryostat builder, instrument checker, NCrystal integration
```

### Supporting Directories

- **examples/** — Demo notebooks and scripts (cryostat, libpyvinyl, calibration)
- **tutorial/** — Step-by-step notebooks covering basics, SPLIT, EXTEND/WHEN, JUMP, and Union components
- **docs/** — Sphinx documentation source with autosummary-generated API docs
- **test_instr_db/** — Instrument database fixtures for reader tests

## Running Tests

### Unit Tests

Run with `python -m unittest`. For example:

```bash
python -m unittest mcstasscript.tests.test_instrument_diagnostics -v
```

### Integration Tests

Integration tests require a McStas installation. Run with:

```bash
python -m unittest discover -s mcstasscript/integration_tests -v
```

## GitHub CLI

Use the authenticated `gh` CLI for GitHub-hosted operations such as pull
requests, issues, reviews, checks, and releases. Verify the active
authentication before performing those operations:

```bash
gh auth status
gh api user --jq '.login'
```

If Git transport authentication is unavailable, configure Git to use the
authenticated `gh` token with:

```bash
gh auth setup-git
```

## GitHub PR Review Comments (via gh CLI)

### Replying to a review comment

Use `in_reply_to` with the comment ID — **must be done before pushing a new commit**, otherwise the comment becomes "outdated" and the API returns 404:

```bash
gh api repos/<owner>/<repo>/pulls/comments -X POST --input - <<'EOF'
{
  "body": "Your reply text here.",
  "in_reply_to": <comment_id>
}
EOF
```

### Creating an inline comment on the current commit

```bash
gh api repos/<owner>/<repo>/pulls/1/comments -X POST --input - <<'EOF'
{
  "body": "Comment text.",
  "path": "path/to/file.py",
  "commit_id": "<current_commit_sha>",
  "position": <line_number_in_diff>
}
EOF
```

### Creating a review with multiple inline comments

```bash
gh api repos/<owner>/<repo>/pulls/1/reviews -X POST --input - <<'EOF'
{
  "commit_id": "<commit_sha>",
  "body": "Review summary",
  "event": "COMMENT",
  "comments": [
    {
      "path": "path/to/file.py",
      "line": 8,
      "body": "Comment on line 8."
    },
    {
      "path": "path/to/file.py",
      "line": 100,
      "body": "Comment on line 100."
    }
  ]
}
EOF
```

### Important: Reply before pushing

Once you push a new commit, the reviewer's comments become "outdated" and can no longer be replied to via the API. Always reply to review comments **before** pushing your fix commit.
