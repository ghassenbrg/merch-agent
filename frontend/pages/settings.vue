<script setup lang="ts">
import type { ConfigResponse, SettingsPatch } from '~/composables/useApi'
import { Save, ShieldCheck } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const base = useApiBase()
const apiOptions = useApiFetchOptions()
const apiHeaders = useApiHeaders()
const saveMessage = ref('')
const isSaving = ref(false)
const enabledMarketplaces = ref<string[]>([])
const defaultProduct = ref('')
const schedulerEnabled = ref(false)
const stopSwitchEngaged = ref(false)
const scheduledPackagesPerRun = ref(2)
const maxPackagesPerRun = ref(10)
const maxPackagesPerDay = ref(10)
const intervalMinutes = ref(1440)
const cooldownMinutes = ref(60)
const diskUsageLimitMb = ref(2048)

interface ProductTemplateConfig {
  width: number
  height: number
  products: string[]
}

const { data: config, pending, error, refresh } = await useFetch<ConfigResponse>(`${base}/api/config`, apiOptions)

watchEffect(() => {
  if (!config.value) return
  enabledMarketplaces.value = [...(config.value.settings.enabled_marketplaces || [])]
  defaultProduct.value = config.value.settings.default_products?.[0] || ''
  const operations = config.value.settings.autopilot_operations || {}
  schedulerEnabled.value = Boolean(operations.scheduler_enabled)
  stopSwitchEngaged.value = Boolean(operations.stop_switch_engaged)
  scheduledPackagesPerRun.value = Number(operations.scheduled_packages_per_run ?? 2)
  maxPackagesPerRun.value = Number(operations.max_packages_per_run ?? 10)
  maxPackagesPerDay.value = Number(operations.max_packages_per_day ?? 10)
  intervalMinutes.value = Number(operations.interval_minutes ?? 1440)
  cooldownMinutes.value = Number(operations.cooldown_minutes ?? 60)
  diskUsageLimitMb.value = Number(operations.disk_usage_limit_mb ?? 2048)
})

const marketplaces = computed(() => config.value?.marketplaces.marketplaces || [])
const languageSections = computed(() => config.value?.marketplaces.language_sections || {})
const products = computed(() => Object.entries(config.value?.product_templates.products || {}))
const templates = computed<[string, ProductTemplateConfig][]>(() => Object.entries(
  (config.value?.product_templates.product_templates || {}) as Record<string, ProductTemplateConfig>,
))
const prices = computed(() => config.value?.settings.default_prices || config.value?.pricing.default_prices || {})
const validationChecks = computed(() => Object.entries(config.value?.validation.ready_for_amazon_draft || {}))
const hardRules = computed(() => config.value?.amazon_upload_ui.amazon_upload_ui?.hard_rules || [])
const runtime = computed(() => config.value?.settings.runtime || {})

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
      autopilot_operations: {
        ...(config.value?.settings.autopilot_operations || {}),
        scheduler_enabled: schedulerEnabled.value,
        stop_switch_engaged: stopSwitchEngaged.value,
        scheduled_packages_per_run: scheduledPackagesPerRun.value,
        max_packages_per_run: maxPackagesPerRun.value,
        max_packages_per_day: maxPackagesPerDay.value,
        interval_minutes: intervalMinutes.value,
        cooldown_minutes: cooldownMinutes.value,
        disk_usage_limit_mb: diskUsageLimitMb.value,
        default_product: defaultProduct.value || 'standard_tshirt',
      },
    }
    await $fetch(`${base}/api/settings`, {
      method: 'PATCH',
      headers: apiHeaders,
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

      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Autopilot Operations</h2>
            <span class="draft-meta">Scheduled generation is local-only and cannot invoke Amazon Draft Assist.</span>
          </div>
          <StatusBadge :status="stopSwitchEngaged ? 'BLOCKED' : 'READY'" />
        </div>
        <div class="panel-body section-stack">
          <div class="detail-grid">
            <label class="toggle-row">
              <span>
                <strong>Local scheduler</strong>
                <small>Allows scheduled autopilot ticks to create local packages.</small>
              </span>
              <input v-model="schedulerEnabled" type="checkbox" />
            </label>
            <label class="toggle-row">
              <span>
                <strong>Stop switch</strong>
                <small>Blocks queued scheduled jobs and halts before the next local package.</small>
              </span>
              <input v-model="stopSwitchEngaged" type="checkbox" />
            </label>
          </div>
          <div class="meta-grid">
            <label class="field compact-field">
              <span>Scheduled packages</span>
              <input v-model.number="scheduledPackagesPerRun" class="text-field" type="number" min="0" max="10" />
            </label>
            <label class="field compact-field">
              <span>Max per run</span>
              <input v-model.number="maxPackagesPerRun" class="text-field" type="number" min="0" max="10" />
            </label>
            <label class="field compact-field">
              <span>Max per day</span>
              <input v-model.number="maxPackagesPerDay" class="text-field" type="number" min="0" max="100" />
            </label>
            <label class="field compact-field">
              <span>Interval minutes</span>
              <input v-model.number="intervalMinutes" class="text-field" type="number" min="0" max="10080" />
            </label>
            <label class="field compact-field">
              <span>Cooldown minutes</span>
              <input v-model.number="cooldownMinutes" class="text-field" type="number" min="0" max="10080" />
            </label>
            <label class="field compact-field">
              <span>Disk limit MB</span>
              <input v-model.number="diskUsageLimitMb" class="text-field" type="number" min="0" max="102400" />
            </label>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Security Posture</h2>
            <span class="draft-meta">{{ runtime.environment || 'local' }} · {{ runtime.auth_required ? 'auth required' : 'localhost only' }}</span>
          </div>
          <StatusBadge :status="runtime.auth_required && runtime.api_token_configured ? 'READY' : 'LOCAL_ONLY'" />
        </div>
        <div class="panel-body meta-grid">
          <div class="meta-box">
            <div class="meta-label">Exposure</div>
            <div class="meta-value">{{ runtime.exposed ? 'External' : 'Local' }}</div>
          </div>
          <div class="meta-box">
            <div class="meta-label">Allowed Origins</div>
            <div class="meta-value">{{ runtime.allowed_origins?.length || 0 }}</div>
          </div>
          <div class="meta-box">
            <div class="meta-label">Write Rate Limit</div>
            <div class="meta-value">{{ runtime.write_rate_limit_per_minute || 60 }}/min</div>
          </div>
          <div class="meta-box">
            <div class="meta-label">Log Retention</div>
            <div class="meta-value">{{ runtime.log_retention_days || 30 }} days</div>
          </div>
        </div>
      </section>

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
