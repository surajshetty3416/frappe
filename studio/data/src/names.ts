import { reactive } from "vue"

import { getNames } from "./api"

// core DocTypes a site's own data most often points to
const CORE_TARGETS = ["User", "Role", "Contact", "Address", "Country", "Currency", "File"]

// what a Link or Table field can point to, offered when a person picks one
export const doctypeNames = reactive({ links: [] as string[], tables: [] as string[] })

let loaded: Promise<void> | null = null
export function loadDoctypeNames(reload = false) {
	if (loaded && !reload) return loaded
	loaded = Promise.all([
		getNames("DocType", { custom: 1, istable: 0 }),
		getNames("DocType", { custom: 1, istable: 1 }),
	]).then(([links, tables]) => {
		doctypeNames.links = [...links, ...CORE_TARGETS]
		doctypeNames.tables = tables
	})
	return loaded
}
