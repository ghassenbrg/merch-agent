<script setup lang="ts">
import type { DraftSummary } from '~/composables/useApi'
import type { StatusResponse } from '~/composables/useApi'
import { Archive, Filter, Search, Trash2 } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const base = useApiBase()
const apiOptions = useApiFetchOptions()
const apiHeaders = useApiHeaders()
const query = ref('')
const statusFilter = ref('all')
const productFilter = ref('all')
const marketplaceFilter = ref('all')
const actionMessage = ref('')
const actionBusy = ref('')

const { data: drafts, pending, error, refresh } = await useFetch<DraftSummary[]>(`${base}/api/drafts`, apiOptions)

const statuses = computed(() => [...new Set((drafts.value || []).map((draft) => draft.status))].sort())
const products = computed(() => [...new Set((drafts.value || []).map((draft) => draft.product_label))].sort())
const marketplaces = computed(() => {
  const codes = (drafts.value || []).flatMap((draft) => draft.selected_marketplaces)
  return [...new Set(codes)].sort()
})

const filteredDrafts = computed(() => {
  const search = query.value.trim().toLowerCase()
  return (drafts.value || []).filter((draft) => {
    const matchesSearch = !search || [
      draft.title,
      draft.niche,
      draft.status,
      draft.product_label,
      draft.selected_marketplaces.join(' '),
    ].some((value) => value.toLowerCase().includes(search))

    return matchesSearch
      && (statusFilter.value === 'all' || draft.status === statusFilter.value)
      && (productFilter.value === 'all' || draft.product_label === productFilter.value)
      && (marketplaceFilter.value === 'all' || draft.selected_marketplaces.includes(marketplaceFilter.value))
  })
})

async function refreshDrafts() {
  await refresh()
}

function openDraft(draftId: string) {
  navigateTo(`/drafts/${draftId}`)
}

async function archiveDraft(draft: DraftSummary) {
  actionBusy.value = `archive:${draft.draft_id}`
  try {
    const response = await $fetch<StatusResponse>(`${base}/api/drafts/${draft.draft_id}/archive`, {
      method: 'POST',
      headers: apiHeaders,
    })
    actionMessage.value = response.message
    await refresh()
  } finally {
    actionBusy.value = ''
  }
}

async function deleteDraft(draft: DraftSummary) {
  const confirmed = window.confirm(`Delete "${draft.title}" locally? This removes the draft, run link, and generated artifact files.`)
  if (!confirmed) return

  actionBusy.value = `delete:${draft.draft_id}`
  try {
    const response = await $fetch<StatusResponse>(`${base}/api/drafts/${draft.draft_id}`, {
      method: 'DELETE',
      headers: apiHeaders,
    })
    actionMessage.value = response.message
    await refresh()
  } finally {
    actionBusy.value = ''
  }
}
</script>

<template>
  <div class="section-stack">
    <header class="command-bar">
      <div class="command-copy">
        <h1 class="page-title">Drafts</h1>
        <p class="page-subtitle">Generated local packages with status, product, and marketplace filters.</p>
      </div>
      <button class="btn" :disabled="pending" @click="refreshDrafts">Refresh</button>
    </header>

    <div v-if="actionMessage" class="notice">
      <span>{{ actionMessage }}</span>
    </div>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">Draft Library</h2>
          <span class="draft-meta">{{ filteredDrafts.length }} shown · {{ drafts?.length || 0 }} total</span>
        </div>
        <div class="search-box">
          <Search :size="15" />
          <input v-model="query" type="search" placeholder="Search drafts" />
        </div>
      </div>

      <div class="filter-row">
        <label>
          <Filter :size="14" />
          <span>Status</span>
          <select v-model="statusFilter">
            <option value="all">All statuses</option>
            <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
          </select>
        </label>
        <label>
          <span>Product</span>
          <select v-model="productFilter">
            <option value="all">All products</option>
            <option v-for="product in products" :key="product" :value="product">{{ product }}</option>
          </select>
        </label>
        <label>
          <span>Marketplace</span>
          <select v-model="marketplaceFilter">
            <option value="all">All marketplaces</option>
            <option v-for="marketplace in marketplaces" :key="marketplace" :value="marketplace">{{ marketplace }}</option>
          </select>
        </label>
      </div>

      <div v-if="pending" class="empty state-box">Loading draft library from {{ base }}...</div>
      <div v-else-if="error" class="empty state-box">Backend is not available at {{ base }}. Start FastAPI before reviewing packages.</div>
      <div v-else class="draft-list library-list">
        <div
          v-for="draft in filteredDrafts"
          :key="draft.draft_id"
          class="draft-list-item"
        >
          <DraftCard
            :draft="draft"
            :selected="false"
            @click="openDraft(draft.draft_id)"
          />
          <div class="draft-row-actions">
            <button
              class="btn"
              :disabled="!!actionBusy"
              title="Archive draft"
              @click="archiveDraft(draft)"
            >
              <Archive :size="15" />
              Archive
            </button>
            <button
              class="btn danger"
              :disabled="!!actionBusy"
              title="Delete draft"
              @click="deleteDraft(draft)"
            >
              <Trash2 :size="15" />
              Delete
            </button>
          </div>
        </div>
        <div v-if="!filteredDrafts.length" class="empty compact">No drafts match these filters. Clear search or run local generation from the dashboard.</div>
      </div>
    </section>
  </div>
</template>
