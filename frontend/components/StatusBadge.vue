<script setup lang="ts">
const props = defineProps<{
  status: string
}>()

const variant = computed(() => {
  if (props.status.includes('SAVED') || props.status.includes('READY')) return 'ready'
  if (props.status.includes('FAILED') || props.status.includes('BLOCKED') || props.status.includes('ARCHIVED')) return 'blocked'
  return 'pending'
})
</script>

<template>
  <span class="badge" :class="variant">{{ status }}</span>
</template>
