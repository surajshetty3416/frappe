<template>
	<div class="relative h-full bg-surface-gray-1">
		<div v-if="loading" class="flex h-full items-center justify-center">
			<LoadingIndicator class="size-5 text-ink-gray-4" />
		</div>

		<div v-else-if="!nodes.length" class="flex h-full items-center justify-center overflow-y-auto px-6">
			<div class="flex w-full max-w-xl flex-col items-center text-center">
				<span class="grid size-10 place-items-center rounded-full bg-surface-gray-2">
					<span class="lucide-database size-5 text-ink-gray-6" />
				</span>
				<h1 class="mt-4 text-2xl font-semibold text-ink-gray-9">Describe your data</h1>
				<p class="mt-2 max-w-md text-p-base text-ink-gray-6">
					Tell the assistant in the chat what you keep track of: the things, what each one holds, and how they link. Its DocTypes show here as a diagram.
				</p>
			</div>
		</div>

		<div v-else ref="panel" class="size-full">
			<VueFlow
				:nodes="nodes"
				:edges="edges"
				:nodes-connectable="false"
				:elements-selectable="false"
				:min-zoom="0.2"
				:max-zoom="1.25"
				:default-viewport="{ x: 0, y: 0, zoom: 1 }"
				:zoom-on-scroll="false"
				pan-on-scroll
				:pan-on-scroll-mode="PanOnScrollMode.Vertical"
				class="size-full"
				@node-click="({ node }) => openDocType(node.id)"
			>
				<template #node-doctype="{ data }">
					<DocTypeNode :data="data" />
				</template>
			</VueFlow>
			<div class="pointer-events-none absolute inset-x-0 top-0 flex flex-col gap-1 bg-surface-gray-1 px-6 py-5">
				<h1 class="text-xl font-semibold text-ink-gray-9">Data</h1>
				<span class="text-sm text-ink-gray-5">{{ summary }}</span>
			</div>
			<div class="absolute bottom-4 right-4 flex items-center gap-0.5 rounded-4 border border-outline-gray-2 bg-surface-base p-0.5">
				<Button variant="ghost" icon="lucide-minus" tooltip="Zoom out" @click="zoomOut()" />
				<span class="w-10 text-center text-sm tabular-nums text-ink-gray-6">{{ Math.round(viewport.zoom * 100) }}%</span>
				<Button variant="ghost" icon="lucide-plus" tooltip="Zoom in" @click="zoomIn()" />
				<span class="mx-0.5 h-4 w-px bg-outline-gray-2" />
				<Button variant="ghost" label="Fit" icon-left="lucide-scan" @click="fit()" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onListUpdate } from "@shell/realtime"
import { useDebounceFn, useElementSize } from "@vueuse/core"
import { type Edge, MarkerType, type Node, PanOnScrollMode, VueFlow, useVueFlow } from "@vue-flow/core"
import { Button, LoadingIndicator } from "frappe-ui"
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { type SchemaNode, getSchema } from "../api"
import DocTypeNode from "../components/DocTypeNode.vue"
import { TABLE_TYPES } from "../fields"

const route = useRoute()
const router = useRouter()
const { fitView, setViewport, viewport, zoomIn, zoomOut } = useVueFlow()

const schema = ref<SchemaNode[]>([])
const loading = ref(true)
async function load() {
	schema.value = await getSchema()
	loading.value = false
}
load()
const fit = () => fitView({ padding: 0.1, maxZoom: 1 })
// a DocType the assistant makes shows up as it lands
const reload = useDebounceFn(load, 500)
const stop = onListUpdate("DocType", reload)
onBeforeUnmount(stop)

// a child table belongs to the first DocType that holds it, drawn inside it
const parentOf = computed(() => {
	const parents = new Map<string, string>()
	for (const doctype of schema.value) {
		for (const field of doctype.fields) {
			if (TABLE_TYPES.has(field.fieldtype) && field.options && !parents.has(field.options)) parents.set(field.options, doctype.name)
		}
	}
	return parents
})
const owner = (name: string) => parentOf.value.get(name) ?? name
const placed = computed(() => schema.value.filter((doctype) => !(doctype.istable && parentOf.value.has(doctype.name))))
const childrenOf = (name: string) => schema.value.filter((doctype) => doctype.istable && parentOf.value.get(doctype.name) === name)

// each link from a field, its own or one of its child tables', to the DocType it names
const links = computed(() =>
	placed.value.flatMap((doctype) =>
		[doctype, ...childrenOf(doctype.name)].flatMap((holder) =>
			holder.fields
				.filter((field) => field.fieldtype === "Link" && field.options && owner(field.options) !== doctype.name)
				.map((field) => ({
					source: doctype.name,
					handle: holder === doctype ? field.fieldname : `${holder.name}.${field.fieldname}`,
					target: owner(field.options!),
				}))
		)
	)
)

// how far a DocType sits from the end of its links: what links comes before what it links to
const depthOf = computed(() => {
	const columns = new Map<string, number>()
	const visiting = new Set<string>()
	const column = (name: string): number => {
		if (columns.has(name)) return columns.get(name)!
		if (visiting.has(name)) return 0
		visiting.add(name)
		const targets = links.value.filter((link) => link.source === name).map((link) => link.target)
		const value = targets.length ? Math.max(...targets.map(column)) + 1 : 0
		visiting.delete(name)
		columns.set(name, value)
		return value
	}
	placed.value.forEach((doctype) => column(doctype.name))
	return columns
})

const heightOf = (doctype: SchemaNode) => {
	if (doctype.core) return 40
	const rows = (node: SchemaNode) => node.fields.filter((field) => !TABLE_TYPES.has(field.fieldtype)).length
	const children = childrenOf(doctype.name).reduce((sum, child) => sum + 40 + rows(child) * 24, 0)
	return 50 + rows(doctype) * 28 + children
}

// at 100% the cards fill the panel's width in columns, each card under the shortest one, and the rest scrolls down
const panel = ref<HTMLElement | null>(null)
const { width } = useElementSize(panel)
const CARD = 260
const MARGIN = 24
const TOP = 120
const GAP = 40
const nodes = computed<Node[]>(() => {
	const room = Math.max(CARD, width.value - 2 * MARGIN)
	const count = Math.max(1, Math.floor((room + GAP) / (CARD + GAP)))
	const step = count > 1 ? CARD + Math.min(160, (room - count * CARD) / (count - 1)) : 0
	const bottoms = Array<number>(count).fill(TOP)
	const ordered = [...placed.value].sort((a, b) => (depthOf.value.get(b.name) ?? 0) - (depthOf.value.get(a.name) ?? 0))
	return ordered.map((doctype) => {
		const column = bottoms.indexOf(Math.min(...bottoms))
		const y = bottoms[column]
		bottoms[column] = y + heightOf(doctype) + GAP
		return {
			id: doctype.name,
			type: "doctype",
			position: { x: MARGIN + column * step, y },
			data: { doctype, children: childrenOf(doctype.name) },
		}
	})
})
// a resize lays the cards out again, so the view returns to their left edge at 100%
watch(width, () => setViewport({ x: 0, y: viewport.value.y, zoom: 1 }))

const edges = computed<Edge[]>(() =>
	links.value.map((link) => ({
		id: `${link.source}.${link.handle}`,
		source: link.source,
		sourceHandle: link.handle,
		target: link.target,
		targetHandle: "in",
		style: { stroke: "var(--outline-gray-4)", strokeWidth: 1.25 },
		markerEnd: { type: MarkerType.ArrowClosed, color: "var(--outline-gray-4)", width: 16, height: 16 },
	}))
)

const summary = computed(() => {
	const own = schema.value.filter((doctype) => !doctype.core)
	const records = own.reduce((sum, doctype) => sum + (doctype.count ?? 0), 0)
	return `${own.length} DocType${own.length === 1 ? "" : "s"} · ${records.toLocaleString()} record${records === 1 ? "" : "s"}`
})

// the DocType opens in the same chat
const openDocType = (name: string) => router.push({ name: "data-doctype", params: { doctype: name }, query: { chat: route.query.chat } })

onMounted(() => (document.title = "Data"))
</script>
