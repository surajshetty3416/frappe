<template>
	<AppComponent :block="root" />
</template>

<script setup lang="ts">
import { provide, onUnmounted } from "vue"
import { usePageMeta } from "frappe-ui"

import { useLoadedPage } from "@studio/page/pageLoader"
import { onPageScriptHotUpdate } from "@studio/data/studioPageScripts"
import AppComponent from "@studio/components/AppComponent.vue"

import useAppStore from "@studio/stores/appStore"
import useComponentStore from "@studio/stores/componentStore"
import { pageScopeKey } from "@studio/stores/codeStore"

const { page, scope, root } = useLoadedPage()

provide(pageScopeKey, scope)
onUnmounted(() => scope.teardownPage())
onUnmounted(onPageScriptHotUpdate((name, setup) => scope.applyPageScriptHotUpdate(name, setup)))

useAppStore().activePage = page
useComponentStore().setComponents(page.components || [])
usePageMeta(() => ({ title: page.page_title }))
</script>
