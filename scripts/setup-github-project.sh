#!/usr/bin/env bash
# One-time setup of a GitHub Project (v2) for this repo, and bulk-adding all open issues to it.
# Requires gh with the "project" scope:  gh auth refresh -s project
set -euo pipefail

OWNER="${OWNER:-Izinshtein-Miryam}"
REPO="${REPO:-smart-recipes}"
TITLE="${TITLE:-מתכונים חכם – פיתוח}"

number=$(gh project list --owner "$OWNER" --format json --jq ".projects[] | select(.title == \"$TITLE\") | .number" | head -n1)
if [[ -z "$number" ]]; then
  number=$(gh project create --owner "$OWNER" --title "$TITLE" --format json --jq '.number')
  echo "Created project #$number"
fi
gh project link "$number" --owner "$OWNER" --repo "$OWNER/$REPO" || true

gh issue list --repo "$OWNER/$REPO" --state open --limit 500 --json url --jq '.[].url' |
  while read -r url; do
    gh project item-add "$number" --owner "$OWNER" --url "$url" >/dev/null && echo "added $url"
  done

url=$(gh project view "$number" --owner "$OWNER" --format json --jq '.url')
echo
echo "Project: $url"
echo "For auto-adding new issues set: repository variable PROJECT_URL=$url and secret PROJECT_TOKEN"
