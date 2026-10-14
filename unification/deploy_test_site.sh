#!/usr/bin/env bash
# Keep the devbox's test site on the newest code that passed its checks: the open sync PR's head
# while it isn't a draft, otherwise $BASE. It only moves forward. Runs after sync_pr.sh.
#
#   REPO        owner/name of the repo behind the remote "origin"
#   BASE        the branch the sync PRs go into (unified)
#   SITE_BENCH  the bench serving the site; its apps/frappe is a checkout of this repo
#   SITE        the site to migrate, and SITE_UNIT the systemd unit that runs the bench
set -uo pipefail
BASE=${BASE:-unified}
cd "$SITE_BENCH/apps/frappe" || exit 1
git fetch --quiet origin || exit 1
pr_head=$(gh pr list --repo "$REPO" --head sync/upstream --base "$BASE" --state open \
	--json headRefOid,isDraft --jq '.[0] | select(.isDraft | not) | .headRefOid') || exit 1
target=${pr_head:-$(git rev-parse "origin/$BASE")}
current=$(git rev-parse HEAD)
if [[ $target == "$current" ]]; then
	exit 0
fi
if ! git merge-base --is-ancestor "$current" "$target"; then
	echo "The test site stays at $current: $target doesn't build on it."
	exit 0
fi
echo "Moving the test site from ${current:0:10} to ${target:0:10}."
set -e
git -c advice.detachedHead=false checkout --quiet --detach "$target"
uv pip install --quiet --python "$SITE_BENCH/env/bin/python" --editable .
yarn install --frozen-lockfile --non-interactive --silent
yarn --cwd studio install --frozen-lockfile --non-interactive --silent
(cd "$SITE_BENCH" && bench build --app frappe)
(cd "$SITE_BENCH/sites" && ../env/bin/python -m frappe.utils.bench_helper frappe --site "$SITE" migrate)
sudo systemctl restart "$SITE_UNIT"
