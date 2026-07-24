#!/usr/bin/env bash
# Build McStasScript documentation locally.
#
# Prerequisites:
#   pip install -e .                        # install mcstasscript (editable)
#   pip install -r docs/requirements.txt    # install doc build deps
#
# Usage:
#   ./build_docs.sh                 # build HTML (notebooks NOT executed)
#   ./build_docs.sh --execute       # build HTML, executing all notebooks
#
# Output: docs/build/html/

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS_DIR="$REPO_ROOT/docs"

SPHINX_OPTS="-b html"

if [[ "${1:-}" == "--execute" ]]; then
    echo "==> Note: notebooks will be executed during build."
    SPHINX_OPTS="$SPHINX_OPTS -D nb_execution_mode=force -D nb_execution_timeout=300"
fi

# --- Build ---
echo "==> Building documentation..."
cd "$DOCS_DIR"
python3 -m sphinx $SPHINX_OPTS source build/html

echo ""
echo "==> Done. Open docs/build/html/index.html in a browser."
