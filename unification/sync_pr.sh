#!/usr/bin/env bash
# Merge the upstream changes that merge cleanly, check them, and open a PR into $BASE. A source
# that conflicts is set aside and listed in one "Upstream sync needs a hand" issue.
#
# Starts in a worktree already reset to origin/$BASE. systemd/unification-sync.service does that
# before running this, so the script is never rewritten while it runs.
#
#   REPO       owner/name of the repo behind the remote "origin", where the PR goes
#   BASE       the branch to merge into (unified)
#   BENCH      the bench this worktree is apps/frappe of (default ../..): its env/ is reinstalled
#              from the worktree, and TEST_SITE in its sites/ is one the tests may change
#   DRY_RUN=1  print the PR and issue instead of pushing
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
BASE=${BASE:-unified}
BENCH=${BENCH:-$(cd "$ROOT/../.." && pwd)}
BRANCH=sync/upstream
ISSUE="Upstream sync needs a hand"
OUT=$(mktemp -d)
FAILED=0

open_pr() {
	gh pr list --repo "$REPO" --head "$BRANCH" --base "$BASE" --state open --json url --jq '.[0].url // empty'
}

issue_number() {
	gh issue list --repo "$REPO" --state open --search "\"$ISSUE\" in:title" --json number,title \
		--jq ".[] | select(.title == \"$ISSUE\") | .number" | head -1
}

ask_for_a_hand() {
	{ echo "$1 ($(date -u +%F))."; echo; cat "$OUT/merge.md"; } > "$OUT/issue.md"
	if [[ -n ${DRY_RUN:-} ]]; then cat "$OUT/issue.md"; return; fi
	local number
	number=$(issue_number)
	if [[ -n $number ]]; then
		gh issue edit "$number" --repo "$REPO" --body-file "$OUT/issue.md" > /dev/null
	else
		gh issue create --repo "$REPO" --title "$ISSUE" --body-file "$OUT/issue.md" > /dev/null
	fi
}

all_clear() {
	local number
	number=$(issue_number)
	if [[ -n $number && -z ${DRY_RUN:-} ]]; then
		gh issue close "$number" --repo "$REPO" --comment "Every source merged cleanly on $(date -u +%F)." > /dev/null
	fi
}

in_bench() {
	(cd "$BENCH/sites" && "$BENCH/env/bin/python" "$@")
}

install_env() {
	local dev
	dev=$(python3 -c 'import tomllib; print(" ".join(k + v for k, v in tomllib.load(open("pyproject.toml", "rb"))["tool"]["bench"]["dev-dependencies"].items()))')
	uv pip install --python "$BENCH/env/bin/python" --editable "$ROOT" $dev
}

layer_tests() {
	local failed=0 file module
	for file in $(find frappe/web frappe/analytics frappe/ai frappe/ui -name 'test_*.py' | sort); do
		module=${file%.py}
		module=${module//\//.}
		if ! in_bench -m frappe.utils.bench_helper frappe --site "$TEST_SITE" run-tests --module "$module" > "$OUT/test.log" 2>&1; then
			failed=1
			echo "FAILED $module"
			tail -30 "$OUT/test.log"
		fi
	done
	return $failed
}

check() {
	local name=$1
	shift
	if "$@" > "$OUT/$name.log" 2>&1; then
		echo "| $name | passed |" >> "$OUT/checks.md"
		return
	fi
	FAILED=1
	echo "| $name | **failed** |" >> "$OUT/checks.md"
	{ echo; echo "<details><summary>$name</summary>"; echo; echo '```'; tail -60 "$OUT/$name.log"; echo '```'; echo "</details>"; } >> "$OUT/failures.md"
}

# a failed lookup must not read as "no PR": the force-push below would overwrite its branch
pr=$(open_pr) || exit 1
if [[ -n $pr ]]; then
	echo "$pr is still open; merge or close it first."
	exit 0
fi
git switch --quiet -C "$BRANCH"
python3 unification/sync.py merge --skip-conflicts > "$OUT/merge.md" 2>&1
status=$?
cat "$OUT/merge.md"
case $status in
	0) all_clear ;;
	2) ask_for_a_hand "These sources conflict, so the sync set them aside" ;;
	*) ask_for_a_hand "The sync stopped with an error"; exit 1 ;;
esac
if [[ $(git rev-parse HEAD) == $(git rev-parse "origin/$BASE") ]]; then
	echo "Nothing new merged."
	exit 0
fi

printf '| Check | Result |\n| --- | --- |\n' > "$OUT/checks.md"
: > "$OUT/failures.md"
check env install_env
check imports in_bench "$ROOT/unification/check_imports.py"
check build bash -c "yarn --cwd studio install --frozen-lockfile --non-interactive && yarn --cwd studio build"
check migrate in_bench -m frappe.utils.bench_helper frappe --site "$TEST_SITE" migrate
check tests layer_tests

{
	echo "Upstream changes merged by \`unification/sync.py\` on $(date -u +%F)."
	if ((status == 2)); then echo "Sources that conflict were set aside: see the \"$ISSUE\" issue."; fi
	printf '\n## Checks\n\n'
	cat "$OUT/checks.md" "$OUT/failures.md"
	echo
	cat "$OUT/merge.md"
} | head -c 60000 > "$OUT/pr.md"

if [[ -n ${DRY_RUN:-} ]]; then
	cat "$OUT/pr.md"
	exit 0
fi
git push --quiet --force origin "$BRANCH"
draft=()
if ((FAILED)); then draft=(--draft); fi
gh pr create --repo "$REPO" --base "$BASE" --head "$BRANCH" "${draft[@]}" \
	--title "chore(unification): sync upstream $(date -u +%F)" --body-file "$OUT/pr.md"
