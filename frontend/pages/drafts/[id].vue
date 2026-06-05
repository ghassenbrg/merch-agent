<script setup lang="ts">
import type { Draft, DraftEvent, StatusResponse } from '~/composables/useApi'
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from '@lucide/vue'

definePageMeta({ layout: 'default' })

const route = useRoute()
const base = useApiBase()
const draftId = computed(() => String(route.params.id))
const actionMessage = ref('')
const isAmazonBusy = ref(false)
const actionBusy = ref('')

const { data: draft, pending, error, refresh } = await useFetch<Draft>(
  () => `${base}/api/drafts/${draftId.value}`,
  { watch: [draftId] },
)
const { data: events, refresh: refreshEvents } = await useFetch<DraftEvent[]>(
  () => `${base}/api/drafts/${draftId.value}/events`,
  { watch: [draftId], default: () => [] },
)

const selectedProducts = computed(() => draft.value?.products.filter((product) => product.selected) || [])
const selectedMarketplaces = computed(() => draft.value?.marketplaces.filter((marketplace) => marketplace.selected) || [])
const excludedMarketplaces = computed(() => draft.value?.marketplaces.filter((marketplace) => !marketplace.selected) || [])
const downloadUrl = computed(() => `${base}/api/drafts/${draftId.value}/design/final.png`)

const readinessItems = computed(() => {
  if (!draft.value) return []
  return [
    ['PNG valid', draft.value.validation.png_valid],
    ['Transparent artwork', draft.value.validation.transparent_background],
    ['Resolution matches template', draft.value.validation.correct_resolution],
    ['Policy precheck passed', draft.value.validation.amazon_policy_precheck === 'pass'],
    ['No product terms in listing', draft.value.validation.product_type_terms_removed],
    ['Price and royalty configured', draft.value.validation.price_config_exists && draft.value.price.royalty_positive],
  ]
})

async function postDraftAction(action: string) {
  actionBusy.value = action
  try {
    const response = await $fetch<StatusResponse>(`${base}/api/drafts/${draftId.value}/${action}`, {
      method: 'POST',
    })
    actionMessage.value = response.message
    await Promise.all([refresh(), refreshEvents()])
  } finally {
    actionBusy.value = ''
  }
}

async function startAmazonDraft() {
  if (!draft.value) return
  const confirmed = window.confirm('Start Amazon Draft Assist for this one package only? The live browser operator is not enabled yet; this run is simulated.')
  if (!confirmed) return

  isAmazonBusy.value = true
  try {
    const response = await $fetch<{ message: string }>(`${base}/api/drafts/${draftId.value}/amazon-draft`, {
      method: 'POST',
    })
    actionMessage.value = response.message
    await Promise.all([refresh(), refreshEvents()])
  } finally {
    isAmazonBusy.value = false
  }
}
</script>

<template>
  <div class="section-stack">
    <header class="command-bar">
      <div class="command-copy">
        <h1 class="page-title">{{ draft?.listing_groups.English.design_title || 'Draft Detail' }}</h1>
        <p class="page-subtitle">{{ draft?.summary || draftId }}</p>
      </div>
      <NuxtLink class="btn" to="/drafts">Back to Drafts</NuxtLink>
    </header>

    <div v-if="actionMessage" class="notice">
      <Sparkles :size="17" />
      <span>{{ actionMessage }}</span>
    </div>

    <section v-if="pending" class="panel">
      <div class="empty">Loading draft...</div>
    </section>
    <section v-else-if="error" class="panel">
      <div class="empty">Draft was not found or the backend is unavailable.</div>
    </section>
    <template v-else-if="draft">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">{{ draft.niche }}</h2>
            <span class="draft-meta">{{ draft.draft_id }}</span>
          </div>
          <StatusBadge :status="draft.status" />
        </div>
        <div class="panel-body detail-grid">
          <div class="section-stack">
            <DesignPreview :draft="draft" />
            <a class="btn" :href="downloadUrl" target="_blank" rel="noreferrer">
              <Download :size="15" />
              Download Final PNG
            </a>
          </div>

          <div class="section-stack">
            <div class="meta-grid">
              <div class="meta-box">
                <div class="meta-label">Translation</div>
                <div class="meta-value">{{ draft.translation_mode }}</div>
              </div>
              <div class="meta-box">
                <div class="meta-label">Price</div>
                <div class="meta-value">
                  {{ draft.price.amount ? `${draft.price.currency} ${draft.price.amount}` : 'Missing' }}
                </div>
              </div>
              <div class="meta-box">
                <div class="meta-label">Trademark</div>
                <div class="meta-value">{{ draft.validation.trademark_precheck }}</div>
              </div>
              <div class="meta-box">
                <div class="meta-label">Royalty</div>
                <div class="meta-value">{{ draft.price.royalty_positive ? 'Positive' : 'Blocked' }}</div>
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
              <button class="btn" :disabled="!!actionBusy" @click="postDraftAction('approve')">
                <RefreshCw v-if="actionBusy === 'approve'" :size="15" class="spin" />
                Approve
              </button>
              <button class="btn" :disabled="!!actionBusy" @click="postDraftAction('regenerate-design')">Regenerate Design</button>
              <button class="btn" :disabled="!!actionBusy" @click="postDraftAction('regenerate-listing')">Regenerate Listing</button>
              <button class="btn danger" :disabled="!!actionBusy" @click="postDraftAction('reject')">Reject</button>
            </div>

            <div class="assist-panel">
              <div class="assist-copy">
                <ShieldCheck :size="20" />
                <div>
                  <strong>Amazon Draft Assist</strong>
                  <span>Manual launch, one package, save draft only. Auto-translation and publish are blocked.</span>
                </div>
              </div>
              <AmazonDraftButton :draft="draft" :busy="isAmazonBusy" @start="startAmazonDraft" />
            </div>
          </div>
        </div>
      </section>

      <div class="detail-grid">
        <section class="panel">
          <div class="panel-header">
            <h2 class="panel-title">Products</h2>
            <span class="draft-meta">{{ selectedProducts.length }} selected</span>
          </div>
          <div class="panel-body table-list">
            <div v-for="product in draft.products" :key="product.code" class="table-row">
              <span>
                <strong>{{ product.label || product.code }}</strong>
                <small>{{ product.template }} · {{ product.width }}x{{ product.height }}</small>
              </span>
              <StatusBadge :status="product.selected ? 'SELECTED' : 'ARCHIVED'" />
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <h2 class="panel-title">Marketplaces</h2>
            <span class="draft-meta">{{ selectedMarketplaces.length }} selected</span>
          </div>
          <div class="panel-body table-list">
            <div v-for="marketplace in selectedMarketplaces" :key="marketplace.code" class="table-row">
              <span>
                <strong>{{ marketplace.code }}</strong>
                <small>{{ marketplace.language_group }}</small>
              </span>
              <StatusBadge status="READY" />
            </div>
            <div v-for="marketplace in excludedMarketplaces" :key="marketplace.code" class="table-row muted-row">
              <span>
                <strong>{{ marketplace.code }}</strong>
                <small>{{ marketplace.excluded_reason || 'Excluded from this package.' }}</small>
              </span>
              <StatusBadge status="ARCHIVED" />
            </div>
          </div>
        </section>
      </div>

      <div class="detail-grid">
        <ValidationPanel :draft="draft" />
        <ScoreBreakdown :draft="draft" />
      </div>

      <ListingEditor :draft="draft" />

      <section class="panel">
        <div class="panel-header">
          <h2 class="panel-title">Draft Events</h2>
          <span class="draft-meta">{{ events?.length || 0 }} events</span>
        </div>
        <div class="panel-body table-list">
          <div v-for="event in events" :key="`${event.created_at}-${event.event_type}`" class="table-row">
            <span>
              <strong>{{ event.message }}</strong>
              <small>{{ event.event_type }} · {{ event.created_at }}</small>
            </span>
            <StatusBadge :status="event.to_status || event.event_type" />
          </div>
          <div v-if="!events?.length" class="empty compact">No draft events recorded.</div>
        </div>
      </section>
    </template>
  </div>
</template>
