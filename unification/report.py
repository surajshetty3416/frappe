"""What a sync merged, as markdown: a summary table, then each source's commits."""

import re


def qualified(subject, slug):
	"""In this fork GitHub reads a bare `#306` as frappe/frappe#306, whichever repo it came from."""
	return re.sub(r"(?<![\w/.-])#(\d+)", rf"{slug}#\1", subject)


def cell(text):
	return text.replace("|", "\\|")


def places(paths, limit=3):
	if not paths:
		return "not carried over"
	folders = sorted({"/".join(path.split("/")[:3]) for path in paths})
	shown = ", ".join(f"`{folder}`" for folder in folders[:limit])
	return shown + (f" and {len(folders) - limit} more" if len(folders) > limit else "")


class Entry:
	"""One source's part of a sync."""

	def __init__(self, source, commits, review):
		self.source = source
		self.commits = commits
		self.review = review
		self.paths = {commit.sha: source.paths(commit.sha) for commit in commits}
		self.result = ""
		self.conflicts = []

	@property
	def merged(self):
		return not self.conflicts

	@property
	def when(self):
		dates = sorted(commit.date for commit in self.commits)
		return dates[0] if dates[0] == dates[-1] else f"{dates[0]} to {dates[-1]}"

	def row(self):
		source = self.source
		return f"| {source.title} | {source.layer} | {len(self.commits)} | {self.when} | {self.result} |"

	def line(self, commit):
		link = f"[`{commit.sha[:8]}`]({self.source.url}/commit/{commit.sha})"
		what = cell(qualified(commit.subject, self.source.slug))
		return f"| {commit.date} | {link} {what} | {places(self.paths[commit.sha])} |"

	def section(self):
		lines = [f"### {self.source.title} ({self.source.layer})", "", "| When | What | Where |", "| --- | --- | --- |"]
		lines += [self.line(commit) for commit in self.commits]
		if self.review:
			lines += ["", "New lines that still name an old app, to look at:", ""]
			lines += [f"- `{line}`" for line in self.review]
		if self.conflicts:
			lines += ["", "Conflicts in:", ""] + [f"- `{path}`" for path in self.conflicts]
		return "\n".join(lines)


def render(entries):
	if not entries:
		return "Nothing new upstream."
	summary = ["| Source | Layer | Commits | When | Result |", "| --- | --- | --- | --- | --- |"]
	summary += [entry.row() for entry in entries]
	sections = "\n\n".join(entry.section() for entry in entries)
	return "## Summary\n\n" + "\n".join(summary) + "\n\n## Changes\n\n" + sections + "\n"
