<script setup lang="ts">
import type { Draft } from '~/composables/useApi'
import { CloudUpload } from '@lucide/vue'

const props = defineProps<{
  draft: Draft
  busy: boolean
}>()

const emit = defineEmits<{
  start: []
}>()

const enabled = computed(() => (
  props.draft.status === 'READY_FOR_AMAZON_DRAFT'
  && props.draft.amazon_draft.eligible
  && !props.draft.amazon_draft.saved
))
</script>

<template>
  <button class="btn primary" :disabled="!enabled || busy" @click="emit('start')">
    <CloudUpload :size="15" />
    {{ busy ? 'Starting...' : draft.amazon_draft.saved ? 'Amazon Draft Saved' : 'Save as Amazon Draft' }}
  </button>
</template>
