# Studio setup

This branch, `unified-poc`, serves Studio at `/studio` on any frappe-bench. It needs Python 3.14, Node 24 or later, MariaDB and Redis.

## Bench

```bash
bench init --frappe-path https://github.com/surajshetty3416/frappe --frappe-branch unified-poc --python python3.14 studio-bench
cd studio-bench
bench pip install -e apps/frappe/harness
```

The last command replaces the `frappe-flow` release from PyPI with the flow server in `harness/`, which this branch changes. Run it before making a site, because installing a site starts the flow server. On a bench that already has sites, run `bench flow-server restart` after it.

## Site

Start the bench in its own terminal and leave it running:

```bash
bench start
```

Then make the site and check the flow server:

```bash
bench new-site studio.localhost --admin-password admin
bench flow-server status
```

If the flow server is not running, start it with `bench flow-server start`. Open `http://studio.localhost:8000/studio` and log in as Administrator.

## Model

A new site runs chats on Claude Code Opus. Log in to Claude Code (`claude`) as the OS user that runs the bench, or set a token from `claude setup-token` as the API key of the `claude-code` Flow Provider.

## Frappeverse demo

```bash
bench --site studio.localhost studio-demo
```

This replays seven recorded chats that build a conference, one per layer: Data, Apps, Websites, Dashboards, Print, Email and Agents. Each chat then opens with its transcript and the artifacts it made. It takes about six minutes and needs `bench start` running.

Run it on a new site. It sets India, INR and Asia/Kolkata, names Administrator Aditi Rao, and sends mail to an SMTP receiver on `127.0.0.1:1025`. Replays call no model, but the Agents chat starts five screener runs on Claude Code. Run again, it plays only the chats it has not replayed: a second replay of a chat makes the same artifacts again and fails.

## Pilot bench

On a pilot bench with this branch and the harness installed as above:

```bash
pilot -b <bench> new-site studio-test.localhost --admin-password admin
```

`pilot new-site` restarts the bench's workers, which cuts any chat running on its other sites.
