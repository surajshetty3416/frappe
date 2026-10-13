import CodeView from "./tools/CodeView.vue";
import CreateView from "./tools/CreateView.vue";
import JsonView from "./tools/JsonView.vue";
import NamesView from "./tools/NamesView.vue";
import ReadView from "./tools/ReadView.vue";
import ReportView from "./tools/ReportView.vue";
import { parseResult } from "./tools/result.js";
import SnippetView from "./tools/SnippetView.vue";

// How the assistant's tools read in the transcript and approval cards: a present-tense label, an
// icon, the one-line subject of the call, the count it ended on, and the view that draws
// its records. `view` renders the result in the expanded row, and the arguments on the
// approval card of a tool that asks first. A tool without one shows its raw result.
const TOOLS = {
	find_doctypes: {
		icon: "lucide-search",
		label: "Finding DocTypes",
		stat: (result) => count(result.length, "match", "matches"),
	},
	describe: {
		icon: "lucide-layers",
		label: "Reading DocType Meta",
		stat: (result) => count(result.fields?.length ?? 0, "field"),
	},
	read_records: {
		icon: "lucide-database",
		label: "Reading Records",
		view: ReadView,
		stat: (result) => count(result.length, "record"),
	},
	run_report: {
		icon: "lucide-chart-column",
		label: "Running Report",
		view: ReportView,
		stat: (result) =>
			result.rows.length < result.row_count
				? `${result.rows.length} of ${count(result.row_count, "row")}`
				: count(result.row_count, "row"),
	},
	create: {
		icon: "lucide-file-plus",
		label: "Creating Records",
		view: CreateView,
		asks: true,
		stat: (result) => outcome(result.created, result.failures, "created"),
	},
	update: {
		icon: "lucide-pencil",
		label: "Updating Records",
		view: NamesView,
		asks: true,
		stat: (result) => outcome(result.updated, result.failures, "updated"),
	},
	delete: {
		icon: "lucide-trash-2",
		label: "Deleting Records",
		view: NamesView,
		asks: true,
		stat: (result) => outcome(result.deleted, result.failures, "deleted"),
	},
	run_action: {
		icon: "lucide-play",
		label: (args) => ACTIONS[args.action] ?? "Running Document Actions",
		view: NamesView,
		asks: true,
		stat: (result) =>
			result.action === "rename"
				? "renamed"
				: outcome(result.results, result.failures, "done"),
	},
	execute: { icon: "lucide-code", label: "Running Code", view: CodeView, asks: true },
	search_knowledge: {
		icon: "lucide-book-open",
		label: "Searching Knowledge",
		view: SnippetView,
		stat: (result) => count(result.length, "hit"),
	},
	search_attachments: {
		icon: "lucide-paperclip",
		label: "Searching Attachments",
		view: SnippetView,
		stat: (result) => count(result.length, "hit"),
	},
	update_memory: {
		icon: "lucide-bookmark",
		label: "Saving Memory",
		stat: (result) => result.action ?? "",
	},
	load_skill: { icon: "lucide-book", label: "Loading Skill" },
	subagent: { icon: "lucide-bot", label: "Sub-agent" },
	list_chats: { icon: "lucide-messages-square", label: "Reading Chats", stat: (result) => count(result.length, "chat") },
	start_chat: { icon: "lucide-message-square-plus", label: "Starting Chat", subject: (args) => subject({ name: args.title }) },
	send_to_chat: { icon: "lucide-send", label: "Sending to Chat", subject: (args) => subject({ content: args.message }) },
};

const ACTIONS = {
	submit: "Submitting",
	cancel: "Cancelling",
	amend: "Amending",
	rename: "Renaming",
};

const SUBJECT_KEYS = [
	"doctype",
	"report_name",
	"query",
	"search",
	"name",
	"action",
	"description",
	"content",
];

export function presentTool(name, args = {}, result = null) {
	const tool = TOOLS[name];
	// a custom Imported or Script tool: its return is the point, so always show it
	if (!tool) return { resultComponent: JsonView };
	const parsed = tool.stat ? parseResult(result) : null;
	// a cut result is no longer JSON, so show its text; execute's view already does
	const cut = result?.details?.truncation?.truncated && tool.view !== CodeView;
	return {
		icon: tool.icon,
		label: typeof tool.label === "function" ? tool.label(args) : tool.label,
		subject: tool.subject ? tool.subject(args) : subject(args),
		stat: parsed ? tool.stat(parsed) : "",
		argsComponent: tool.asks ? tool.view : undefined,
		resultComponent: cut ? JsonView : tool.view,
	};
}

function subject(args) {
	for (const key of SUBJECT_KEYS) {
		const value = args?.[key];
		if (typeof value === "string" && value.trim()) {
			const line = value.split("\n")[0];
			return line.length > 80 ? line.slice(0, 77) + "…" : line;
		}
	}
	return "";
}

function count(n, singular, plural = `${singular}s`) {
	return `${n} ${n === 1 ? singular : plural}`;
}

function outcome(done, failures, verb) {
	const ok = `${done?.length ?? 0} ${verb}`;
	return failures?.length ? `${ok} · ${failures.length} failed` : ok;
}
