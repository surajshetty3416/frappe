"""Rewrite upstream builder/insights/flow/studio references to the unified layout.

usage: python unification/port_rewrite.py <file> [<file> ...]   (paths from the repo root)
Rewrites in place and prints the lines that still name an old app, for a person to look at.
sync.py runs the same rewrite over every file a merge brings in.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYERS = {"builder": "web", "insights": "analytics", "flow": "ai", "studio": "ui"}
MODULES = {"Builder": "Web", "Insights": "Analytics", "Flow": "AI", "Studio": "UI"}
ALIASES = {"builder": "@web/", "studio": "@ui/"}  # the upstream frontends whose "@/" meant their src


def modules(layer):
	"""Top-level names inside a layer package, so `builder.css` or `flow.json` stay put."""
	return {path.stem if path.suffix == ".py" else path.name for path in (ROOT / "frappe" / layer).iterdir()}


NAMES = {old: modules(new) for old, new in LAYERS.items()}
ALT = "|".join(LAYERS)
DOTTED = re.compile(rf"(?<![\w.])(?P<app>{ALT})\.(?:(?P=app)\.)?(?P<head>\w+)(?P<tail>(?:\.\w+)*)")
REVIEW = re.compile(
	rf"get_app_path\(\s*[\"'](?:{ALT})[\"']|[\"'](?:{ALT})[\"']\s*(?:in|==|!=)|(?<![\w/])/(?:builder|insights|flow)(?:/|[\"'`])|/studio/app/"
	rf"|\bapp(?:_name)?\s*(?::\s*str\s*)?=\s*[\"'](?:{ALT})[\"']"
)


def dotted(match):
	app, head = match["app"], match["head"]
	if head not in NAMES[app]:
		return match[0]
	return f"frappe.{LAYERS[app]}.{head}{match['tail']}"


def layer_of(path):
	parts = path.split("/")
	return parts[1] if len(parts) > 2 and parts[0] in ("frappe", "studio") and parts[1] in LAYERS.values() else None


def rewrite(text, path):
	for old, new in LAYERS.items():
		text = re.sub(rf"^(\s*)import {old}$", rf"\1from frappe import {new} as {old}", text, flags=re.M)
		text = re.sub(rf"^(\s*)from {old} import ", rf"\1from frappe.{new} import ", text, flags=re.M)
		text = text.replace(f"/assets/{old}/frontend/", "/assets/frappe/studio/")
		text = text.replace(f"/assets/{old}/", f"/assets/frappe/{new}/")
		text = text.replace(f'"{old}/templates/', f'"{new}/templates/')
	# dotted paths in `from x import`, in string literals and after /api/method/
	in_place = rf"(?<=from )(?:{ALT})\.[\w.]+(?= import)|(?<=[\"'`])(?:{ALT})\.[\w.]+|(?<=/api/method/)(?:{ALT})\.[\w.]+"
	text = re.sub(in_place, lambda match: DOTTED.sub(dotted, match[0]), text)
	text = re.sub(
		r'(["\'])templates/generators/(webpage|studio_renderer|app_renderer)',
		lambda m: f"{m[1]}{'web' if m[2] == 'webpage' else 'ui'}/templates/generators/{m[2]}",
		text,
	)
	for old, new in MODULES.items():
		text = text.replace(f'"module": "{old}"', f'"module": "{new}"')
	if layer := layer_of(path):
		text = re.sub(r"(?<![\w/.-])(?:\./)?frontend/(?=src2?/|public/)", f"studio/{layer}/", text)
	layer = next((old for old in ALIASES if f"/{LAYERS[old]}/" in f"/{path}"), None)
	if layer and path.startswith("studio/"):
		text = re.sub(r"(?<=[\"'`])@/", ALIASES[layer], text)
	return text


def main(paths):
	for name in paths:
		path = ROOT / name
		text = path.read_text()
		new = rewrite(text, name)
		if new != text:
			path.write_text(new)
		for number, line in enumerate(new.splitlines(), 1):
			if REVIEW.search(line):
				print(f"{name}:{number}: {line.strip()}")


if __name__ == "__main__":
	main(sys.argv[1:])
