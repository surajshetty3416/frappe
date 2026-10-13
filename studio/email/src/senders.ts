// what sends a template, once per trigger: several automations can share one
export function sentWhen(senders: string[] = []) {
	const triggers = [...new Set(senders)]
	if (!triggers.length) return "Not sent automatically"
	return triggers.length > 1 ? `${triggers[0]} +${triggers.length - 1} more` : triggers[0]
}
