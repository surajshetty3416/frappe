<script setup lang="ts">
import { computed, watch } from 'vue'
import useQuery from '../query/query'
import { FIELDTYPES } from '../helpers/constants'
import ColumnFilterValueSelector from '../query/components/ColumnFilterValueSelector.vue'
import {
	getOperatorOptions,
	getValueSelectorType,
	normalizeDateRange,
} from '../query/components/filter_utils'
import NumberRangeInput from '../query/components/NumberRangeInput.vue'
import RelativeDatePicker from '../query/components/RelativeDatePicker.vue'
import { ColumnOption, FilterOperator } from '../types/query.types'
import { WorkbookDashboardFilter } from '../types/workbook.types'
import useDashboard, { parseFilterLink } from './dashboard'
import { __ } from '../translation'
import { DatePicker, DateRangePicker } from 'frappe-ui'

// A selected filter tile's properties: its type, the charts it filters, and
// its default value. Each change writes the dashboard, which saves itself.
const props = defineProps<{ name: string; index: number }>()

const dashboard = useDashboard(props.name)
const filter = computed(() => dashboard.doc.items[props.index] as WorkbookDashboardFilter)

// The server replaces the default with the reader's `default_user_key`, which a
// shipped workbook sets. A default the author picks here must not be replaced.
watch(
	() => [filter.value?.default_operator, filter.value?.default_value],
	() => filter.value && delete filter.value.default_user_key,
)

// Once each: several cells can show readings of one Number chart, and a filter
// lands on the chart, not on the cell.
const charts = computed(() => dashboard.linkedCharts().filter(Boolean))

// The stores come from the dashboard's own map, which resolves one per chart the
// grid names. A store registers a resource, a watcher and a history when it is
// made, so it cannot be made in a computed.
const linkOptions = computed(() => {
	return charts.value
		.map((name) => dashboard.chartsByName[name])
		.filter(Boolean)
		.map((chart) => {
			const dependentColumns = chart.getDependentQueryColumns().map((group) => {
				return {
					group: group.group,
					options: disableColumnOptions(group.options),
				}
			})
			return {
				name: chart.doc.name,
				title: chart.doc.title,
				columns: dependentColumns,
			}
		})
})

const enabledLinks = computed(() => Object.keys(filter.value.links || {}))
function toggleLink(link: string) {
	filter.value.links ||= {}
	if (enabledLinks.value.includes(link)) {
		delete filter.value.links[link]
	} else {
		filter.value.links[link] = ''
	}
}

const FILTER_TYPES = {
	String: FIELDTYPES.TEXT,
	Number: FIELDTYPES.NUMBER,
	Date: FIELDTYPES.DATE,
}
function disableColumnOptions(options: ColumnOption[]) {
	return options.map((o) => {
		return {
			...o,
			disabled: !FILTER_TYPES[filter.value.filter_type].includes(o.data_type),
		}
	})
}

function onFilterTypeChange() {
	filter.value.default_operator = undefined
	filter.value.default_value = undefined
	filter.value.links = {}
}

const defaultOperatorOptions = computed(() => getOperatorOptions(filter.value.filter_type))

const defaultValueSelectorType = computed(() => {
	if (!filter.value.default_operator) return
	return getValueSelectorType(filter.value.default_operator, filter.value.filter_type)
})

function onDefaultOperatorChange(operator: FilterOperator) {
	const oldType = defaultValueSelectorType.value
	filter.value.default_operator = operator
	if (oldType !== getValueSelectorType(operator, filter.value.filter_type)) {
		filter.value.default_value = undefined
	}
}

const dateRangeVal = computed({
	get: () => normalizeDateRange(filter.value.default_value),
	set: (val: any) => {
		filter.value.default_value = normalizeDateRange(val)
	},
})

function clearDefault() {
	filter.value.default_operator = undefined
	filter.value.default_value = undefined
}

const sourceColumn = computed(() => {
	const firstChart = Object.keys(filter.value.links || {})[0]
	if (!firstChart) return
	const linkedColumn = filter.value.links[firstChart]
	return parseFilterLink(linkedColumn)
})

function defaultValuesProvider(search: string) {
	if (!sourceColumn.value) return Promise.resolve([])
	// preview values straight from the linked query — the dashboard endpoint only
	// serves columns already saved as filters, which this column may not be yet
	return useQuery(sourceColumn.value.query).getDistinctColumnValues(
		sourceColumn.value.column,
		search,
	)
}
</script>

<template>
	<div v-if="filter" class="flex flex-col gap-3">
		<FormControl
			v-model="filter.filter_type"
			:label="__('Type')"
			type="select"
			:options="Object.keys(FILTER_TYPES)"
			@update:modelValue="onFilterTypeChange"
		/>

		<div class="flex flex-col gap-1">
			<label class="text-xs text-ink-gray-5">{{ __('Linked charts') }}</label>
			<div v-for="link in linkOptions" :key="link.name" class="flex h-8 w-full items-center gap-2">
				<Toggle
					:modelValue="enabledLinks.includes(link.name)"
					@update:modelValue="toggleLink(link.name)"
				/>
				<p class="flex-1 truncate text-base text-ink-gray-8">{{ link.title }}</p>
				<Combobox
					v-if="enabledLinks.includes(link.name)"
					class="min-w-[10rem]"
					:placeholder="__('Select a column')"
					:options="link.columns"
					:modelValue="filter.links[link.name]"
					@update:modelValue="filter.links[link.name] = $event"
				/>
			</div>
		</div>

		<div class="flex flex-col gap-1.5">
			<div class="flex items-center justify-between">
				<label class="text-xs text-ink-gray-5">{{ __('Default value') }}</label>
				<Button
					v-if="filter.default_operator"
					variant="ghost"
					size="sm"
					:label="__('Clear')"
					@click="clearDefault"
				/>
			</div>
			<NumberRangeInput
				v-if="filter.filter_type === 'Number'"
				v-model:operator="filter.default_operator"
				v-model:value="filter.default_value as number"
			/>
			<div v-else class="flex flex-wrap items-start gap-2">
				<FormControl
					class="w-32 flex-shrink-0"
					type="select"
					:placeholder="__('Operator')"
					:modelValue="filter.default_operator"
					:options="defaultOperatorOptions"
					@update:modelValue="onDefaultOperatorChange($event)"
				/>
				<template v-if="defaultValueSelectorType">
					<DatePicker
						v-if="defaultValueSelectorType === 'date'"
						class="flex-1"
						:modelValue="filter.default_value as string"
						@update:modelValue="filter.default_value = $event"
					/>
					<DateRangePicker
						v-else-if="defaultValueSelectorType === 'date_range'"
						class="flex-1"
						v-model="dateRangeVal as [string, string]"
					/>
					<RelativeDatePicker
						v-else-if="defaultValueSelectorType === 'relative_date'"
						class="min-w-[15rem] flex-1"
						v-model="filter.default_value as string"
					/>
					<div v-else-if="defaultValueSelectorType === 'select'" class="flex-1">
						<ColumnFilterValueSelector
							v-model="filter.default_value as string[]"
							:valuesProvider="defaultValuesProvider"
						/>
					</div>
					<FormControl
						v-else-if="defaultValueSelectorType === 'text'"
						class="flex-1"
						v-model="filter.default_value"
						:placeholder="__('Value')"
						autocomplete="off"
					/>
				</template>
			</div>
		</div>
	</div>
</template>
