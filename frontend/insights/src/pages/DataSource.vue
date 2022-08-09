<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 v-if="dataSource.doc" class="text-3xl font-medium text-gray-900">
					{{ dataSource.doc.title }}
				</h1>
			</div>
		</template>
		<template #main>
			<div v-if="dataSource.tables" class="flex flex-1 flex-col">
				<div class="mb-4 flex space-x-4">
					<Input type="text" placeholder="Status" />
				</div>
				<div class="flex h-[calc(100%-3rem)] flex-col rounded-md border">
					<!-- List Header -->
					<div
						class="flex items-center justify-between border-b py-3 px-4 text-sm text-gray-500"
					>
						<p class="mr-4">
							<Input type="checkbox" class="rounded-md border-gray-400" />
						</p>
						<p class="flex-1">Label</p>
						<p class="flex-1">Table</p>
					</div>
					<ul
						role="list"
						class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-scroll"
					>
						<li v-for="table in dataSource.tables" :key="table.table">
							<router-link
								:to="{
									name: 'DataSourceTable',
									params: {
										name: dataSource.doc.name,
										table: table.table,
									},
								}"
								class="flex cursor-pointer items-center rounded-md py-3 px-4 hover:bg-gray-50"
							>
								<p class="mr-4">
									<Input type="checkbox" class="rounded-md border-gray-400" />
								</p>
								<p
									class="flex-1 whitespace-nowrap text-sm font-medium text-gray-900"
								>
									{{ table.label }}
								</p>
								<p class="flex-1 whitespace-nowrap text-sm text-gray-500">
									{{ table.table }}
								</p>
							</router-link>
						</li>
					</ul>
					<div class="flex w-full border-t px-4 py-2 text-sm text-gray-500">
						<p class="ml-auto">
							Showing {{ dataSource.tables.length }} of
							{{ dataSource.tables.length }}
						</p>
					</div>
				</div>
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import { useDataSource } from '@/utils/datasource'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dataSource = useDataSource(props.name)
window.dataSource = dataSource
</script>
