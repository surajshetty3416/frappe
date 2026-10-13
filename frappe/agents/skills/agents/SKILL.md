---
name: Agents
description: Make or change a Flow Agent, and an Automation Flow that runs it with the RunAgent action when a record is created or changed, or on a schedule. Load it before you create or update either DocType. Use for any request for an agent, an assistant, a bot, a screener, a digest, or work that should happen by itself.
---

# Agents and automations

An agent is a `Flow Agent`: instructions, a model and tools. An automation is an `Automation Flow`: a trigger, optional filters, and steps. A `RunAgent` step starts the agent with a prompt. Make both with the `create` tool. Change them with `update`. Studio opens each one beside the chat.

## Steps

1. Run `describe` on every DocType the agent reads or writes. Use the real fieldnames and the exact Select options in its instructions.
2. Find the model with `read_records` on `Flow Model` (`enabled` = 1). Use its `name`.
3. Create the agent. Then create the automation that runs it, if the request says when it should run.

## Flow Agent

```json
{
  "title": "Proposal Screener",
  "description": "Scores and tags each new Talk Proposal.",
  "enabled": 1,
  "model": "<Flow Model name>",
  "instructions": "...",
  "tools": [{"tool": "read_records"}, {"tool": "update"}]
}
```

- `title` is the agent's name and must be unique. `model` and `instructions` are required.
- `instructions` speak to the agent: what it reads, what it writes in which fields, the allowed values, and what it never does. An automation's agent has no person to ask, so tell it to finish the job without questions.
- `tools` holds only what the job needs:

| Tool | Use |
|---|---|
| `read_records` | Read records of any DocType, with filters and fields |
| `describe` | Read a DocType's fields |
| `find_doctypes` | Find DocTypes by name |
| `update` | Change fields on existing records |
| `create` | Insert records |
| `run_report` | Run a report |
| `send_email_template` | Send an email from an Email Template |

  An agent that only answers questions gets `read_records` and `describe`, never `update` or `create`.
- `reasoning_effort` is optional: `low`, `medium` or `high`.
- `skills` is optional: `[{"skill": "<Flow Skill name>"}]`.

## Automation Flow

```json
{
  "title": "Screen new proposals",
  "enabled": 1,
  "document_type": "Talk Proposal",
  "trigger_type": "Doc Created",
  "actions": [
    {
      "step_type": "Action",
      "action_type": "RunAgent",
      "params": {"agent": "Proposal Screener", "prompt": "Screen Talk Proposal {{ doc.name }}."}
    }
  ]
}
```

- `enabled` defaults to 0. Set it to 1, or the automation never runs.
- `trigger_type` is one of `Doc Created`, `Doc Updated`, `Field Value Changed`, `Doc Submitted`, `Doc Cancelled`, `Doc Deleted`, `Date Based` and `Scheduled`. Every one but `Scheduled` needs `document_type`.
- `Field Value Changed` needs `trigger_field`, and optionally `from_value` and `to_value`.
- `Scheduled` needs `cron_expression` in the site's time zone, such as `0 8 * * *` for every day at 08:00. Leave `document_type` empty.
- `filters` narrows which records run it: a JSON string of rows `[["status", "=", "Open"]]`.
- `params.agent` is the Flow Agent's `name` (its title). `params.prompt` is a Jinja template: `{{ doc.name }}` and `{{ doc.<fieldname> }}` read the record that fired the trigger. Name the record and let the agent read the rest with its tools.
- The automation runs the agent as Administrator and its tools run without approval. The agent's reply and its session show under the automation's Runs.

## Check

After you make an automation on a document event, create one test record only if the person asks for a test. The run starts in the background and the agent writes a few seconds later. Read the record back with `read_records` to see what the agent wrote.
