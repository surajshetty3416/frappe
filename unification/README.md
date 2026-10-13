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

This folder keeps the branch in step with those repos until it lands in frappe develop: this
file maps where everything moved and what the unification added, and [`sync.py`](sync.py) merges
upstream changes (see "Keeping up with upstream"). Delete the folder once the merge is upstream.

## Sources

| Upstream | Branch | Layer |
| --- | --- | --- |
| frappe/frappe | develop | the base |
| frappe/builder | develop | web |
| frappe/insights | develop | analytics |
| frappe/flow | main (it has no develop) | ai |
| frappe/studio | develop | ui |

[`sources.json`](sources.json) holds the last upstream commit merged from each and, for the apps,
its rewritten copy here (the merge's second parent); every sync updates it in its merge commit.
The first merges took builder at `477481ff`, insights at `ef8c4817`, flow at `b3466bf0` and
studio at `42491ecd`, on frappe develop at `c8d85d63`.

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

## Keeping up with upstream

```sh
python3 unification/sync.py status           # what each source has that isn't merged yet
python3 unification/sync.py merge            # merge it all, one merge commit per source
python3 unification/sync.py merge insights   # or one source
```

Run it from the repo root on the branch to update, with a clean tree. It needs `uvx` (or
`git-filter-repo` 2.47 on the PATH) and keeps its clones in `~/.cache/frappe-unification`
(`UNIFICATION_CACHE`).

### How a sync works

frappe develop merges as it is. An app's history was rewritten before its first merge so its
files sat under `frappe/<app>/` and `frontend/<app>/` (`CALLBACK` in `sync.py`); later commits here
moved them to the layer folders. A sync rewrites only the commits since the last merge, the same
way, and parents them on their copies already merged here, matched by author, both times and
subject (a commit the first rewrite dropped, such as a `frappe-ui` submodule bump, hands over to
its parent). What's left is a plain merge, and git's rename detection carries the changes onto the
layer folders.

It doesn't re-run the whole rewrite: `git-filter-repo` rewrites hashes quoted in messages
("cherry picked from commit ...") only for commits it has already exported, and the export order
shifts as upstream adds and deletes branches, so a full rewrite stops reproducing the merged
history.

### What it resolves itself

- **Files the unification only renamed things in** (`@/` to `@web/`, `builder.` to `frappe.web.`):
  it merges them again with upstream's sides renamed first, so only real edits conflict. A file
  upstream deleted goes.
- **A change git lost track of across the rename**: merged into the file's new home (`moves` in
  `sources.json`).
- **Repo tooling the unification removed** (CI, lint, lockfiles, generated `.d.ts`; `ignore` in
  `sources.json`): stays removed.
- **New upstream files under the old folders**: moved to the layer's.
- **Old names in whatever the merge brought in**: rewritten by [`port_rewrite.py`](port_rewrite.py).
  The new lines it can't decide on (`get_app_path("builder", ...)`, app-name checks, `/builder`
  URLs) are printed as "look at".
- **Generated files**: regenerated (`regenerate` in `sources.json`).

### What needs a person

`merge` stops at a source that still conflicts and lists the files (`--skip-conflicts` sets the
source aside instead). The usual causes:

- **Both sides edited the same lines.** Combine them, keeping the unification's integration (see
  "How the layers plug in"). For example, the shell owns the theme, so upstream code that sets
  `data-theme` should read and toggle frappe-ui's `useColorScheme()` instead.
- **Upstream changed a file that doesn't exist here.** Port the intent and `git rm` the old path:
  `package.json` to `studio/package.json` (then `yarn install` in `studio/`), `pyproject.toml`
  to the root one, `index.html`/`main.ts`/vite config to the layer's `layer.ts`, its `setup` or
  `studio/vite.config.js`.
- **Upstream added something the layout has no place for**, such as a new folder beside an app's
  `frontend/src`: decide where it goes.

Then `git add` the files, run the source's `regenerate` commands, `git commit` (the message is
ready) and run `merge` again for the other sources.

Check by hand, since the tool can't see these:

- new **patches**: in the layer's `patches.txt` as `frappe.<layer>.patches...`;
- new **whitelisted methods**: every argument type-annotated;
- new **DocTypes**: `"module"` is the layer's (Web, Analytics, AI, UI);
- new **routes**: relative paths in the layer's routes, unique names, `meta.artifact` on an
  artifact's editor;
- new **CSS** in a layer: no `@tailwind base`, no `frappe-ui/style.css` import;
- new **templates**: Jinja names prefixed with the layer folder.

### Checks

```sh
# from the bench's sites/ folder
../env/bin/python ../apps/frappe/unification/check_imports.py
bench --site <test site> migrate
bench --site <test site> run-tests --module frappe.<layer>.<module>
yarn --cwd ../apps/frappe/studio install && yarn --cwd ../apps/frappe/studio build   # also builds insights' desk islands
```

Then open `/studio`, the touched layer's screens and an artifact editor in the browser.

### The daily PR

On the devbox, `systemd/unification-sync.timer` runs [`sync_pr.sh`](sync_pr.sh) at 01:47 UTC
(07:17 IST). It works in a bench of its own, `/home/t3run/unification-sync`, whose `apps/frappe`
is a worktree of the unified bench's repo, so the bench serving unified.surajshetty.tech is never
touched. Each run:

1. skips the day if a `sync/upstream` PR is still open;
2. resets the worktree to `origin/unified` and runs `sync.py merge --skip-conflicts` on a
   `sync/upstream` branch;
3. checks the result: reinstalls the sync bench's env from the merged `pyproject.toml` (with
   frappe's dev dependencies), imports every layer module, builds the SPA, then migrates
   `unified-test.localhost` and runs every layer test on it;
4. pushes and opens a PR into `unified`, as a draft if a check failed;
5. lists the sources it set aside in an "Upstream sync needs a hand" issue on the fork, updated
   each run and closed once everything merges. Merge those by hand with `sync.py merge <source>`
   and push to `unified`; the next run carries on from there.

`systemctl start unification-sync` runs it now, `journalctl -u unification-sync` shows the run,
and `DRY_RUN=1` prints the PR and issue instead of pushing.

One-time setup, as root on the devbox. The sync bench shares the unified bench's MariaDB, Redis and
built desk assets:

```sh
B=/home/t3run/unification-sync U=/home/t3run/unified-bench
sudo -u t3run git -C $U/apps/frappe worktree add --detach $B/apps/frappe origin/unified
sudo -u t3run -i uv venv --python 3.14 $B/env
sudo -u t3run mkdir -p $B/sites && echo frappe | sudo -u t3run tee $B/sites/apps.txt
sudo -u t3run python3 -c "import json; c = json.load(open('$U/sites/common_site_config.json')); c.pop('default_site', None); json.dump(c, open('$B/sites/common_site_config.json', 'w'), indent=1)"
sudo -u t3run ln -s $U/sites/assets $B/sites/assets
sudo -u t3run -i gh auth setup-git
cd $B/apps/frappe && sudo -u t3run -i uv pip install --python $B/env/bin/python -e $B/apps/frappe
cd $B/sites && sudo -u t3run ../env/bin/python -m frappe.utils.bench_helper frappe new-site unified-test.localhost \
  --db-root-username root --db-root-password <root> --admin-password admin
sudo -u t3run ../env/bin/python -m frappe.utils.bench_helper frappe --site unified-test.localhost set-config allow_tests true
cp $B/apps/frappe/unification/systemd/unification-sync.* /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now unification-sync.timer
```

A frappe checkout must sit at `<bench>/apps/frappe`: frappe finds its bench as `../..` from the
repo, and the SPA build scans `apps/` for studio apps. Outside that layout `new-site` half installs
and frappe's migrate then reaps every DocType as an orphan.

## Still open

- Upstream sites running the separate apps have no upgrade path to this layout yet (Installed
  Applications, Module Def renames, Patch Log names `insights.patches.*` vs
  `frappe.analytics.patches.*`).
- Layer translations (`frappe/<layer>/locale`) aren't loaded by frappe.
- Frontend telemetry is off since the layers share one page.
- Builder's and Studio's editors still have their own AI tab beside the Studio chat.
- frappe-ui's `reka-ui` patch (shadow-DOM layers for insights' desk islands) isn't applied:
  it targets reka-ui 2.10 and the SPA resolves 2.11. `studio/patches` applies the SPA's own.
- frappe-ui stays at 1.0.0; studio upstream moved to 1.0.1.
- Studio's canvas theme toggle sets `data-theme` inside the layer, which `layerScope.js` only
  matches on or above the layer's root: check it in the browser.
- Licenses: insights is GPLv3 and flow AGPLv3 inside MIT frappe; their texts are kept as
  `frappe/analytics/license.txt` and `frappe/ai/license.txt`.
