# Unification: builder, insights, flow and studio in frappe

Frappe Builder, Insights, Flow and Studio were merged into this repo, with their full git
history, as **layers** of the `frappe` app. One install of frappe gives all four, and one
single-page app, **Studio**, serves them at `/studio`.

| Layer | Was | Python | Frontend | What it makes |
| --- | --- | --- | --- | --- |
| web | frappe/builder | `frappe/web` | `studio/web` | websites (Builder Page) |
| analytics | frappe/insights | `frappe/analytics` | `studio/analytics` | workbooks, dashboards |
| ai | frappe/flow | `frappe/ai` | `studio/ai` | chats, agents, tools |
| ui | frappe/studio | `frappe/ui` | `studio/ui` | apps (Studio App) |

This file is the map for porting later changes from those four repos. Read "Porting upstream
changes" before touching a merge. The two scripts it runs are in "Scripts" at the end; save them
outside the repo.

## Sources

Each app was merged at the upstream commit below. Its history was first rewritten to the paths
this repo used at merge time (see "The history rewrite"), so the merge's second parent is the
*rewritten* copy of that upstream commit.

| Upstream | Branch | Merged upstream commit | Date | Rewritten commit (merge's 2nd parent) |
| --- | --- | --- | --- | --- |
| frappe/builder | develop | `477481ff78aaae7ef1c7318258f2b3aa159ff6fd` | 2026-10-10 | `c587875347a7014d16b4f7dc9f9d875c00dd0949` |
| frappe/insights | develop | `ef8c48175b5fcd177f4ea08ee51100eb75816f82` | 2026-10-08 | `a721d45ef1d072292d56caa95a154920e9f8308c` |
| frappe/flow | main (no develop) | `b3466bf0624d66ce796fb3c155eb8361739fa7a3` | 2026-10-12 | `dba5b9b949a294e90f494bed7d67e9789a5e8163` |
| frappe/studio | develop | `42491ecdedc01a4d4630503443ed9125ca63887f` | 2026-10-12 | `04f6cec5bc06d4bf0a3b14c256860a12acbb2b8f` |

The four merges sit on frappe develop at `c8d85d6356ca4ef3ec8edfa3340985c3007bfa55`.
Update this table in the same commit as every port.

## Where things moved

Paths in the upstream repos, and where they live now. `<app>/<app>/` is the app's module folder;
it and the package root `<app>/` were flattened into one package.

### Python

| Upstream | Here |
| --- | --- |
| `builder/builder/*`, `builder/*` | `frappe/web/*` |
| `insights/insights/*`, `insights/*` | `frappe/analytics/*` |
| `flow/flow/*`, `flow/*` | `frappe/ai/*` |
| `studio/studio/*`, `studio/*` | `frappe/ui/*` |
| `<app>/<app>/__init__.py` | dropped (the package root's `__init__.py` stays) |
| repo-root files (README, AGENTS.md, docs/, skills/, scripts/, LICENSE) | `frappe/<layer>/` |
| `<app>/public/*` | `frappe/public/<layer>/*`, served at `/assets/frappe/<layer>/` |
| `<app>/www/<spa page>.py` (`_builder.py`, `_insights.py`, `studio.py`, `flow/index.py`) | `frappe/<layer>/shell.py`, now only `get_boot()`; the page is `frappe/www/_studio.py` |
| `builder/www/404.py`, `sitemap.py` | `frappe/web/not_found.py`, `frappe/web/sitemap.py`, called from `frappe/www/404.py` and `frappe/www/sitemap.py` |
| `builder/www/404.html`, `sitemap.xml`, `builder_assets/` | `frappe/www/` |
| `<app>/templates/*` | `frappe/<layer>/templates/*`; Jinja names gain the layer: `templates/generators/webpage.html` is `web/templates/generators/webpage.html` |
| `insights/templates/emails/insights_invitation.html` | `frappe/templates/emails/` |
| `insights/fixtures/*` | `frappe/fixtures/*` |
| `<app>/patches.txt`, `patches/` | stay in the layer (`frappe/<layer>/patches.txt`), read by frappe's patch handler after frappe's own |
| `<app>/locale/` | stays in the layer; not wired into frappe's translations yet |
| `flow/commands`, `studio/commands` | `frappe/commands/flow.py`, `frappe/commands/studio.py` |
| flow `realtime/handlers.js` | `realtime/flow_handlers.js`, called from `realtime/handlers.js` |
| flow `harness/` (the `frappe-flow` distribution and `@flow/ui-core`) | repo root `harness/` |
| `pyproject.toml` dependencies | merged into the root `pyproject.toml` |
| CI, lint, docker, commitlint, crowdin, lockfiles, the `frappe-ui` submodule | dropped |

Python names: `builder.builder.x` and `builder.x` are `frappe.web.x`; likewise `frappe.analytics`,
`frappe.ai`, `frappe.ui`. Insights code that did `import insights` (for `insights.warehouse` and
friends) now does `from frappe import analytics as insights`. Modules are **Web, Analytics, AI,
UI**; DocType names did not change (Builder Page, Insights Workbook, Flow Agent, Studio App...).

### Frontend

| Upstream | Here |
| --- | --- |
| builder `frontend/*` | `studio/web/*` |
| insights `frontend/*` (source in `src2`) | `studio/analytics/*` |
| studio `frontend/*` | `studio/ui/*` |
| flow `frontend/*` | `studio/ai/*`; its root `tailwind.config.js` is `studio/ai/tailwind.config.js` |
| each app's `index.html`, `main.ts`, `vite.config.*`, `postcss.config.js`, `package.json`, `yarn.lock`, `tsconfig.json` | gone: `studio/` has one of each |
| `frontend/public/*` assets | `studio/public/*`, built to `/assets/frappe/studio/` (logos renamed: `builder_logo.png`, `insights-logo.png`, `studio-logo.svg`, `studio-favicon.png`) |
| studio `renderer.html` | `frappe/ui/templates/generators/studio_renderer.html`; the renderer is the `ui-renderer` entry of `studio/vite.config.js` |
| the `@/` alias | `@web/` (builder), `@ui/` (studio); insights used relative imports; `@ai/`, `@analytics/`, `@shell/` (studio/src) |

### URLs

| Upstream | Here |
| --- | --- |
| `/builder/...` | `/studio/web/...` (`builder_path` is fixed to `studio/web`) |
| `/insights/...` | `/studio/analytics/...` (`insights_path` is fixed to `studio/analytics`; insights builds every path with `appPath()`) |
| `/flow`, `/flow/s/<id>` | `/studio`, `/studio/chat/<id>`; flow's own page (agents, settings) is `/studio/ai` |
| `/studio/home`, `/studio/app/<app>/<page>` | `/studio/ui`, `/studio/ui/app/<app>/<page>` |

`/builder`, `/insights` and `/flow` redirect server-side (`website_redirects` in `frappe/hooks.py`);
the old studio paths redirect in the client.

## How the layers plug in

These are the pieces that exist only here. A port must not undo them.

### Backend

- **Hooks.** `frappe/hooks.py` declares `layers = ["web", "analytics", "ai", "ui"]`;
  `frappe._load_app_hooks` reads each `frappe/<layer>/hooks.py` with the same merge rules as
  separate apps. The layer hooks lost: `app_*` metadata, `export_python_type_annotations`,
  `require_type_annotated_api_methods`, `website_route_rules`, `add_to_apps_screen` (one
  "Studio" entry in `frappe/hooks.py`), and builder's `user_invitation.allowed_roles` (it would
  let a Website Manager invite any role through the frappe app).
- **Every whitelisted method needs type annotations.** frappe sets
  `require_type_annotated_api_methods`, and the layers are frappe now. An upstream method with an
  untyped argument fails with a 417 here.
- **App name.** There is no `builder`/`insights`/`flow`/`studio` app any more. `get_installed_apps()`
  checks, `get_app_path("<app>", ...)`, `app_name=` filters and export targets use `"frappe"`
  and the layer folder: `get_app_path("frappe", "web", ...)`. Builder exports to app `frappe` by
  default (`template_target_app()`). Builder invitations are frappe-app invitations tagged by
  their `/studio/web` redirect path.
- **The Studio page.** `/studio` and everything under it render `frappe/www/_studio.py`, whose
  boot merges every `frappe/<layer>/shell.py` `get_boot()`.
- **Artifacts.** Each layer names the DocTypes Studio can open beside a chat in its
  `studio_artifacts` hook (`{doctype: {label, route, title_field}}`). Chats link to artifacts
  through the `Flow Session Artifact` child table; `frappe/ai/artifacts.py` has the API
  (`link_artifact`, `get_history`, `get_artifact_session`, `get_session_artifacts`).
- **AI.** Layer tools for the assistant live in `frappe/<layer>/flow_tools.py`, are listed under
  the `flow_tools` hook, return `"artifact"` when they create or change one, and the built-in
  "Flow" assistant carries them all. Builder's and Studio's own AI fall back to Flow Model and
  Flow Provider keys, so one model set up in flow serves every AI.
- **Studio apps.** frappe's own `studio/` folder is the SPA, and is also where studio exports
  apps for the frappe app; frappe's exported studio apps are only those listed in
  `frappe/ui/studio_apps.txt` (`frappe.ui.utils.get_studio_apps`). Per-app builds run
  `yarn build-studio-app` in `studio/`.
- **Login** lands on the default app; new sites default to Studio.

### Frontend (`studio/`)

- One Vite app (frappe-ui 1.0.0, Vue 3.5, Vite 8). A dependency bump in an upstream
  `frontend/package.json` goes to `studio/package.json`.
- **The shell** (`studio/src`) owns `createApp`, pinia, the router (base `/`), `FrappeUIProvider`,
  translations (`__`), the theme, the rail, the home (`/studio`) and the chat routes.
- **A layer** hands the shell a `Layer` from `studio/<layer>/src/layer.ts` (`src2/layer.ts` for
  analytics): `name`, `title`, `icon`, `path`, `component` (its root, rendering `<RouterView>`),
  relative child `routes`, `setup(app)` (runs once on first entry: CSS, global components, socket)
  and `beforeEnter`. A layer's `router` module hands out the shell's router, so upstream code that
  imports it keeps working. A route with `meta.artifact = { doctype, param }` gets the chat on its
  left.
- **Renamed to avoid clashes:** route names (`builder-home`, `builder-editor`, ...;
  `InsightsHome`, `InsightsNotFound`; `StudioHome`, `StudioNotPermitted`, `StudioNotFound`), studio
  pinia ids (`studioStore`, `studioCanvasStore`, `studioComponentStore`) and resource cache keys
  (`studio-apps`, `studio-pages`).
- **CSS.** A layer's stylesheet starts with `@config "<its tailwind.config.js>";` and has
  `@tailwind components; @tailwind utilities;` only: no `@tailwind base`, no
  `frappe-ui/style.css` (the shell has both). Tailwind configs use `content: { relative: true }`.
  `studio/build/layerScope.js` wraps every layer's CSS in
  `@scope ([data-layer=x]) to ([data-layer]:not([data-layer=x]))`; the shell sets `data-layer` on
  `<html>` and on the chat beside an editor. The shell's own stylesheet must keep its `@config`
  line, or its classes go missing from builds.
- **Not carried over:** each app's standalone boot code (`main.ts`), its own `ToastProvider` /
  `FrappeUIProvider`, the frontend telemetry plugin, insights' `window.fetch` 403 override,
  builder's editor demo route, and app switchers in the layers' headers (the rail does that).

## Porting upstream changes

The history rewrite is deterministic: running the same rewrite on a fresh clone of an upstream
repo reproduces the commits already merged here, hash for hash. So a port is a plain `git merge`
of the rewritten upstream branch, and git's rename detection carries the changes onto the
folders' current names (`frappe/insights/...` in the rewritten history lands in
`frappe/analytics/...`).

This was tried with the 6 insights commits after `ef8c4817`: the code auto-merged onto
`frappe/analytics`, the only conflict was a generated file, and the layer's tests passed.

### 1. Rewrite the upstream history

Use `git-filter-repo` (tested with version `a40bce548d2c`; `uvx git-filter-repo` works) on a fresh
**full** clone (not shallow):

```sh
git clone --single-branch --branch develop https://github.com/frappe/insights.git /tmp/port/insights
./rewrite_app_history.sh /tmp/port/insights insights   # see "Scripts" below
```

Check that the rewrite is the same as before: the rewritten copy of the upstream commit in the
"Sources" table must have the hash in its "Rewritten commit" column.

```sh
git -C /tmp/port/insights log --format='%H %s' | grep -m1 '<subject of the merged upstream commit>'
```

If it differs, stop: the merge would bring the whole history in a second time. Check the clone is
full, the branch is right and the script is unchanged.

### 2. Merge

```sh
git fetch /tmp/port/insights develop:refs/heads/port/insights
git merge --no-ff port/insights -m "feat(analytics): merge frappe/insights@develop up to <short sha>"
```

To take a single change instead, cherry-pick its rewritten commit from `port/insights`.

### 3. Resolve

Expect conflicts in:

- **Generated files** the rename rewrote (`frappe/analytics/docs/coverage.md`): drop the old-path
  copy (`git rm frappe/insights/docs/coverage.md`) and regenerate
  (`python frappe/analytics/tests/features.py generate`).
- **Files that no longer exist here**: an app's `frontend/index.html`, `main.ts`, vite config,
  `package.json`, `yarn.lock`, root CI and lint configs. Port the intent by hand: boot code goes to
  the layer's `setup`, routes to its `layer.ts`/routes file, dependencies to `studio/package.json`.
- **`hooks.py`**: keep the layer's hooks shape (see "Hooks" above); add new hooks, don't bring back
  removed keys.
- **Lines the rename touched** (imports, method paths, URLs): keep the unified form.

### 4. Rewrite the new code

Upstream code still says `builder.`, `insights.`, `/assets/builder/`, `@/`... Run the rewrite
script over every file the merge changed, from the repo root:

```sh
git diff --name-only --diff-filter=AM HEAD^1 HEAD -- frappe/web frappe/analytics frappe/ai frappe/ui studio \
  | xargs python port_rewrite.py
```

It rewrites in place and prints the lines that still need a person: `get_app_path("<app>", ...)`,
app-name checks such as `"builder" in frappe.get_installed_apps()`, and absolute `/builder`,
`/insights`, `/flow` or `/studio/app/` URLs (see "URLs").

Then check by hand:

- new **patches**: add them to the layer's `patches.txt` as `frappe.<layer>.patches...`;
- new **whitelisted methods**: every argument type-annotated;
- new **DocTypes**: `"module"` is the layer's (Web, Analytics, AI, UI);
- new **routes**: relative paths in the layer's routes, unique names, `meta.artifact` on an editor
  of an artifact;
- new **CSS** files in a layer: no `@tailwind base`, no `frappe-ui/style.css` import;
- new **templates**: Jinja names prefixed with the layer folder.

### 5. Check

```sh
# every layer module imports (run from the bench's sites/ folder)
../env/bin/python -c "import frappe, importlib, pkgutil
frappe.init(site='', sites_path='.')
for layer in ['web', 'analytics', 'ai', 'ui']:
    pkg = importlib.import_module(f'frappe.{layer}')
    for m in pkgutil.walk_packages(pkg.__path__, f'frappe.{layer}.'):
        if '.test' not in m.name and '__main__' not in m.name:
            importlib.import_module(m.name)"
bench --site <test site> migrate
bench --site <test site> run-tests --module frappe.<layer>.<module>   # the touched layer's tests
cd apps/frappe/studio && yarn build                                    # also builds insights' desk islands
```

Then open `/studio`, the layer's screens and an artifact editor in the browser.

## Scripts

### The history rewrite (`rewrite_app_history.sh`)

The exact rewrite used for the merges. It maps paths to where they were **at merge time**
(`frappe/<app>/`, `frontend/<app>/`); git's rename detection takes them the rest of the way. Don't
"fix" it to the current names: a different rewrite produces different hashes, and step 1's check
fails.

```sh
#!/bin/zsh
# usage: rewrite_app_history.sh <full clone> <app: builder | insights | flow | studio>
set -e
cd "$1"
APP="$2"
uvx git-filter-repo --force --filename-callback "
A = b'$APP'
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
"
```

### The code rewrite (`port_rewrite.py`)

Run from the repo root (it reads the layer folders to tell a module path from a file name such as
`"builder.css"`).

```python
"""Rewrite upstream builder/insights/flow/studio references to the unified layout.

usage: python port_rewrite.py <file> [<file> ...]   (run from the frappe repo root)
Rewrites in place and prints the lines that still name an old app for a manual look.
"""

import re
import sys
from pathlib import Path

LAYERS = {"builder": "web", "insights": "analytics", "flow": "ai", "studio": "ui"}
MODULES = {"Builder": "Web", "Insights": "Analytics", "Flow": "AI", "Studio": "UI"}
ALIASES = {"builder": "@web/", "studio": "@ui/"}  # the upstream frontends whose "@/" meant their src


def modules(layer):
	"""Top-level names inside a layer package, so `builder.css` or `flow.json` stay put."""
	return {path.stem if path.suffix == ".py" else path.name for path in Path("frappe", layer).iterdir()}


NAMES = {old: modules(new) for old, new in LAYERS.items()}
ALT = "|".join(LAYERS)
DOTTED = re.compile(rf"(?<![\w.])(?P<app>{ALT})\.(?:(?P=app)\.)?(?P<head>\w+)(?P<tail>(?:\.\w+)*)")


def dotted(match):
	app, head = match["app"], match["head"]
	if head not in NAMES[app]:
		return match[0]
	return f"frappe.{LAYERS[app]}.{head}{match['tail']}"


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
	text = re.sub(r'(["\'])templates/generators/(webpage|studio_renderer|app_renderer)', lambda m: f"{m[1]}{'web' if m[2] == 'webpage' else 'ui'}/templates/generators/{m[2]}", text)
	for old, new in MODULES.items():
		text = text.replace(f'"module": "{old}"', f'"module": "{new}"')
	layer = next((old for old in ALIASES if f"/{LAYERS[old]}/" in f"/{path}"), None)
	if layer and path.startswith("studio/"):
		text = re.sub(r"(?<=[\"'`])@/", ALIASES[layer], text)
	return text


REVIEW = re.compile(rf"get_app_path\(\s*[\"'](?:{ALT})[\"']|[\"'](?:{ALT})[\"']\s*(?:in|==|!=)|(?<![\w/])/(?:builder|insights|flow)(?:/|[\"'`])|/studio/app/")


def main(paths):
	for name in paths:
		path = Path(name)
		text = path.read_text()
		new = rewrite(text, name)
		if new != text:
			path.write_text(new)
		for number, line in enumerate(new.splitlines(), 1):
			if REVIEW.search(line):
				print(f"{name}:{number}: {line.strip()}")


if __name__ == "__main__":
	main(sys.argv[1:])
```

## Still open

- Upstream sites running the separate apps have no upgrade path to this layout yet (Installed
  Applications, Module Def renames, Patch Log names `insights.patches.*` vs
  `frappe.analytics.patches.*`).
- Layer translations (`frappe/<layer>/locale`) aren't loaded by frappe.
- Frontend telemetry is off since the layers share one page.
- Builder's and Studio's editors still have their own AI tab beside the Studio chat.
- Licenses: insights is GPLv3 and flow AGPLv3 inside MIT frappe; their texts are kept as
  `frappe/analytics/license.txt` and `frappe/ai/license.txt`.
