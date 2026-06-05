<script setup lang="ts">
import type { Draft } from '~/composables/useApi'

defineProps<{
  draft: Draft
}>()

const labels: Record<string, string> = {
  png_valid: 'PNG valid',
  transparent_background: 'Transparent background',
  correct_resolution: 'Correct resolution',
  file_size_under_limit: 'File size under limit',
  design_not_too_small: 'Design not too small',
  design_not_cropped: 'Design not cropped',
  product_type_terms_removed: 'Product type terms removed',
  listing_min_lengths_passed: 'Listing min lengths passed',
  selected_marketplaces_have_copy: 'Selected marketplaces have copy',
  price_config_exists: 'Price config exists',
}
</script>

<template>
  <div class="panel">
    <div class="panel-header">
      <h2 class="panel-title">Validation</h2>
      <StatusBadge :status="draft.amazon_draft.eligible ? 'READY' : 'BLOCKED'" />
    </div>
    <div class="panel-body check-list">
      <div v-for="(label, key) in labels" :key="key" class="check-item">
        <span class="check-dot" :class="{ pass: draft.validation[key] === true }" />
        <span>{{ label }}</span>
      </div>
      <div class="check-item">
        <span class="check-dot" :class="{ pass: draft.validation.trademark_precheck === 'pass' }" />
        <span>Trademark precheck: {{ draft.validation.trademark_precheck }}</span>
      </div>
      <div class="check-item">
        <span class="check-dot" :class="{ pass: draft.validation.amazon_policy_precheck === 'pass' }" />
        <span>Amazon policy precheck: {{ draft.validation.amazon_policy_precheck }}</span>
      </div>
    </div>
  </div>
</template>
