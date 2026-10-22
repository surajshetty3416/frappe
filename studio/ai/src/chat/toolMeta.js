import CodeView from "./tools/CodeView.vue";
import CreateView from "./tools/CreateView.vue";
import JsonView from "./tools/JsonView.vue";
import NamesView from "./tools/NamesView.vue";
import QueryView from "./tools/QueryView.vue";
import ReadView from "./tools/ReadView.vue";
import ReportView from "./tools/ReportView.vue";
import { parseResult } from "./tools/result.js";
import SnippetView from "./tools/SnippetView.vue";
import { recordTitle } from "@shell/artifacts";

// How the assistant's tools read in the transcript and approval cards: a present-tense label, an
// icon, the one-line subject of the call, the count it ended on, and the view that draws
// its records. `view` renders the result in the expanded row, and the arguments on the
// approval card of a tool that asks first. A tool without one shows its raw result.
const TOOLS = {
	find_doctypes: {
		icon: "lucide-search",
		label: "Finding DocTypes",
		// a call that only filters by module names the module
		subject: (args) => subject(args) || args.module || "",
		stat: (result) => countOf(result.doctypes.length, result.total, "match", "matches"),
	},
	describe: {
		icon: "lucide-layers",
		label: "Reading DocType Meta",
		subject: (args) => noun(args.doctype) ?? subject(args),
		stat: (result) => count(result.fields?.length ?? 0, "field"),
	},
	read_records: {
		icon: "lucide-database",
		label: (args) => recordsLabel("Reading", args.doctype) ?? "Reading Records",
		subject: (args) => (noun(args.doctype) ? "" : subject(args)),
		view: ReadView,
		stat: (result) => countOf(result.records.length, result.total, "record"),
	},
	run_report: {
		icon: "lucide-chart-column",
		label: "Running Report",
		view: ReportView,
		stat: (result) => countOf(result.rows.length, result.row_count, "row"),
	},
	create: {
		icon: "lucide-file-plus",
		label: (args) => recordsLabel("Creating", args.doctype, args.records?.length) ?? "Creating Records",
		subject: (args) => (noun(args.doctype) ? createdTitles(args) : subject(args)),
		view: CreateView,
		asks: true,
		stat: (result) => outcome(result.created, "created"),
	},
	update: {
		icon: "lucide-pencil",
		label: (args) => recordsLabel("Updating", args.doctype, args.names?.length) ?? "Updating Records",
		subject: (args) => (noun(args.doctype) ? titles(args.doctype, args.names) : subject(args)),
		view: NamesView,
		asks: true,
		stat: (result) => outcome(result.updated, "updated"),
	},
	delete: {
		icon: "lucide-trash-2",
		label: (args) => recordsLabel("Deleting", args.doctype, args.names?.length) ?? "Deleting Records",
		subject: (args) => (noun(args.doctype) ? titles(args.doctype, args.names) : subject(args)),
		view: NamesView,
		asks: true,
		stat: (result) => outcome(result.deleted, "deleted"),
	},
	run_action: {
		icon: "lucide-play",
		label: (args) => ACTIONS[args.action] ?? "Running Document Actions",
		view: NamesView,
		asks: true,
		stat: (result) =>
			result.action === "rename" ? "renamed" : outcome(result.results, "done"),
	},
	execute: { icon: "lucide-code", label: "Running Code", view: CodeView, asks: true },
	run_query: {
		icon: "lucide-database",
		label: "Querying",
		subject: (args) => tables(args.sql),
		view: QueryView,
		stat: (result) => count(result.rows?.length ?? 0, "row"),
	},
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
	run_automation: {
		icon: "lucide-zap",
		label: "Running Automation",
		subject: (args) => titles("Automation Flow", [args.automation]),
		view: JsonView,
	},
	// the layers' tools keep their own names and name the record they take by its title
	publish_web_page: { subject: (args) => titles("Builder Page", [args.page]), view: JsonView },
	add_form_block: { subject: (args) => titles("Builder Page", [args.page]), view: JsonView },
	add_chat_block: { subject: (args) => titles("Builder Page", [args.page]), view: JsonView },
	set_page_data_script: { subject: (args) => titles("Builder Page", [args.page]), view: JsonView },
	get_studio_page: { subject: (args) => titles("Studio Page", [args.page], "page_title"), view: JsonView },
	save_studio_page: { subject: (args) => args.title ?? "", view: JsonView },
	read_dashboard: { subject: (args) => titles("Insights Dashboard v3", [args.dashboard]), view: JsonView },
	add_chart: { subject: (args) => titles("Insights Dashboard v3", [args.dashboard]), view: JsonView },
	update_dashboard: { subject: (args) => titles("Insights Dashboard v3", [args.dashboard]), view: JsonView },
	update_chart: { subject: (args) => titles("Insights Chart v3", [args.chart]), view: JsonView },
	ask_agent: { subject: (args) => titles("Flow Agent", [args.agent]), view: JsonView },
	preview_output: { subject: (args) => args.name ?? "", view: JsonView },
	list_chats: { icon: "lucide-messages-square", label: "Reading Chats", stat: (result) => count(result.length, "chat") },
	start_chat: { icon: "lucide-message-square-plus", label: "Starting Chat", subject: (args) => subject({ name: args.title }) },
	send_to_chat: { icon: "lucide-send", label: "Sending to Chat", subject: (args) => subject({ content: args.message }) },
	get_setup_state: { icon: "lucide-compass", label: "Reading Your Setup" },
	configure_site: {
		icon: "lucide-building-2",
		label: "Setting Up the Organization",
		subject: (args) => [args.organization, args.country, args.currency, args.time_zone].filter(Boolean).join(" · "),
		view: JsonView,
		asks: true,
	},
	invite_people: {
		icon: "lucide-user-plus",
		label: "Inviting People",
		subject: (args) => (args.people ?? []).map((person) => person.first_name || person.email).join(", "),
		view: JsonView,
		asks: true,
		stat: (result) => count(result.length ?? 0, "person", "people"),
	},
	read_workspace: { icon: "lucide-layout-dashboard", label: "Reading Workspace" },
	arrange_workspace: {
		icon: "lucide-layout-dashboard",
		label: "Arranging Workspace",
		subject: (args) => (args.widgets ?? []).map((widget) => widget.title || widget.type).join(", "),
		stat: (result) => count(result.length ?? 0, "widget"),
	},
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

// the flow server's file tools keep the core's own rows, which fold a read's file text
const FILE_TOOLS = new Set(["read", "grep"]);

export function presentTool(name, args = {}, result = null) {
	if (FILE_TOOLS.has(name)) return {};
	const tool = TOOLS[name];
	// a custom Imported or Script tool: its return is the point, so always show it
	if (!tool) return { resultComponent: JsonView };
	const parsed = tool.stat ? parseResult(result) : null;
	const stat = parsed ? readStat(tool, parsed) : "";
	// a cut result is no longer JSON, and an older one may not fit the view, so show
	// their text; execute's view already does
	const plain =
		(result?.details?.truncation?.truncated || stat === null) && tool.view !== CodeView;
	return {
		icon: tool.icon,
		label: typeof tool.label === "function" ? tool.label(args) : tool.label,
		subject: tool.subject ? tool.subject(args) : subject(args),
		stat: stat ?? "",
		argsComponent: tool.asks ? tool.view : undefined,
		resultComponent: plain ? JsonView : tool.view,
	};
}

// what a DocType is called where people see it: an artifact's label, or the word for an internal one
const NOUNS = {
	"Flow Model": "Model",
	"Flow Run": "Agent run",
	"Flow Tool": "Tool",
	"Flow Agent Tool": "Agent tool",
	"Automation Run": "Automation run",
};
const noun = (doctype) => window.studio_artifacts?.[doctype]?.label ?? NOUNS[doctype];

function recordsLabel(verb, doctype, n) {
	const word = noun(doctype);
	if (!word) return null;
	return `${verb} ${n === 1 ? word : `${word}s`}`;
}

function titles(doctype, names, titleField) {
	const shown = (names ?? []).filter(Boolean).map((name) => recordTitle(doctype, name, titleField));
	return subject({ name: shown.join(", ") });
}

// a new record's title, from the field its artifact titles it by
function createdTitles(args) {
	const field = window.studio_artifacts?.[args.doctype]?.title_field ?? "title";
	return subject({ name: (args.records ?? []).map((record) => record[field]).filter(Boolean).join(", ") });
}

// null for a result saved before its tool's return changed
function readStat(tool, parsed) {
	try {
		return tool.stat(parsed);
	} catch {
		return null;
	}
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

// the tables a query reads, by their DocType names
function tables(sql) {
	const names = [...String(sql ?? "").matchAll(/\b(?:from|join)\s+(?:`tab([^`]+)`|tab(\w+))/gi)].map(
		(match) => match[1] ?? match[2]
	);
	const unique = [...new Set(names)];
	return unique.length > 3 ? `${unique.slice(0, 3).join(", ")} and ${unique.length - 3} more` : unique.join(", ");
}

function count(n, singular, plural = `${singular}s`) {
	return `${n} ${n === 1 ? singular : plural}`;
}

function countOf(shown, total, singular, plural) {
	const all = count(total, singular, plural);
	return shown < total ? `${shown} of ${all}` : all;
}

function outcome(done, verb) {
	return `${done?.length ?? 0} ${verb}`;
}
