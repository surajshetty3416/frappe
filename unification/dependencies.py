"""Carry an app's dependency changes into the unified pyproject.toml and studio/package.json.

An app moving a shared dependency forward moves it here too; one moving it back, or below what
another layer needs, leaves it. Whatever can't be compared is left as a note for a person.
"""

import json
import re
import tomllib

NPM_SECTIONS = ("dependencies", "devDependencies")


def floor(spec):
	"""The lowest version a spec allows, comparable; None when it names no version."""
	match = re.search(r"(\d+(?:\.\d+)*)(-?[a-zA-Z][\w.]*)?", spec)
	if not match:
		return None
	numbers = [int(part) for part in match[1].split(".")]
	return (*(numbers + [0] * 4)[:4], 0 if match[2] else 1)


def newer(wanted, have):
	wanted, have = floor(wanted), floor(have)
	return None if None in (wanted, have) else wanted > have


def requirement(text):
	"""(normalised name, version spec) of a Python requirement."""
	name = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", text)[0]
	spec = re.sub(r"^\s*\[[^\]]*\]", "", text[len(name) :])
	return re.sub(r"[-_.]+", "-", name).lower(), spec


def python_requirements(text):
	lines = tomllib.loads(text).get("project", {}).get("dependencies", [])
	return {requirement(line)[0]: line for line in lines}


def port(base, theirs, target):
	if target.name == "package.json":
		return port_npm(json.loads(base), json.loads(theirs), target)
	return port_python(python_requirements(base), python_requirements(theirs), target)


def port_python(before, after, target):
	text, notes = target.read_text(), []
	current = python_requirements(text)
	for name, wanted in after.items():
		if before.get(name) == wanted:
			continue
		have = current.get(name)
		if have is None:
			text = add_python(text, wanted)
			notes.append(f"added {wanted}")
		elif decide(requirement(wanted)[1], requirement(have)[1], notes, wanted, have):
			text = text.replace(f'"{have}"', f'"{wanted}"', 1)
	notes += [f"upstream dropped {before[name]}, kept here" for name in before.keys() - after.keys() if name in current]
	target.write_text(text)
	return notes


def add_python(text, wanted):
	start = text.index("\ndependencies = [\n")
	end = text.index("\n]", start)
	return f'{text[:end]}\n    "{wanted}",{text[end:]}'


def port_npm(before, after, target):
	root, notes = json.loads(target.read_text()), []
	for section in NPM_SECTIONS:
		for name, wanted in after.get(section, {}).items():
			if before.get(section, {}).get(name) == wanted:
				continue
			home = next((part for part in NPM_SECTIONS if name in root.get(part, {})), None)
			if home is None:
				root.setdefault(section, {})[name] = wanted
				root[section] = dict(sorted(root[section].items()))
				notes.append(f"added {name}@{wanted}")
			elif decide(wanted, root[home][name], notes, f"{name}@{wanted}", f"{name}@{root[home][name]}"):
				root[home][name] = wanted
	target.write_text(json.dumps(root, indent="\t") + "\n")
	return notes


def decide(wanted, have, notes, wanted_label, have_label):
	"""True when wanted should replace have; notes what happened either way."""
	verdict = newer(wanted, have)
	if verdict is None:
		notes.append(f"upstream wants {wanted_label}, here {have_label}: compare by hand")
	elif verdict:
		notes.append(f"{have_label} to {wanted_label}")
	return bool(verdict)
