<script setup lang="ts">
import type { Draft, DraftSummary, RunResponse, StatusResponse } from '~/composables/useApi'
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ClipboardCheck,
  CloudUpload,
  Layers3,
  Play,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  XCircle,
} from '@lucide/vue'

definePageMeta({ layout: 'default' })

const base = useApiBase()
const selectedDraftId = ref<string | null>(null)
const actionMessage = ref('')
const isRunning = ref(false)
const isAmazonBusy = ref(false)
const query = ref('')
const activeFilter = ref<'all' | 'ready' | 'needs_fix' | 'saved' | 'blocked'>('all')
const bulkCount = ref(2)
const bulkProduct = ref('standard_tshirt')

const { data: drafts, pending, error, refresh } = await useFetch<DraftSummary[]>(`${base}/api/drafts`)
const { data: config } = await useFetch<any>(`${base}/api/config`)

watchEffect(() => {
  if (!selectedDraftId.value && drafts.value?.length) {
    selectedDraftId.value = drafts.value[0].draft_id
  }
})

const { data: selectedDraft, refresh: refreshSelected } = await useFetch<Draft | null>(
  () => selectedDraftId.value ? `${base}/api/drafts/${selectedDraftId.value}` : null,
  { watch: [selectedDraftId] },
)

const stats = computed(() => {
  const all = drafts.value || []
  return {
    ready: all.filter((draft) => draft.status === 'READY_FOR_AMAZON_DRAFT').length,
    needsFix: all.filter((draft) => draft.status === 'LISTING_READY' || draft.status.includes('NEEDS') || draft.status === 'HUMAN_REVIEW_REQUIRED').length,
    saved: all.filter((draft) => draft.status.includes('SAVED')).length,
    blocked: all.filter((draft) => draft.status.includes('BLOCKED') || draft.status.includes('FAILED')).length,
  }
})

const filterTabs = computed(() => [
  { key: 'all', label: 'All', count: drafts.value?.length || 0 },
  { key: 'ready', label: 'Ready', count: stats.value.ready },
  { key: 'needs_fix', label: 'Needs fix', count: stats.value.needsFix },
  { key: 'saved', label: 'Saved', count: stats.value.saved },
  { key: 'blocked', label: 'Blocked', count: stats.value.blocked },
] as const)

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

    const matchesFilter = activeFilter.value === 'all'
      || (activeFilter.value === 'ready' && draft.status === 'READY_FOR_AMAZON_DRAFT')
      || (activeFilter.value === 'needs_fix' && (draft.status === 'LISTING_READY' || draft.status.includes('NEEDS') || draft.status === 'HUMAN_REVIEW_REQUIRED'))
      || (activeFilter.value === 'saved' && draft.status.includes('SAVED'))
      || (activeFilter.value === 'blocked' && (draft.status.includes('BLOCKED') || draft.status.includes('FAILED')))

    return matchesSearch && matchesFilter
  })
})

const readinessItems = computed(() => {
  if (!selectedDraft.value) return []
  return [
    ['PNG valid', selectedDraft.value.validation.png_valid],
    ['Transparent artwork', selectedDraft.value.validation.transparent_background],
    ['Resolution matches template', selectedDraft.value.validation.correct_resolution],
    ['Policy precheck passed', selectedDraft.value.validation.amazon_policy_precheck === 'pass'],
    ['No human policy review needed', selectedDraft.value.validation.human_review_required !== true],
    ['No product terms in listing', selectedDraft.value.validation.product_type_terms_removed],
    ['Price and royalty configured', selectedDraft.value.validation.price_config_exists && selectedDraft.value.price.royalty_positive],
  ]
})

const productOptions = computed(() => Object.entries(config.value?.product_templates?.products || {}))

async function runAutopilot() {
  isRunning.value = true
  actionMessage.value = ''
  try {
    const response = await $fetch<RunResponse>(`${base}/api/workflows/autopilot/run`, {
      method: 'POST',
      body: {
        count: bulkCount.value,
        default_product: bulkProduct.value,
        explore_marketplaces: true,
        touch_amazon: false,
        production_mode: false,
      },
    })
    actionMessage.value = response.message
    if (response.createdDraftIds.length) {
      selectedDraftId.value = response.createdDraftIds[0]
    }
    await refresh()
  } finally {
    isRunning.value = false
  }
}

async function postDraftAction(action: string) {
  if (!selectedDraftId.value) return
  const response = await $fetch<StatusResponse>(`${base}/api/drafts/${selectedDraftId.value}/${action}`, {
    method: 'POST',
  })
  actionMessage.value = response.message
  await Promise.all([refresh(), refreshSelected()])
}

async function afterListingSaved(message: string) {
  actionMessage.value = message
  await Promise.all([refresh(), refreshSelected()])
}

async function startAmazonDraft() {
  if (!selectedDraftId.value) return
  const confirmed = window.confirm('Start Amazon Draft Assist for this one package only? The live browser operator is not enabled yet; this run is simulated.')
  if (!confirmed) return

  isAmazonBusy.value = true
  try {
    const response = await $fetch<{ message: string }>(`${base}/api/drafts/${selectedDraftId.value}/amazon-draft`, {
      method: 'POST',
    })
    actionMessage.value = response.message
    await Promise.all([refresh(), refreshSelected()])
  } finally {
    isAmazonBusy.value = false
  }
}
</script>

<template>
  <div>
    <header class="command-bar">
      <div class="command-copy">
        <h1 class="page-title">Draft Review Dashboard</h1>
        <p class="page-subtitle">Review local packages, fix blockers, and launch draft assist only by explicit action.</p>
      </div>
      <div class="system-strip">
        <span class="system-pill">
          <CheckCircle2 :size="15" />
          API connected
        </span>
        <span class="system-pill muted">Amazon: manual only</span>
      </div>
      <div class="toolbar">
        <button class="btn primary" :disabled="isRunning" @click="runAutopilot">
          <RefreshCw v-if="isRunning" :size="15" class="spin" />
          <Play v-else :size="15" />
          {{ isRunning ? 'Running...' : 'Generate Local Packages' }}
        </button>
      </div>
    </header>

    <section class="panel bulk-panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">Bulk Local Generation</h2>
          <span class="draft-meta">Creates local packages only. Amazon batch actions are not available.</span>
        </div>
        <Layers3 :size="18" />
      </div>
      <div class="panel-body bulk-controls">
        <label class="field compact-field">
          <span>Packages</span>
          <input v-model.number="bulkCount" class="text-field" type="number" min="1" max="10" />
        </label>
        <label class="field compact-field">
          <span>Product</span>
          <select v-model="bulkProduct" class="select-field">
            <option value="standard_tshirt">standard_tshirt</option>
            <option v-for="[code] in productOptions" :key="String(code)" :value="String(code)">{{ code }}</option>
          </select>
        </label>
        <div class="notice muted-notice">
          <Settings2 :size="16" />
          Autopilot request always sends touch_amazon=false and stops at local review status.
        </div>
      </div>
    </section>

    <section class="metric-grid">
      <div class="metric-card">
        <span class="metric-icon ready"><ClipboardCheck :size="18" /></span>
        <span class="metric-label">Ready</span>
        <strong>{{ stats.ready }}</strong>
      </div>
      <div class="metric-card">
        <span class="metric-icon warning"><AlertTriangle :size="18" /></span>
        <span class="metric-label">Needs Fix</span>
        <strong>{{ stats.needsFix }}</strong>
      </div>
      <div class="metric-card">
        <span class="metric-icon saved"><CloudUpload :size="18" /></span>
        <span class="metric-label">Saved</span>
        <strong>{{ stats.saved }}</strong>
      </div>
      <div class="metric-card">
        <span class="metric-icon blocked"><XCircle :size="18" /></span>
        <span class="metric-label">Blocked</span>
        <strong>{{ stats.blocked }}</strong>
      </div>
    </section>

    <div v-if="actionMessage" class="notice">
      <Sparkles :size="17" />
      <span>{{ actionMessage }}</span>
    </div>

    <div class="dashboard-grid">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Draft Queue</h2>
            <span class="draft-meta">{{ filteredDrafts.length }} shown · {{ drafts?.length || 0 }} total</span>
          </div>
          <div class="search-box">
            <Search :size="15" />
            <input v-model="query" type="search" placeholder="Search drafts" />
          </div>
        </div>
        <div class="filter-tabs">
          <button
            v-for="tab in filterTabs"
            :key="tab.key"
            :class="{ active: activeFilter === tab.key }"
            @click="activeFilter = tab.key"
          >
            {{ tab.label }}
            <span>{{ tab.count }}</span>
          </button>
        </div>
        <div v-if="pending" class="empty state-box">Loading drafts from {{ base }}...</div>
        <div v-else-if="error" class="empty state-box">Backend is not available at {{ base }}. Check that FastAPI is running before review.</div>
        <div v-else class="draft-list">
          <DraftCard
            v-for="draft in filteredDrafts"
            :key="draft.draft_id"
            :draft="draft"
            :selected="draft.draft_id === selectedDraftId"
            @click="selectedDraftId = draft.draft_id"
          />
          <div v-if="!filteredDrafts.length" class="empty compact">No drafts match this view. Clear filters or generate local packages.</div>
        </div>
      </section>

      <section v-if="selectedDraft" class="section-stack">
        <div class="panel">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">{{ selectedDraft.listing_groups.English.design_title }}</h2>
              <div class="draft-meta">{{ selectedDraft.summary }}</div>
            </div>
            <StatusBadge :status="selectedDraft.status" />
          </div>
          <div class="panel-body detail-grid">
            <DesignPreview :draft="selectedDraft" />
            <div class="section-stack">
              <div class="meta-grid">
                <div class="meta-box">
                  <div class="meta-label">Product</div>
                  <div class="meta-value">{{ selectedDraft.products[0].label }}</div>
                </div>
                <div class="meta-box">
                  <div class="meta-label">Marketplaces</div>
                  <div class="meta-value">
                    {{ selectedDraft.marketplaces.filter((marketplace) => marketplace.selected).map((marketplace) => marketplace.code).join(', ') }}
                  </div>
                </div>
                <div class="meta-box">
                  <div class="meta-label">Translation</div>
                  <div class="meta-value">{{ selectedDraft.translation_mode }}</div>
                </div>
                <div class="meta-box">
                  <div class="meta-label">Price</div>
                  <div class="meta-value">
                    {{ selectedDraft.price.amount ? `${selectedDraft.price.currency} ${selectedDraft.price.amount}` : 'Missing' }}
                  </div>
                </div>
              </div>
              <div class="readiness-strip">
                <div
                  v-for="[label, passed] in readinessItems"
                  :key="label"
                  class="readiness-chip"
                  :class="{ pass: passed }"
                >
                  <CheckCircle2 v-if="passed" :size="14" />
                  <AlertTriangle v-else :size="14" />
                  {{ label }}
                </div>
              </div>
              <div class="toolbar action-toolbar">
                <button class="btn" @click="postDraftAction('approve')">Approve</button>
                <button class="btn" @click="postDraftAction('regenerate-design')">Regenerate Design</button>
                <button class="btn" @click="postDraftAction('regenerate-listing')">Regenerate Listing</button>
                <button class="btn danger" @click="postDraftAction('reject')">Reject</button>
              </div>
              <div class="assist-panel">
                <div class="assist-copy">
                  <ShieldCheck :size="20" />
                  <div>
                    <strong>Amazon Draft Assist</strong>
                    <span>Manual launch, one package, save draft only. Auto-translation and publish are blocked.</span>
                  </div>
                </div>
                <AmazonDraftButton :draft="selectedDraft" :busy="isAmazonBusy" @start="startAmazonDraft" />
              </div>
            </div>
          </div>
        </div>

        <div class="detail-grid">
          <ValidationPanel :draft="selectedDraft" />
          <ScoreBreakdown :draft="selectedDraft" />
        </div>

        <ListingEditor :draft="selectedDraft" @saved="afterListingSaved" />
      </section>

      <section v-else class="panel">
        <div class="empty state-box">Select a draft to review, or generate local packages to populate the queue.</div>
      </section>
    </div>
  </div>
</template>
