// The daemon's user_message keeps the whole text a turn sent it: the typed message plus
// the attachment, excerpt and memory blocks Flow appended. The bubble shows the message,
// with the files as chips.
const MEMORY = /\n<memory>\n[\s\S]*?\n<\/memory>$/;
// what the editor beside the chat showed, which FrappeClient.run adds for the agent
const CONTEXT = /\n\n<studio_context>\n(.*)\n<\/studio_context>/;
const EXCERPTS = /\n[^\n]*\n<excerpts>\n[\s\S]*?\n<\/excerpts>/;
const FILE_BLOCK = /\n<file name="([^"]*)">\n[\s\S]*?\n<\/file>/g;
const FILE_NOTE = /\n\[Attached file: ([^\n]+?) \(large; relevant excerpts follow\)\]/g;
// the results of the tasks an orchestrator routed, which the site sends it once they all end
const TASK_RESULTS = /\n\n<task_results>\n[\s\S]*?\n<\/task_results>/;
const XML_ENTITIES = { "&quot;": '"', "&lt;": "<", "&gt;": ">", "&amp;": "&" };

export function cleanUserText(text) {
	const files = [];
	let context = null;
	const value = String(text ?? "")
		.replace(MEMORY, "")
		.replace(CONTEXT, (_, json) => {
			try {
				context = JSON.parse(json);
			} catch {
				// not ours to show
			}
			return "";
		})
		.replace(EXCERPTS, "")
		.replace(FILE_BLOCK, (_, name) => {
			files.push(name.replace(/&quot;|&lt;|&gt;|&amp;/g, (entity) => XML_ENTITIES[entity]));
			return "";
		})
		.replace(FILE_NOTE, (_, name) => {
			files.push(name);
			return "";
		});
	return { text: value, files, context };
}

// `fileId` names the staged File behind a chip, so a steered message the composer is
// still showing as queued matches its durable row; `modelName` maps a provider model id
// to the Flow Model the page speaks in.
export function presentEvent(
	event,
	{ fileId = (name, fallback) => fallback ?? `file:${name}`, modelName = (id) => id } = {}
) {
	if (event.type === "model_changed") return { ...event, model: modelName(event.model) };
	if (event.type === "user_message") {
		const notice = taskNotice(event.content);
		return { ...event, content: presentUserContent(event.content, fileId), ...(notice && { notice }) };
	}
	return event;
}

// a task report shows as a quiet line, never as the person's bubble
function taskNotice(content) {
	const text = typeof content === "string" ? content : Array.isArray(content) ? content.map((block) => block.text ?? "").join("") : "";
	if (!TASK_RESULTS.test(text)) return null;
	return cleanUserText(text.replace(TASK_RESULTS, "")).text.trim() || "Tasks finished";
}

const contextBlocks = (contexts) => contexts.filter(Boolean).map((context) => ({ type: "context", context }));

function presentUserContent(content, fileId) {
	const files = [];
	const chip = (name) => ({ type: "attachment", id: fileId(name), name, kind: "file" });
	const contexts = [];
	if (typeof content === "string") {
		const cleaned = cleanUserText(content);
		if (!cleaned.files.length && !cleaned.context) return cleaned.text;
		return [{ type: "text", text: cleaned.text }, ...cleaned.files.map(chip), ...contextBlocks([cleaned.context])];
	}
	if (!Array.isArray(content)) return content;
	const blocks = content.map((block) => {
		if (block.type === "attachment") return { ...block, id: fileId(block.name, block.id) };
		if (block.type !== "text") return block;
		const cleaned = cleanUserText(block.text);
		files.push(...cleaned.files);
		contexts.push(cleaned.context);
		return { ...block, text: cleaned.text };
	});
	return [...blocks, ...files.map(chip), ...contextBlocks(contexts)];
}
