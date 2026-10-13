"""Keep the unified frappe in step with the repos it was merged from.

From the frappe repo root, on the branch to update, with a clean tree:

	python3 unification/sync.py status             what each source has that isn't merged yet
	python3 unification/sync.py merge [source ...]  merge it, one merge commit per source

`merge` stops at the first source that conflicts, with everything else (and the new sources.json)
staged: resolve, commit, and run it again for the rest. Exit codes: 0 done, 2 conflicts.
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

import port_rewrite

ROOT = port_rewrite.ROOT
SOURCES = Path(__file__).with_name("sources.json")
CACHE = Path(os.environ.get("UNIFICATION_CACHE", Path.home() / ".cache" / "frappe-unification"))
# the rewrite's output must match the merged history hash for hash, so its version is pinned
FILTER_REPO = ["uvx", "git-filter-repo==2.47.0"] if shutil.which("uvx") else ["git-filter-repo"]
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


def ported(data, path):
	try:
		return port_rewrite.rewrite(data.decode(), path).encode()
	except UnicodeDecodeError:
		return data


def has_markers(path):
	text = (ROOT / path).read_text(errors="replace")
	return any(line.startswith(("<<<<<<< ", ">>>>>>> ")) for line in text.splitlines())


class Source:
	"""An upstream merged as it is: frappe itself."""

	def __init__(self, name, config):
		self.name = name
		self.config = config
		self.ref = f"refs/unification/{name}"
		self.repo = ROOT

	@property
	def title(self):
		repo = self.config["repo"].removeprefix("https://github.com/").removesuffix(".git")
		return f"{repo}@{self.config['branch']}"

	def fetch(self):
		git("fetch", "--quiet", "--no-tags", self.config["repo"], f"+refs/heads/{self.config['branch']}:{self.ref}")

	def head(self):
		return git("rev-parse", self.ref)

	def pending(self):
		pending = f"{self.config['commit']}..{self.head()}"
		return git("log", "--no-merges", "--format=%h %s", pending, cwd=self.repo).splitlines()

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
		head, commits = self.head(), self.rewrite()
		if commits.get(self.config["commit"]) != self.config["rewritten"]:
			sys.exit(
				f"{self.name}: the rewrite no longer turns {self.config['commit'][:10]} into "
				f"{self.config['rewritten'][:10]}, so merging would bring its history in a second time. "
				"Check the git-filter-repo version and CALLBACK."
			)
		git("fetch", "--quiet", self.work, f"+refs/heads/{self.config['branch']}:{self.ref}")
		self.config.update(commit=head, rewritten=commits[head])

	def rewrite(self):
		"""Rewrite a fresh copy of the branch to the paths it was merged at; returns {old: new} commits."""
		shutil.rmtree(self.work, ignore_errors=True)
		branch = self.config["branch"]
		git("clone", "--quiet", "--no-local", "--no-tags", "--branch", branch, self.repo, self.work, cwd=CACHE)
		callback = CALLBACK.format(app=self.name)
		subprocess.run([*FILTER_REPO, "--force", "--quiet", "--filename-callback", callback], cwd=self.work, check=True)
		lines = (self.work / ".git" / "filter-repo" / "commit-map").read_text().splitlines()[1:]
		return dict(line.split() for line in lines)

	def settle(self):
		carried = []
		for path in unmerged():
			if not (self.take_upstream(path) or self.drop(path)) and (new := self.carry(path)):
				carried.append(new)
		homeless = [path for path in staged() if self.is_old(path) and not self.rehome(path)]
		review = self.port([*staged(), *carried])
		self.regenerate()
		return review, [*unmerged(), *homeless, *(path for path in carried if has_markers(path))]

	def moved(self, path):
		for old, new in self.config["moves"].items():
			if path.startswith(old):
				return new + path[len(old) :]

	def is_old(self, path):
		return path.startswith((f"frappe/{self.name}/", f"frontend/{self.name}/"))

	def ignored(self, path):
		return any(fnmatch(path, pattern) for pattern in self.ignore)

	def take_upstream(self, path):
		"""Where the unification only renamed things in a file, upstream's side is the answer."""
		base, ours, theirs = stage(path, 1), stage(path, 2), stage(path, 3)
		if None in (base, ours) or ported(base, path) != ours:
			return False
		if theirs is None:
			git("rm", "--quiet", path)
		else:
			(ROOT / path).write_bytes(ported(theirs, path))
			git("add", path)
		return True

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

	def carry(self, path):
		"""Merge an upstream change into a file rename detection lost track of; returns its path here."""
		new = self.moved(path)
		base, ours, theirs = stage(path, 1), stage(path, 2), stage(path, 3)
		if ours is not None or None in (new, base, theirs) or not (ROOT / new).is_file():
			return None
		with tempfile.TemporaryDirectory() as folder:
			Path(folder, "base").write_bytes(base)
			Path(folder, "upstream").write_bytes(theirs)
			labels = ["-L", "unified", "-L", "base", "-L", "upstream"]
			subprocess.run(["git", "merge-file", *labels, ROOT / new, Path(folder, "base"), Path(folder, "upstream")])
		git("rm", "--quiet", "--cached", path)
		(ROOT / path).unlink(missing_ok=True)
		return new

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
		print(f"## {source.title}: {len(pending)} new commit{'' if len(pending) == 1 else 's'}")
		print("".join(f"- {line}\n" for line in pending))


def merge(data, source):
	pending = source.pending()
	if not pending:
		return
	source.prepare()
	print(f"## {source.title}: {len(pending)} new commits")
	subprocess.run(["git", "-c", "merge.directoryRenames=true", "merge", "--no-ff", "--no-commit", source.ref], cwd=ROOT, capture_output=True)
	review, conflicts = source.settle()
	save(data)
	print("".join(f"- look at {line}\n" for line in review))
	Path(git("rev-parse", "--path-format=absolute", "--git-path", "MERGE_MSG")).write_text(message(data, source, pending))
	if conflicts:
		print("Conflicts. Resolve these, `git add` them and `git commit` (the message is ready), then run merge again:")
		print("".join(f"- {path}\n" for path in conflicts))
		sys.exit(2)
	git("commit", "--quiet", "--no-verify", "--no-edit")
	print(f"merged as {git('rev-parse', '--short', 'HEAD')}\n")


def message(data, source, pending):
	body = "\n".join(f"- {line.split(' ', 1)[1]}" for line in pending)
	trailers = "\n".join(data["commit_trailers"])
	return f"chore(unification): merge {source.title} up to {source.config['commit'][:10]}\n\n{body}\n\n{trailers}\n"


def main(command="status", *names):
	data, sources = load()
	chosen = [sources[name] for name in names] if names else list(sources.values())
	if command == "status":
		return status(chosen)
	if git("status", "--porcelain", "--untracked-files=no") or git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False):
		sys.exit("Commit or set aside local changes, and finish any merge in progress, first.")
	for source in chosen:
		source.fetch()
		merge(data, source)


if __name__ == "__main__":
	main(*sys.argv[1:])
