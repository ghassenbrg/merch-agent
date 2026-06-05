<script setup lang="ts">
import type { Draft } from '~/composables/useApi'

const props = defineProps<{
  draft: Draft
}>()

const base = useApiBase()
const apiHeaders = useApiHeaders()
const imageFailed = ref(false)
const objectUrl = ref('')
const directPreviewUrl = computed(() => `${base}/api/drafts/${props.draft.draft_id}/design/final.png`)
const usesProtectedImage = computed(() => Object.keys(apiHeaders).length > 0)
const previewUrl = computed(() => usesProtectedImage.value ? objectUrl.value : directPreviewUrl.value)
const hasFinalPng = computed(() => (
  Boolean(props.draft.design?.final_png)
  && !imageFailed.value
  && (!usesProtectedImage.value || Boolean(objectUrl.value))
))

function revokeObjectUrl() {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = ''
  }
}

async function loadProtectedImage() {
  imageFailed.value = false
  if (!usesProtectedImage.value || !import.meta.client) {
    revokeObjectUrl()
    return
  }
  try {
    const blob = await $fetch<Blob>(directPreviewUrl.value, {
      headers: apiHeaders,
      responseType: 'blob',
    })
    revokeObjectUrl()
    objectUrl.value = URL.createObjectURL(blob)
  } catch {
    imageFailed.value = true
  }
}

watch(
  () => props.draft.draft_id,
  () => {
    imageFailed.value = false
    loadProtectedImage()
  },
  { immediate: true },
)

onBeforeUnmount(revokeObjectUrl)
</script>

<template>
  <div>
    <div class="design-preview">
      <img
        v-if="hasFinalPng"
        class="print-art-image"
        :src="previewUrl"
        :alt="`${draft.listing_groups.English.design_title} final PNG`"
        @error="imageFailed = true"
      >
      <div v-else class="print-art">
        <strong>{{ draft.listing_groups.English.design_title }}</strong>
        <span>{{ draft.design.theme }}</span>
      </div>
    </div>
    <div class="meta-grid">
      <div class="meta-box">
        <div class="meta-label">Resolution</div>
        <div class="meta-value">{{ draft.design.width }} x {{ draft.design.height }}</div>
      </div>
      <div class="meta-box">
        <div class="meta-label">Placement</div>
        <div class="meta-value">{{ draft.design.placement }}</div>
      </div>
      <div class="meta-box">
        <div class="meta-label">PNG</div>
        <div class="meta-value">{{ draft.design.transparent ? 'Transparent' : 'Opaque' }}</div>
      </div>
      <div class="meta-box">
        <div class="meta-label">File Size</div>
        <div class="meta-value">{{ draft.design.file_size_mb }} MB</div>
      </div>
    </div>
  </div>
</template>
