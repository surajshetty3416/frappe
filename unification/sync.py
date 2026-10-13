"""Keep the unified frappe in step with the repos it was merged from.

From the frappe repo root, on the branch to update, with a clean tree:

	python3 unification/sync.py status             what each source has that isn't merged yet
	python3 unification/sync.py merge [source ...]  merge it, one merge commit per source

`merge` stops at the first source that conflicts, with everything else (and the new sources.json)
staged: resolve, commit, and run it again for the rest. With --skip-conflicts it sets that source
aside and goes on with the others. Exit codes: 0 done, 2 conflicts.
"""

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from fnmatch import fnmatch
from pathlib import Path
from typing import NamedTuple

import port_rewrite
import report

ROOT = port_rewrite.ROOT
SOURCES = Path(__file__).with_name("sources.json")
CACHE = Path(os.environ.get("UNIFICATION_CACHE", Path.home() / ".cache" / "frappe-unification"))
FILTER_REPO = ["uvx", "git-filter-repo==2.47.0"] if shutil.which("uvx") else ["git-filter-repo"]
# where the first merge put each upstream path; sources.json "moves" says where they are now
CALLBACK = """
A = b'{app}'
if filename == b'.gitmodules' or filename == b'frappe-ui' or filename.startswith(b'frappe-ui/'):
    return None
if filename == A + b'/' + A + b'/__init__.py':
    return None
if filename.startswith(A + b'/' + A + b'/'):
    return b'frappe/' + A + b'/' + filename[2 * len(A) + 2:]
if filename.startswith(A + b'/'):
    return b'frappe/' + filename
if filename.startswith(b'frontend/'):
    return b'frontend/' + A + b'/' + filename[len(b'frontend/'):]
return b'frappe/' + A + b'/' + filename
"""


def git(*args, cwd=ROOT, check=True):
	result = subprocess.run(["git", *map(str, args)], cwd=cwd, capture_output=True, text=True)
	if check and result.returncode:
		sys.exit(f"git {' '.join(map(str, args[:3]))} failed:\n{result.stderr}")
	return result.stdout.strip()


def unmerged():
	return sorted(set(git("diff", "--name-only", "--diff-filter=U").splitlines()))


def staged():
	return git("diff", "--cached", "--name-only", "--diff-filter=AM", "HEAD").splitlines()


def stage(path, number):
	result = subprocess.run(["git", "show", f":{number}:{path}"], cwd=ROOT, capture_output=True)
	return result.stdout if result.returncode == 0 else None


def added_lines(path):
	diff = git("diff", "-U0", "HEAD", "--", path).splitlines()
	return [line[1:].strip() for line in diff if line.startswith("+") and not line.startswith("+++")]


KEY = "%ae%x1f%at%x1f%ct%x1f%s"


def key(commit, repo):
	"""What a commit and its rewritten copy share: author, both times and subject."""
	return git("log", "-1", f"--format={KEY}", commit, cwd=repo)


def keyed(head, repo):
	lines = git("log", f"--format=%H%x1f{KEY}", head, cwd=repo).splitlines()
	return {line.split("\x1f", 1)[1]: line.split("\x1f", 1)[0] for line in lines}


def ported(data, path):
	try:
		return port_rewrite.rewrite(data.decode(), path).encode()
	except UnicodeDecodeError:
		return data


def merge_file(path, base, theirs):
	"""Three-way merge upstream's change into the file at path; False if it left conflict markers."""
	with tempfile.TemporaryDirectory() as folder:
		Path(folder, "base").write_bytes(base)
		Path(folder, "upstream").write_bytes(theirs)
		labels = ["-L", "unified", "-L", "base", "-L", "upstream"]
		merge = ["git", "merge-file", *labels, ROOT / path, Path(folder, "base"), Path(folder, "upstream")]
		return subprocess.run(merge).returncode == 0


def has_markers(path):
	text = (ROOT / path).read_text(errors="replace")
	return any(line.startswith(("<<<<<<< ", ">>>>>>> ")) for line in text.splitlines())


class Commit(NamedTuple):
	sha: str
	date: str
	subject: str


class Source:
	"""An upstream merged as it is: frappe itself."""

	layer = "core"

	def __init__(self, name, config):
		self.name = name
		self.config = config
		self.ref = f"refs/unification/{name}"
		self.repo = ROOT

	@property
	def url(self):
		return self.config["repo"].removesuffix(".git")

	@property
	def slug(self):
		return self.url.removeprefix("https://github.com/")

	@property
	def title(self):
		return f"{self.slug}@{self.config['branch']}"

	def fetch(self):
		git("fetch", "--quiet", "--no-tags", self.config["repo"], f"+refs/heads/{self.config['branch']}:{self.ref}")

	def head(self):
		return git("rev-parse", self.ref)

	def pending(self):
		"""The upstream commits not merged yet, oldest first."""
		pending = f"{self.config['commit']}..{self.head()}"
		log = git("log", "--no-merges", "--reverse", "--format=%H%x1f%cs%x1f%s", pending, cwd=self.repo)
		return [Commit(*line.split("\x1f", 2)) for line in log.splitlines()]

	def paths(self, commit):
		"""What an upstream commit touched, at its paths here."""
		return git("diff-tree", "--no-commit-id", "--name-only", "-r", commit, cwd=self.repo).splitlines()

	def prepare(self):
		"""Leave the commit to merge at self.ref, and record it."""
		self.config["commit"] = self.head()

	def settle(self):
		"""Adapt what the merge brought in. Returns (lines to look at, files still conflicted)."""
		return [], unmerged()


class App(Source):
	"""An app merged as a layer of frappe, through the path rewrite."""

	def __init__(self, name, config, ignore):
		super().__init__(name, config)
		self.layer = port_rewrite.LAYERS[name]
		self.ignore = ignore
		self.repo = CACHE / f"{name}.git"
		self.work = CACHE / name

	def fetch(self):
		branch = self.config["branch"]
		if not self.repo.exists():
			CACHE.mkdir(parents=True, exist_ok=True)
			git("clone", "--quiet", "--bare", "--no-tags", "--branch", branch, self.config["repo"], self.repo, cwd=CACHE)
		git("fetch", "--quiet", "--no-tags", "origin", f"+refs/heads/{branch}:refs/heads/{branch}", cwd=self.repo)

	def head(self):
		return git("rev-parse", self.config["branch"], cwd=self.repo)

	def prepare(self):
		"""Rewrite the commits since the last merge onto their parents' copies in the merged history."""
		branch, parents = self.config["branch"], self.merged_parents()
		self.clone()
		parents_callback = f"PARENTS = {parents!r}\ncommit.parents = [PARENTS.get(p, p) for p in commit.parents]"
		rewrite = subprocess.run(
			[*FILTER_REPO, "--force", "--quiet", "--refs", f"{self.config['commit']}..{branch}"]
			+ ["--filename-callback", CALLBACK.format(app=self.name), "--commit-callback", parents_callback],
			cwd=self.work,
			capture_output=True,
			text=True,
		)
		if rewrite.returncode:
			sys.exit(f"{self.name}: git-filter-repo failed:\n{rewrite.stdout}{rewrite.stderr}")
		rewritten = git("rev-parse", branch, cwd=self.work)
		git("merge-base", "--is-ancestor", self.config["rewritten"], rewritten, cwd=self.work)
		git("fetch", "--quiet", self.work, f"+refs/heads/{branch}:{self.ref}")
		self.config.update(commit=self.head(), rewritten=rewritten)

	def paths(self, commit):
		lines = (self.work / ".git" / "filter-repo" / "commit-map").read_text().splitlines()[1:]
		copy = dict(line.split() for line in lines).get(commit, "0" * 40)
		if set(copy) == {"0"}:
			return []
		names = git("diff-tree", "--no-commit-id", "--name-only", "-r", copy, cwd=self.work).splitlines()
		return [self.moved(name) or name for name in names if not self.ignored(name)]

	def clone(self):
		"""A scratch copy of the upstream branch that also holds the merged history to build on."""
		shutil.rmtree(self.work, ignore_errors=True)
		git("clone", "--quiet", "--no-local", "--no-tags", "--branch", self.config["branch"], self.repo, self.work, cwd=CACHE)
		git("update-ref", f"{self.ref}-merged", self.config["rewritten"])
		git("fetch", "--quiet", "--no-tags", ROOT, f"{self.ref}-merged:refs/merged", cwd=self.work)

	def merged_parents(self):
		"""{upstream commit: its copy here} for each commit outside the new ones that they build on."""
		merged = keyed(self.config["rewritten"], ROOT)
		anchor = self.config["commit"]
		if merged.get(key(anchor, self.repo)) != self.config["rewritten"]:
			sys.exit(f"{self.name}: {self.config['rewritten'][:10]} isn't the merged copy of {anchor[:10]}.")
		lines = git("rev-list", "--parents", f"{anchor}..{self.head()}", cwd=self.repo).splitlines()
		new = {line.split()[0] for line in lines}
		outside = {parent for line in lines for parent in line.split()[1:] if parent not in new}
		return {parent.encode(): self.merged_copy(parent, merged).encode() for parent in outside}

	def merged_copy(self, commit, merged):
		# the first rewrite dropped commits left empty (submodule bumps); their children sit on their parent
		while key(commit, self.repo) not in merged:
			commit = git("rev-parse", f"{commit}^", cwd=self.repo)
		return merged[key(commit, self.repo)]

	def settle(self):
		carried = []
		for path in unmerged():
			if not (self.drop(path) or self.remerge(path)) and (new := self.carry(path)):
				carried.append(new)
		homeless = [path for path in staged() if self.is_old(path) and not self.rehome(path)]
		review = self.port([*staged(), *carried])
		self.regenerate()
		return review, [*unmerged(), *homeless, *(path for path in carried if has_markers(path))]

	def remerge(self, path):
		"""Merge again with upstream's sides renamed first, so only real edits conflict. False if not ours to merge."""
		base, ours, theirs = stage(path, 1), stage(path, 2), stage(path, 3)
		if None in (base, ours):
			return False
		if theirs is None:
			if ported(base, path) != ours:
				return False
			git("rm", "--quiet", path)
			return True
		(ROOT / path).write_bytes(ours)
		if merge_file(path, ported(base, path), ported(theirs, path)):
			git("add", path)
		return True

	def carry(self, path):
		"""Merge an upstream change into a file rename detection lost track of; returns its path here."""
		new = self.moved(path)
		base, ours, theirs = stage(path, 1), stage(path, 2), stage(path, 3)
		if ours is not None or None in (new, base, theirs) or not (ROOT / new).is_file():
			return None
		merge_file(new, ported(base, new), ported(theirs, new))
		git("rm", "--quiet", "--cached", path)
		(ROOT / path).unlink(missing_ok=True)
		return new

	def moved(self, path):
		for old, new in self.config["moves"].items():
			if path.startswith(old):
				return new + path[len(old) :]

	def is_old(self, path):
		return path.startswith((f"frappe/{self.name}/", f"frontend/{self.name}/"))

	def ignored(self, path):
		return any(fnmatch(path, pattern) for pattern in self.ignore)

	def drop(self, path):
		"""Keep repo tooling the unification removed (CI, lint, lockfiles) removed."""
		if stage(path, 2) is not None or not self.ignored(path):
			return False
		git("rm", "--quiet", path)
		return True

	def rehome(self, path):
		"""Move a file upstream added where the app's folders used to be; False if it has no home."""
		if self.ignored(path):
			git("rm", "--quiet", "--force", path)
			return True
		new = self.moved(path)
		if not new or (ROOT / new).exists() or not (ROOT / new).parent.is_dir():
			return False
		git("mv", path, new)
		return True

	def port(self, paths):
		"""Rewrite old names in the merged files; returns the new lines that still need a person."""
		review = []
		for path in paths:
			try:
				text = (ROOT / path).read_text()
			except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
				continue
			if (new := port_rewrite.rewrite(text, path)) != text:
				(ROOT / path).write_text(new)
			if not has_markers(path):
				git("add", path)
			review += [f"{path}: {line}" for line in added_lines(path) if port_rewrite.REVIEW.search(line)]
		return review

	def regenerate(self):
		for command in self.config.get("regenerate", []):
			subprocess.run(shlex.split(command), cwd=ROOT, check=True, capture_output=True)
		conflicted = unmerged()
		for path in git("diff", "--name-only").splitlines():
			if path not in conflicted and not has_markers(path):
				git("add", path)


def load():
	data = json.loads(SOURCES.read_text())

	def source(name, config):
		return App(name, config, data["ignore"]) if "rewritten" in config else Source(name, config)

	return data, {name: source(name, config) for name, config in data["sources"].items()}


def save(data):
	SOURCES.write_text(json.dumps(data, indent="\t") + "\n")
	git("add", SOURCES)


def status(sources):
	for source in sources:
		source.fetch()
		pending = source.pending()
		print(f"## {source.title}: {len(pending)} new commit{'' if len(pending) == 1 else 's'}\n")
		for commit in pending:
			print(f"- {commit.date} {commit.sha[:10]} {report.qualified(commit.subject, source.slug)}")
		print()


def merge(data, source, skip_conflicts):
	"""Merge one source in a commit of its own; returns its report entry, or None if nothing is new."""
	commits = source.pending()
	if not commits:
		return None
	before = dict(source.config)
	source.prepare()
	subprocess.run(["git", "-c", "merge.directoryRenames=true", "merge", "--no-ff", "--no-commit", source.ref], cwd=ROOT, capture_output=True)
	review, conflicts = source.settle()
	entry = report.Entry(source, commits, review)
	entry.conflicts = conflicts
	if conflicts and skip_conflicts:
		skip(source, before)
		entry.result = f"set aside: run `sync.py merge {source.name}`"
		return entry
	save(data)
	Path(git("rev-parse", "--path-format=absolute", "--git-path", "MERGE_MSG")).write_text(message(data, source, commits))
	if conflicts:
		entry.result = "conflicts, merge in progress"
		return entry
	git("commit", "--quiet", "--no-verify", "--no-edit")
	entry.result = f"merged as {git('rev-parse', '--short', 'HEAD')}"
	return entry


def skip(source, before):
	git("merge", "--abort")
	git("reset", "--hard", "--quiet", "HEAD")
	source.config.clear()
	source.config.update(before)


def stop(source):
	print("\nResolve the conflicts listed above and `git add` them.", end=" ")
	print("".join(f"Run `{command}`. " for command in source.config.get("regenerate", [])), end="")
	print("Then `git commit` (the message is ready) and run merge again for the other sources.")
	sys.exit(2)


def message(data, source, commits):
	body = "\n".join(f"- {report.qualified(commit.subject, source.slug)}" for commit in commits)
	trailers = "\n".join(data["commit_trailers"])
	return f"chore(unification): merge {source.title} up to {source.config['commit'][:10]}\n\n{body}\n\n{trailers}\n"


def main(command="status", *args):
	data, sources = load()
	names = [arg for arg in args if not arg.startswith("--")]
	chosen = [sources[name] for name in names] if names else list(sources.values())
	if command == "status":
		return status(chosen)
	if git("status", "--porcelain", "--untracked-files=no") or git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False):
		sys.exit("Commit or set aside local changes, and finish any merge in progress, first.")
	entries = []
	for source in chosen:
		source.fetch()
		if entry := merge(data, source, "--skip-conflicts" in args):
			entries.append(entry)
		if entry and entry.conflicts and "--skip-conflicts" not in args:
			print(report.render(entries))
			stop(source)
	print(report.render(entries))
	sys.exit(0 if all(entry.merged for entry in entries) else 2)


if __name__ == "__main__":
	main(*sys.argv[1:])
