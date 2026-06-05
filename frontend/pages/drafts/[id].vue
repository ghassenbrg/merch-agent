<script setup lang="ts">
import type { Draft, DraftArtifact, DraftChange, DraftEvent, StatusResponse } from '~/composables/useApi'
import {
  AlertTriangle,
  Archive,
  CheckCircle2,
  Download,
  ExternalLink,
  FileText,
  History,
  PackageCheck,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
} from '@lucide/vue'

definePageMeta({ layout: 'default' })

const route = useRoute()
const base = useApiBase()
const apiOptions = useApiFetchOptions()
const apiHeaders = useApiHeaders()
const draftId = computed(() => String(route.params.id))
const actionMessage = ref('')
const isAmazonBusy = ref(false)
const showAmazonConfirm = ref(false)
const actionBusy = ref('')
const isSavingReview = ref(false)
const reviewError = ref('')
const selectedMarketplaceCodes = ref<string[]>([])
const priceAmount = ref<number | null>(null)
const priceCurrency = ref('USD')
const manualStatus = ref('LISTING_READY')

const { data: draft, pending, error, refresh } = await useFetch<Draft>(
  () => `${base}/api/drafts/${draftId.value}`,
  { ...apiOptions, watch: [draftId] },
)
const { data: events, refresh: refreshEvents } = await useFetch<DraftEvent[]>(
  () => `${base}/api/drafts/${draftId.value}/events`,
  { ...apiOptions, watch: [draftId], default: () => [] },
)
const { data: changes, refresh: refreshChanges } = await useFetch<DraftChange[]>(
  () => `${base}/api/drafts/${draftId.value}/changes`,
  { ...apiOptions, watch: [draftId], default: () => [] },
)
const { data: artifacts, refresh: refreshArtifacts } = await useFetch<DraftArtifact[]>(
  () => `${base}/api/drafts/${draftId.value}/artifacts`,
  { ...apiOptions, watch: [draftId], default: () => [] },
)

watch(
  draft,
  (value) => {
    if (!value) return
    selectedMarketplaceCodes.value = value.marketplaces
      .filter((marketplace) => marketplace.selected)
      .map((marketplace) => marketplace.code)
    priceAmount.value = value.price.amount ?? null
    priceCurrency.value = value.price.currency || 'USD'
    manualStatus.value = value.status === 'READY_FOR_AMAZON_DRAFT' ? 'LISTING_READY' : value.status
  },
  { immediate: true },
)

const selectedProducts = computed(() => draft.value?.products.filter((product) => product.selected) || [])
const selectedMarketplaces = computed(() => draft.value?.marketplaces.filter((marketplace) => marketplace.selected) || [])
const excludedMarketplaces = computed(() => draft.value?.marketplaces.filter((marketplace) => !marketplace.selected) || [])
const downloadUrl = computed(() => `${base}/api/drafts/${draftId.value}/design/final.png`)
const primaryProduct = computed(() => selectedProducts.value[0] || draft.value?.products[0])
const confirmationDraftTitle = computed(() => draft.value?.listing_groups.English?.design_title || draftId.value)
const confirmationProduct = computed(() => primaryProduct.value?.label || primaryProduct.value?.code || 'Selected product')
const confirmationMarketplaces = computed(() => selectedMarketplaces.value.map((marketplace) => marketplace.code).join(', '))
const confirmationPrice = computed(() => {
  if (!draft.value?.price.amount) return 'Missing'
  const amount = Number(draft.value.price.amount).toFixed(2)
  if (draft.value.price.currency === 'USD') return `$${amount}`
  return `${draft.value.price.currency} ${amount}`
})
const editableStatuses = [
  'LISTING_READY',
  'HUMAN_REVIEW_REQUIRED',
  'BLOCKED_COMPLIANCE',
  'BLOCKED_ARTWORK',
  'ARTWORK_PENDING',
  'ARCHIVED',
]

const readinessItems = computed(() => {
  if (!draft.value) return []
  return [
    ['PNG valid', draft.value.validation.png_valid],
    ['Transparent artwork', draft.value.validation.transparent_background],
    ['Resolution matches template', draft.value.validation.correct_resolution],
    ['Policy precheck passed', draft.value.validation.amazon_policy_precheck === 'pass'],
    ['No human policy review needed', draft.value.validation.human_review_required !== true],
    ['No product terms in listing', draft.value.validation.product_type_terms_removed],
    ['Price and royalty configured', draft.value.validation.price_config_exists && draft.value.price.royalty_positive],
  ]
})

async function postDraftAction(action: string) {
  actionBusy.value = action
  try {
    const response = await $fetch<StatusResponse>(`${base}/api/drafts/${draftId.value}/${action}`, {
      method: 'POST',
      headers: apiHeaders,
    })
    actionMessage.value = response.message
    await Promise.all([refresh(), refreshEvents(), refreshChanges(), refreshArtifacts()])
  } finally {
    actionBusy.value = ''
  }
}

async function saveReviewSettings() {
  if (!draft.value) return
  isSavingReview.value = true
  reviewError.value = ''
  try {
    await $fetch<Draft>(`${base}/api/drafts/${draftId.value}`, {
      method: 'PATCH',
      headers: apiHeaders,
      body: {
        selected_marketplaces: selectedMarketplaceCodes.value,
        price: {
          currency: priceCurrency.value,
          amount: priceAmount.value,
        },
        status: manualStatus.value,
      },
    })
    actionMessage.value = 'Review edits saved locally. Manual approval is required before Amazon Draft Assist.'
    await Promise.all([refresh(), refreshEvents(), refreshChanges(), refreshArtifacts()])
  } catch (error: any) {
    reviewError.value = error?.data?.detail || 'Review edits could not be saved.'
  } finally {
    isSavingReview.value = false
  }
}

async function afterListingSaved(message: string) {
  actionMessage.value = message
  await Promise.all([refresh(), refreshEvents(), refreshChanges(), refreshArtifacts()])
}

async function startAmazonDraft() {
  if (!draft.value) return
  showAmazonConfirm.value = false
  isAmazonBusy.value = true
  try {
    const response = await $fetch<{ message: string }>(`${base}/api/drafts/${draftId.value}/amazon-draft`, {
      method: 'POST',
      headers: apiHeaders,
      body: {
        mode: 'controlled_live_save',
        manual_ui_triggered: true,
        save_draft_only_confirmed: true,
        visible_browser_confirmed: true,
        phase8_safety_confirmed: true,
      },
    })
    actionMessage.value = response.message
    await Promise.all([refresh(), refreshEvents(), refreshChanges(), refreshArtifacts()])
  } catch (error: any) {
    actionMessage.value = error?.data?.detail || 'Controlled live Amazon draft save failed.'
    await Promise.all([refresh(), refreshEvents(), refreshChanges(), refreshArtifacts()])
  } finally {
    isAmazonBusy.value = false
  }
}

function openAmazonConfirm() {
  showAmazonConfirm.value = true
}

function artifactHref(artifact: DraftArtifact) {
  return `${base}${artifact.url}`
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
            <div class="artifact-list">
              <a
                v-for="artifact in artifacts"
                :key="artifact.key"
                class="artifact-link"
                :class="{ missing: !artifact.exists }"
                :href="artifact.exists ? artifactHref(artifact) : undefined"
                target="_blank"
                rel="noreferrer"
              >
                <FileText :size="15" />
                <span>
                  <strong>{{ artifact.label }}</strong>
                  <small>{{ artifact.exists ? artifact.path : 'Missing artifact' }}</small>
                </span>
                <ExternalLink v-if="artifact.exists" :size="14" />
              </a>
              <div v-if="!artifacts?.length" class="empty compact">No package artifacts available yet.</div>
            </div>
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
                <PackageCheck v-else :size="15" />
                Manual Approve
              </button>
              <button class="btn" :disabled="!!actionBusy" @click="postDraftAction('regenerate-design')">Regenerate Design</button>
              <button class="btn" :disabled="!!actionBusy" @click="postDraftAction('regenerate-listing')">Regenerate Listing</button>
              <button class="btn danger" :disabled="!!actionBusy" @click="postDraftAction('reject')">Reject</button>
              <button class="btn danger" :disabled="!!actionBusy" @click="postDraftAction('archive')">
                <Archive :size="15" />
                Archive
              </button>
            </div>

            <div class="assist-panel">
              <div class="assist-copy">
                <ShieldCheck :size="20" />
                <div>
                  <strong>Amazon Draft Assist</strong>
                  <span>Manual launch, one package, save draft only. Auto-translation and publish are blocked.</span>
                </div>
              </div>
              <AmazonDraftButton :draft="draft" :busy="isAmazonBusy" @start="openAmazonConfirm" />
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

      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Review Edits</h2>
            <span class="draft-meta">Marketplace, price, and status edits are local and require manual approval.</span>
          </div>
          <button class="btn primary" :disabled="isSavingReview" @click="saveReviewSettings">
            <RefreshCw v-if="isSavingReview" :size="15" class="spin" />
            <Save v-else :size="15" />
            {{ isSavingReview ? 'Saving...' : 'Save Review Edits' }}
          </button>
        </div>
        <div class="panel-body review-edit-grid">
          <div class="section-stack">
            <div v-if="reviewError" class="inline-error">{{ reviewError }}</div>
            <div>
              <h3 class="subsection-title">Selected Marketplaces</h3>
              <div class="toggle-grid">
                <label v-for="marketplace in draft.marketplaces" :key="marketplace.code" class="toggle-row">
                  <span>
                    <strong>{{ marketplace.code }}</strong>
                    <small>{{ marketplace.language_group }} {{ marketplace.excluded_reason ? `· ${marketplace.excluded_reason}` : '' }}</small>
                  </span>
                  <input v-model="selectedMarketplaceCodes" type="checkbox" :value="marketplace.code" />
                </label>
              </div>
            </div>
          </div>
          <div class="section-stack">
            <div class="form-grid two">
              <div class="field">
                <label for="price-currency">Currency</label>
                <input id="price-currency" v-model="priceCurrency" class="text-field" type="text" />
              </div>
              <div class="field">
                <label for="price-amount">Price</label>
                <input id="price-amount" v-model.number="priceAmount" class="text-field" type="number" min="0" step="0.01" />
              </div>
            </div>
            <div class="field">
              <label for="manual-status">Manual status</label>
              <select id="manual-status" v-model="manualStatus" class="select-field">
                <option v-for="status in editableStatuses" :key="status" :value="status">{{ status }}</option>
              </select>
            </div>
            <div class="notice muted-notice">
              READY_FOR_AMAZON_DRAFT cannot be set here. Use Manual Approve after validation passes.
            </div>
          </div>
        </div>
      </section>

      <div class="detail-grid">
        <ValidationPanel :draft="draft" />
        <ScoreBreakdown :draft="draft" />
      </div>

      <ListingEditor :draft="draft" @saved="afterListingSaved" />

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

      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Listing Change History</h2>
            <span class="draft-meta">{{ changes?.length || 0 }} changes</span>
          </div>
          <History :size="18" />
        </div>
        <div class="panel-body table-list">
          <div v-for="change in changes" :key="`${change.created_at}-${change.field}`" class="table-row change-row">
            <span>
              <strong>{{ change.field }}</strong>
              <small>{{ change.note }} · {{ change.created_at }}</small>
              <small class="change-diff">{{ change.before ?? 'empty' }} -> {{ change.after ?? 'empty' }}</small>
            </span>
          </div>
          <div v-if="!changes?.length" class="empty compact">No listing edits recorded.</div>
        </div>
      </section>

      <div v-if="showAmazonConfirm" class="modal-backdrop" role="presentation">
        <section class="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="amazon-confirm-title">
          <div class="modal-header">
            <div>
              <h2 id="amazon-confirm-title" class="panel-title">Amazon Draft Assist</h2>
              <span class="draft-meta">Controlled live browser session, one package, save draft only.</span>
            </div>
            <button class="btn" :disabled="isAmazonBusy" @click="showAmazonConfirm = false">Cancel</button>
          </div>
          <div class="modal-body">
            <p>You are about to create an Amazon Merch draft for:</p>
            <p>
              Draft: {{ confirmationDraftTitle }}<br>
              Product: {{ confirmationProduct }}<br>
              Marketplaces: {{ confirmationMarketplaces }}<br>
              Price: {{ confirmationPrice }}<br>
              Action: Save Draft only
            </p>
            <p>
              This will open/control the browser.<br>
              The operator will never click Publish.
            </p>
            <div class="notice muted-notice">
              Phase 9 safety: the operator is limited to one selected package and only the Save Draft action is allowed.
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn" :disabled="isAmazonBusy" @click="showAmazonConfirm = false">Cancel</button>
            <button class="btn primary" :disabled="isAmazonBusy" @click="startAmazonDraft">
              <RefreshCw v-if="isAmazonBusy" :size="15" class="spin" />
              <ShieldCheck v-else :size="15" />
              Start Amazon Draft Assist
            </button>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
