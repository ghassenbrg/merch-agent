<script setup lang="ts">
import type { Draft } from '~/composables/useApi'

defineProps<{
  draft: Draft
}>()

const label = (key: string) => key.charAt(0).toUpperCase() + key.slice(1)
</script>

<template>
  <div class="panel">
    <div class="panel-header">
      <h2 class="panel-title">Score Breakdown</h2>
      <strong>{{ draft.score.overall }}</strong>
    </div>
    <div class="panel-body score-grid">
      <div v-for="(value, key) in draft.score" :key="key" class="score-row">
        <span>{{ label(String(key)) }}</span>
        <span class="score-track">
          <span class="score-fill" :style="{ width: `${value}%` }" />
        </span>
        <strong>{{ value }}</strong>
      </div>
    </div>
  </div>
</template>
