<script setup lang="ts">
import type { Draft } from '~/composables/useApi'
import { RefreshCw, Save } from '@lucide/vue'

const props = defineProps<{
  draft: Draft
}>()

const emit = defineEmits<{
  saved: [message: string]
}>()

const base = useApiBase()
const isSaving = ref(false)
const errorMessage = ref('')
const form = ref<Record<string, Record<string, string>>>({})

const fields = [
  ['design_title', 'Design title', 'input'],
  ['brand', 'Brand', 'input'],
  ['feature_bullet_1', 'Feature bullet 1', 'textarea'],
  ['feature_bullet_2', 'Feature bullet 2', 'textarea'],
  ['product_description', 'Description', 'textarea'],
] as const

function resetForm() {
  form.value = Object.fromEntries(
    Object.entries(props.draft.listing_groups).map(([language, listing]) => [
      language,
      Object.fromEntries(
        fields.map(([field]) => [field, String(listing[field] || '')]),
      ),
    ]),
  )
}

watch(
  () => props.draft.draft_id,
  resetForm,
  { immediate: true },
)

async function saveListing() {
  isSaving.value = true
  errorMessage.value = ''
  try {
    await $fetch<Draft>(`${base}/api/drafts/${props.draft.draft_id}`, {
      method: 'PATCH',
      body: {
        listing_groups: form.value,
      },
    })
    emit('saved', 'Listing edits saved locally. Manual approval is required before Amazon Draft Assist.')
  } catch (error: any) {
    errorMessage.value = error?.data?.detail || 'Listing edits could not be saved.'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <div class="panel">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">Listing Editor</h2>
        <span class="draft-meta">{{ draft.translation_mode }} · local persistence</span>
      </div>
      <button class="btn primary" :disabled="isSaving" @click="saveListing">
        <RefreshCw v-if="isSaving" :size="15" class="spin" />
        <Save v-else :size="15" />
        {{ isSaving ? 'Saving...' : 'Save Listing' }}
      </button>
    </div>
    <div class="panel-body section-stack">
      <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
      <div v-for="(listing, language) in draft.listing_groups" :key="language" class="listing-group">
        <div class="draft-title-line">
          <strong>{{ language }}</strong>
          <span class="draft-meta">{{ listing.marketplaces?.join(', ') || 'No selected marketplaces' }}</span>
        </div>
        <div v-for="[field, label, control] in fields" :key="field" class="field">
          <label :for="`${draft.draft_id}-${language}-${field}`">{{ label }}</label>
          <textarea
            v-if="control === 'textarea'"
            :id="`${draft.draft_id}-${language}-${field}`"
            v-model="form[language][field]"
            class="text-field"
            rows="3"
          />
          <input
            v-else
            :id="`${draft.draft_id}-${language}-${field}`"
            v-model="form[language][field]"
            class="text-field"
            type="text"
          />
        </div>
      </div>
      <ul v-if="draft.listing_validation.warnings?.length" class="warning-list">
        <li v-for="warning in draft.listing_validation.warnings" :key="warning">{{ warning }}</li>
      </ul>
    </div>
  </div>
</template>
