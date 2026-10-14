#!/usr/bin/env bash
# Merge the upstream changes that merge cleanly onto the open sync PR, or into a new PR against
# $BASE when none is open, check the result, and describe everything the PR carries. A source
# that conflicts is set aside and listed in one "Upstream sync needs a hand" issue.
#
# Starts in a worktree reset to origin/$BASE (systemd/unification-sync.service does that).
#
#   REPO       owner/name of the repo behind the remote "origin", where the PR goes
#   BASE       the branch to merge into (unified)
#   BENCH      the bench this worktree is apps/frappe of (default ../..): its env/ is reinstalled
#              from the worktree, and TEST_SITE in its sites/ is one the tests may change
#   DRY_RUN=1  print the PR and issue instead of pushing
set -uo pipefail
# switching to the open PR's branch rewrites this file, and bash reads a script as it runs
if [[ -z ${SYNC_PR_COPY:-} ]]; then
	copy=$(mktemp)
	cp "$0" "$copy"
	SYNC_PR_COPY=1 exec bash "$copy" "$@"
fi
ROOT=$(git rev-parse --show-toplevel)
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

# a bench's worker: test jobs left queued pile up across runs until frappe refuses to enqueue
start_worker() {
	in_bench -m frappe.utils.bench_helper frappe purge-jobs --site "$TEST_SITE" > /dev/null
	(cd "$BENCH/sites" && exec "$BENCH/env/bin/python" -m frappe.utils.bench_helper frappe worker) > "$OUT/worker.log" 2>&1 &
	WORKER=$!
	trap 'kill "$WORKER" 2>/dev/null' EXIT
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

# start from the open PR's branch with $BASE merged in, so it stays mergeable and runs the
# current tooling; a failed lookup must not read as "no PR", or the force-push would drop its commits
pr=$(open_pr) || exit 1
checked=""
if [[ -n $pr ]]; then
	checked=$(gh pr view "$pr" --repo "$REPO" --json body --jq .body | sed -n 's/^Checked at `\([0-9a-f]*\)`.*/\1/p' | head -1)
	git fetch --quiet origin "$BRANCH" || exit 1
	git switch --quiet -C "$BRANCH" "origin/$BRANCH"
	if ! git merge --quiet --no-edit -m "chore(unification): bring $BRANCH up to $BASE" "origin/$BASE" > /dev/null; then
		git merge --abort
		echo "$pr no longer merges with $BASE: merge $BASE into $BRANCH by hand." > "$OUT/merge.md"
		ask_for_a_hand "The sync can't add to the open PR"
		exit 1
	fi
else
	git switch --quiet -C "$BRANCH" "origin/$BASE"
fi
start=$(git rev-parse HEAD)
python3 unification/sync.py merge --skip-conflicts > "$OUT/merge.md" 2>&1
status=$?
cat "$OUT/merge.md"
case $status in
	0) all_clear ;;
	2) ask_for_a_hand "These sources conflict, so the sync set them aside" ;;
	*) ask_for_a_hand "The sync stopped with an error"; exit 1 ;;
esac
# a new PR needs something merged; an open one needs checking whenever its branch moved, by
# this run or by hand
head=$(git rev-parse HEAD)
if [[ ( -z $pr && $head == "$start" ) || ( -n $pr && $head == "$checked" ) ]]; then
	echo "Nothing new to check."
	exit 0
fi

printf '| Check | Result |\n| --- | --- |\n' > "$OUT/checks.md"
: > "$OUT/failures.md"
check env install_env
start_worker
check imports in_bench "$ROOT/unification/check_imports.py"
check build bash -c "yarn --cwd studio install --frozen-lockfile --non-interactive && yarn --cwd studio build"
check migrate in_bench -m frappe.utils.bench_helper frappe --site "$TEST_SITE" migrate
check tests layer_tests

python3 unification/sync.py report "origin/$BASE" > "$OUT/report.md" 2>&1
{
	echo "Upstream changes merged by \`unification/sync.py\`."
	if ((status == 2)); then echo "Sources that conflict wait in the \"$ISSUE\" issue."; fi
	echo
	sed '/^## Changes$/,$d' "$OUT/report.md"
	printf '## Checks\n\nChecked at `%s` on %s UTC.\n\n' "$head" "$(date -u '+%F %H:%M')"
	cat "$OUT/checks.md" "$OUT/failures.md"
	echo
	sed -n '/^## Changes$/,$p' "$OUT/report.md"
} | head -c 60000 > "$OUT/pr.md"

if [[ -n ${DRY_RUN:-} ]]; then
	cat "$OUT/pr.md"
	exit 0
fi
if [[ -n $pr ]]; then
	git push --quiet origin "$BRANCH"
	gh pr edit "$pr" --repo "$REPO" --body-file "$OUT/pr.md" > /dev/null
	ready=()
	if ((FAILED)); then ready=(--undo); fi
	gh pr ready "$pr" --repo "$REPO" "${ready[@]}" > /dev/null 2>&1
	exit 0
fi
git push --quiet --force origin "$BRANCH"
draft=()
if ((FAILED)); then draft=(--draft); fi
gh pr create --repo "$REPO" --base "$BASE" --head "$BRANCH" "${draft[@]}" \
	--title "chore(unification): sync upstream" --body-file "$OUT/pr.md"
