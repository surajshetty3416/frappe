<template>
	<div data-layer="shell" class="flex h-full min-h-0">
		<div class="flex min-w-0 flex-1 flex-col overflow-y-auto">
			<div class="mx-auto flex w-full max-w-[640px] flex-col gap-6 px-6 py-10">
				<header class="flex flex-col gap-3">
					<ol class="flex items-center gap-2 text-sm">
						<li v-for="(title, i) in STEPS" :key="title" class="flex items-center gap-2">
							<span
								class="grid size-5 place-items-center rounded-full text-xs tabular-nums"
								:class="i < step ? 'bg-surface-gray-7 text-ink-white' : i === step ? 'bg-surface-gray-3 text-ink-gray-9' : 'bg-surface-gray-2 text-ink-gray-5'"
							>
								<span v-if="i < step" class="lucide-check size-3" /><template v-else>{{ i + 1 }}</template>
							</span>
							<span :class="i === step ? 'font-medium text-ink-gray-8' : 'text-ink-gray-5'">{{ title }}</span>
							<span v-if="i < STEPS.length - 1" class="mx-1 h-px w-6 bg-surface-gray-3" />
						</li>
					</ol>
					<h1 class="text-xl font-semibold text-ink-gray-9">{{ HEADINGS[step] }}</h1>
					<p class="text-sm text-ink-gray-5">{{ HINTS[step] }}</p>
				</header>

				<div v-if="!setup" class="flex h-24 items-center justify-center"><LoadingIndicator class="size-4 text-ink-gray-5" /></div>

				<!-- 1: the organization, guessed from the browser and the admin's email -->
				<form v-else-if="step === 0" class="flex flex-col gap-4" @submit.prevent="saveOrganization">
					<FormControl v-model="org.name" label="Organization name" placeholder="Acme" required />
					<FormControl v-model="org.about" type="textarea" label="What it does" placeholder="We build open-source business software for growing companies." :rows="2" />
					<div class="grid grid-cols-2 gap-3">
						<label class="flex flex-col gap-1.5"><span class="text-xs text-ink-gray-5">Country</span><RecordField :field="LINK('Country')" :model-value="org.country" @update:model-value="(v) => (org.country = v as string)" /></label>
						<label class="flex flex-col gap-1.5"><span class="text-xs text-ink-gray-5">Currency</span><RecordField :field="LINK('Currency')" :model-value="org.currency" @update:model-value="(v) => (org.currency = v as string)" /></label>
						<FormControl v-model="org.time_zone" type="select" label="Time zone" :options="timeZones" />
						<label class="flex flex-col gap-1.5"><span class="text-xs text-ink-gray-5">Language</span><RecordField :field="LINK('Language')" :model-value="org.language" @update:model-value="(v) => (org.language = v as string)" /></label>
					</div>
					<footer class="flex items-center gap-2 pt-2">
						<Button variant="solid" type="submit" label="Continue" :loading="busy" :disabled="!org.name" />
						<Button variant="ghost" label="Skip" @click="step++" />
					</footer>
				</form>

				<!-- 2: the Spaces the installed apps offer, and the workspaces they brought -->
				<div v-else-if="step === 1" class="flex flex-col gap-4">
					<div class="grid grid-cols-2 gap-2">
						<button
							v-for="template in setup.templates"
							:key="template.name"
							type="button"
							class="flex items-start gap-3 rounded-3 border p-3 text-left transition-colors duration-75"
							:class="chosen.has(template.name) ? 'border-outline-gray-5 bg-surface-gray-1' : 'border-outline-gray-2 hover:border-outline-gray-3'"
							@click="toggle(chosen, template.name)"
						>
							<span :class="spaceIcon(template.icon)" class="mt-0.5 size-4 shrink-0 text-ink-gray-6" />
							<span class="min-w-0 flex-1">
								<span class="flex items-center gap-2">
									<span class="text-sm font-medium text-ink-gray-8">{{ template.title }}</span>
									<span v-if="template.app && template.app !== 'frappe'" class="text-xs text-ink-gray-4">{{ template.app }}</span>
								</span>
								<span class="mt-0.5 line-clamp-2 block text-sm text-ink-gray-5">{{ template.description }}</span>
							</span>
							<span class="mt-0.5 size-4 shrink-0" :class="chosen.has(template.name) ? 'lucide-circle-check text-ink-gray-8' : 'lucide-circle text-ink-gray-3'" />
						</button>
					</div>
					<details v-if="setup.workspaces.length" class="rounded-3 border border-outline-gray-2">
						<summary class="cursor-pointer px-3 py-2 text-sm text-ink-gray-6">
							Also join workspaces your apps brought <span class="tabular-nums text-ink-gray-4">({{ setup.workspaces.length }})</span>
						</summary>
						<div class="grid grid-cols-2 gap-x-3 gap-y-1 px-3 pb-3">
							<label v-for="space in setup.workspaces" :key="space.name" class="flex items-center gap-2 text-sm text-ink-gray-7">
								<input type="checkbox" :checked="workspaces.has(space.name)" @change="toggle(workspaces, space.name)" />{{ space.title }}
							</label>
						</div>
					</details>
					<footer class="flex items-center gap-2 pt-2">
						<Button
							variant="solid"
							:label="`Set up ${chosen.size + workspaces.size} ${chosen.size + workspaces.size === 1 ? 'Space' : 'Spaces'}`"
							:loading="busy"
							:disabled="!chosen.size && !workspaces.size"
							@click="saveSpaces"
						/>
						<Button variant="ghost" label="Skip" @click="step++" />
					</footer>
				</div>

				<!-- 3: people, each into the Spaces they work in -->
				<div v-else class="flex flex-col gap-3">
					<div v-for="(person, i) in people" :key="i" class="flex flex-col gap-2 rounded-3 border border-outline-gray-2 p-3">
						<div class="flex items-center gap-2">
							<TextInput v-model="person.email" class="flex-1" type="email" placeholder="name@company.com" />
							<Button variant="ghost" icon="lucide-x" :disabled="people.length === 1" @click="people.splice(i, 1)" />
						</div>
						<div class="flex flex-wrap gap-1.5">
							<button
								v-for="space in mySpaces"
								:key="space"
								type="button"
								class="rounded-full border px-2.5 py-0.5 text-xs transition-colors duration-75"
								:class="person.spaces.includes(space) ? 'border-outline-gray-5 bg-surface-gray-2 text-ink-gray-8' : 'border-outline-gray-2 text-ink-gray-5 hover:border-outline-gray-3'"
								@click="person.spaces.includes(space) ? person.spaces.splice(person.spaces.indexOf(space), 1) : person.spaces.push(space)"
							>{{ space }}</button>
						</div>
					</div>
					<Button variant="ghost" icon-left="lucide-plus" label="Add someone" class="self-start" @click="people.push({ email: '', spaces: [] })" />
					<footer class="flex items-center gap-2 pt-2">
						<Button variant="solid" :label="invitable.length ? `Invite ${invitable.length} and finish` : 'Finish'" :loading="busy" @click="finish()" />
						<Button v-if="invitable.length" variant="ghost" label="Finish without inviting" @click="finish(false)" />
					</footer>
				</div>
			</div>
		</div>

		<!-- the assistant, for describing instead of clicking -->
		<aside class="flex h-full w-[360px] shrink-0 flex-col border-l border-outline-gray-1">
			<header class="flex h-10 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-3">
				<span class="lucide-sparkles size-3.5 text-ink-gray-5" />
				<h2 class="text-sm font-medium text-ink-gray-8">Or describe it</h2>
			</header>
			<div class="min-h-0 flex-1"><HomeChat :setup="{ site: true }" /></div>
		</aside>
	</div>
</template>

<script setup lang="ts">
import { Button, FormControl, LoadingIndicator, TextInput, call, toast } from "frappe-ui"
import { computed, reactive, ref } from "vue"
import { useRouter } from "vue-router"

import RecordField from "../../data/src/components/RecordField.vue"
import HomeChat from "./HomeChat.vue"
import { loadSpaces, loadWorkspace, pane, spaceIcon, spaces } from "./home"
import { errorText } from "./widgets/format"

const STEPS = ["Organization", "Spaces", "People"]
const HEADINGS = ["Tell us about your organization", "Pick the Spaces your teams work in", "Invite your people"]
const HINTS = [
	"We filled in what we could guess. Change anything that's off.",
	"Each Space is where a team works together. You can add more any time.",
	"Each person lands on a Home made from their Spaces, ready to work in.",
]
const LINK = (options: string) => ({ fieldname: options.toLowerCase(), fieldtype: "Link", options, label: options })

const router = useRouter()
document.title = "Set up"
pane.value.open = false

interface Setup {
	organization: { name: string; about: string; country: string; currency: string; time_zone: string; language: string }
	templates: { name: string; title: string; icon: string; description: string; app: string }[]
	workspaces: { name: string; title: string }[]
}
const setup = ref<Setup | null>(null)
const org = reactive({ name: "", about: "", country: "", currency: "", time_zone: "", language: "en" })
const timeZones = (Intl as unknown as { supportedValuesOf: (key: string) => string[] })
	.supportedValuesOf("timeZone")
	.map((zone) => ({ label: zone.replace(/_/g, " "), value: zone }))

const chosen = ref(new Set<string>())
const workspaces = ref(new Set<string>())
const toggle = (set: Set<string>, value: string) => (set.has(value) ? set.delete(value) : set.add(value))

call<Setup>("frappe.ai.setup_flow.get_setup", { time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone }).then((loaded) => {
	setup.value = loaded
	Object.assign(org, loaded.organization)
	// every Space on offer starts chosen but the blank Team one
	loaded.templates.forEach((template) => template.name !== "team" && chosen.value.add(template.name))
})

const step = ref(0)
const busy = ref(false)
async function run(work: () => Promise<unknown>) {
	busy.value = true
	try {
		await work()
		step.value++
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		busy.value = false
	}
}

const saveOrganization = () => run(() => call("frappe.ai.setup_flow.save_organization", { ...org, organization: org.name }))

const saveSpaces = () =>
	run(async () => {
		await call("frappe.ai.setup_flow.save_spaces", { templates_chosen: [...chosen.value], workspaces: [...workspaces.value] })
		await loadSpaces()
	})

const mySpaces = computed(() => spaces.value?.mine.map((space) => space.name) ?? [])
const people = ref([{ email: "", spaces: [] as string[] }])
const invitable = computed(() => people.value.filter((person) => /\S+@\S+\.\S+/.test(person.email)))

async function finish(invite = true) {
	busy.value = true
	try {
		if (invite && invitable.value.length) {
			await call("frappe.ai.setup_flow.invite", { people: invitable.value })
			toast.success(`Invited ${invitable.value.length}`)
		}
		await call("frappe.ai.workspace.finish_setup")
		await loadWorkspace()
		router.push("/home")
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		busy.value = false
	}
}
</script>
