<script setup lang="ts">
import type { ConfigResponse, SettingsPatch } from '~/composables/useApi'
import { Save, ShieldCheck } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const base = useApiBase()
const saveMessage = ref('')
const isSaving = ref(false)
const enabledMarketplaces = ref<string[]>([])
const defaultProduct = ref('')

const { data: config, pending, error, refresh } = await useFetch<ConfigResponse>(`${base}/api/config`)

watchEffect(() => {
  if (!config.value) return
  enabledMarketplaces.value = [...(config.value.settings.enabled_marketplaces || [])]
  defaultProduct.value = config.value.settings.default_products?.[0] || ''
})

const marketplaces = computed(() => config.value?.marketplaces.marketplaces || [])
const languageSections = computed(() => config.value?.marketplaces.language_sections || {})
const products = computed(() => Object.entries(config.value?.product_templates.products || {}))
const templates = computed(() => Object.entries(config.value?.product_templates.product_templates || {}))
const prices = computed(() => config.value?.settings.default_prices || config.value?.pricing.default_prices || {})
const validationChecks = computed(() => Object.entries(config.value?.validation.ready_for_amazon_draft || {}))
const hardRules = computed(() => config.value?.amazon_upload_ui.amazon_upload_ui?.hard_rules || [])

function toggleMarketplace(code: string) {
  if (enabledMarketplaces.value.includes(code)) {
    enabledMarketplaces.value = enabledMarketplaces.value.filter((marketplace) => marketplace !== code)
  } else {
    enabledMarketplaces.value = [...enabledMarketplaces.value, code]
  }
}

async function saveSettings() {
  isSaving.value = true
  saveMessage.value = ''
  try {
    const patch: SettingsPatch = {
      default_products: defaultProduct.value ? [defaultProduct.value] : [],
      enabled_marketplaces: enabledMarketplaces.value,
    }
    await $fetch(`${base}/api/settings`, {
      method: 'PATCH',
      body: patch,
    })
    saveMessage.value = 'Settings saved locally.'
    await refresh()
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <div class="section-stack">
    <header class="command-bar">
      <div class="command-copy">
        <h1 class="page-title">Settings</h1>
        <p class="page-subtitle">Local config contracts for marketplaces, products, pricing, validation, and draft assist.</p>
      </div>
      <button class="btn primary" :disabled="pending || isSaving" @click="saveSettings">
        <Save :size="15" />
        {{ isSaving ? 'Saving...' : 'Save Settings' }}
      </button>
    </header>

    <div v-if="saveMessage" class="notice">
      <ShieldCheck :size="17" />
      <span>{{ saveMessage }}</span>
    </div>

    <section v-if="pending" class="panel">
      <div class="empty">Loading settings...</div>
    </section>
    <section v-else-if="error" class="panel">
      <div class="empty">Backend is not available at {{ base }}.</div>
    </section>
    <template v-else-if="config">
      <div class="detail-grid">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">Marketplaces</h2>
              <span class="draft-meta">{{ enabledMarketplaces.length }} enabled</span>
            </div>
          </div>
          <div class="panel-body table-list">
            <label
              v-for="marketplace in marketplaces"
              :key="marketplace.code"
              class="toggle-row"
            >
              <span>
                <strong>{{ marketplace.code }}</strong>
                <small>{{ marketplace.language_group }} · {{ marketplace.locale }}</small>
              </span>
              <input
                type="checkbox"
                :checked="enabledMarketplaces.includes(marketplace.code)"
                @change="toggleMarketplace(marketplace.code)"
              />
            </label>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">Products</h2>
              <span class="draft-meta">{{ products.length }} configured</span>
            </div>
          </div>
          <div class="panel-body section-stack">
            <div class="field">
              <label>Default product</label>
              <select v-model="defaultProduct" class="select-field">
                <option v-for="[code] in products" :key="code" :value="code">{{ code }}</option>
              </select>
            </div>
            <div class="table-list">
              <div v-for="[name, template] in templates" :key="name" class="table-row">
                <span>
                  <strong>{{ name }}</strong>
                  <small>{{ template.width }}x{{ template.height }} · {{ template.products.length }} products</small>
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div class="detail-grid">
        <section class="panel">
          <div class="panel-header">
            <h2 class="panel-title">Pricing</h2>
            <span class="draft-meta">Default prices</span>
          </div>
          <div class="panel-body table-list">
            <template v-for="(marketPrices, product) in prices" :key="product">
              <div v-for="(price, marketplace) in marketPrices" :key="`${product}-${marketplace}`" class="table-row">
                <span>
                  <strong>{{ product }} · {{ marketplace }}</strong>
                  <small>{{ price.currency }} {{ price.amount }}</small>
                </span>
              </div>
            </template>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <h2 class="panel-title">Validation</h2>
            <span class="draft-meta">{{ validationChecks.length }} ready checks</span>
          </div>
          <div class="panel-body table-list">
            <div v-for="[key, value] in validationChecks" :key="key" class="table-row">
              <span>
                <strong>{{ key }}</strong>
                <small>Required value: {{ value }}</small>
              </span>
              <StatusBadge :status="value === true || value === 'pass' ? 'READY' : 'PENDING'" />
            </div>
          </div>
        </section>
      </div>

      <div class="detail-grid">
        <section class="panel">
          <div class="panel-header">
            <h2 class="panel-title">Language Sections</h2>
          </div>
          <div class="panel-body table-list">
            <div v-for="(section, language) in languageSections" :key="language" class="table-row">
              <span>
                <strong>{{ language }}</strong>
                <small>{{ section.locale }} · {{ section.marketplaces.join(', ') }}</small>
              </span>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <h2 class="panel-title">Amazon Draft Assist</h2>
            <StatusBadge status="SAVE_DRAFT_ONLY" />
          </div>
          <div class="panel-body table-list">
            <div
              v-for="rule in hardRules"
              :key="rule"
              class="table-row"
            >
              <span>
                <strong>{{ rule }}</strong>
                <small>Guardrail</small>
              </span>
              <StatusBadge status="READY" />
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
