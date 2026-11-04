#!/usr/bin/env bash
# Adds all open issues of this repo to an existing GitHub Project (v2).
# Requires gh with the "project" scope:  gh auth refresh -s project
#
# Usage:
#   PROJECT_OWNER=tiizinshtein-stack PROJECT_NUMBER=1 ./scripts/setup-github-project.sh
#
# The project number is the last part of the project URL (.../projects/<number>).
# If PROJECT_NUMBER is empty, the project is looked up by PROJECT_TITLE (or created).
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-Izinshtein-Miryam}"
REPO="${REPO:-smart-recipes}"
PROJECT_OWNER="${PROJECT_OWNER:-$REPO_OWNER}"
PROJECT_TITLE="${PROJECT_TITLE:-מתכונים חכם – פיתוח}"
number="${PROJECT_NUMBER:-}"

if [[ -z "$number" ]]; then
  number=$(gh project list --owner "$PROJECT_OWNER" --format json \
    --jq ".projects[] | select(.title == \"$PROJECT_TITLE\") | .number" | head -n1)
fi
if [[ -z "$number" ]]; then
  number=$(gh project create --owner "$PROJECT_OWNER" --title "$PROJECT_TITLE" --format json --jq '.number')
  echo "Created project #$number"
fi
gh project link "$number" --owner "$PROJECT_OWNER" --repo "$REPO_OWNER/$REPO" || true

# item-add is idempotent: an issue that is already in the project is not duplicated.
gh issue list --repo "$REPO_OWNER/$REPO" --state open --limit 500 --json url --jq '.[].url' |
  while read -r url; do
    gh project item-add "$number" --owner "$PROJECT_OWNER" --url "$url" >/dev/null && echo "added $url"
  done

url=$(gh project view "$number" --owner "$PROJECT_OWNER" --format json --jq '.url')
echo
echo "Project: $url"
echo "For auto-adding new issues set repository variable PROJECT_URL=$url and secret PROJECT_TOKEN"
