<script setup lang="ts">
import type { DraftSummary } from '~/composables/useApi'
import { ChevronRight } from '@lucide/vue'

defineProps<{
  draft: DraftSummary
  selected: boolean
}>()
</script>

<template>
  <button class="draft-row" :class="{ selected }">
    <div class="draft-title-line">
      <span class="draft-title">{{ draft.title }}</span>
      <StatusBadge :status="draft.status" />
    </div>
    <div class="draft-meta">{{ draft.niche }}</div>
    <div class="draft-card-footer">
      <span>{{ draft.product_label }} · {{ draft.selected_marketplaces.join(', ') || 'No marketplace' }}</span>
      <strong>Score {{ draft.score }}</strong>
      <ChevronRight :size="15" />
    </div>
  </button>
</template>
