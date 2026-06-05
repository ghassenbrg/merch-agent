<script setup lang="ts">
import type { Draft } from '~/composables/useApi'

defineProps<{
  draft: Draft
}>()
</script>

<template>
  <div class="panel">
    <div class="panel-header">
      <h2 class="panel-title">Listing Groups</h2>
      <span class="draft-meta">{{ draft.translation_mode }}</span>
    </div>
    <div class="panel-body section-stack">
      <div v-for="(listing, language) in draft.listing_groups" :key="language" class="listing-group">
        <div class="draft-title-line">
          <strong>{{ language }}</strong>
          <span class="draft-meta">{{ listing.marketplaces?.join(', ') }}</span>
        </div>
        <div class="field">
          <label>Design title</label>
          <div class="readonly-field">{{ listing.design_title }}</div>
        </div>
        <div class="field">
          <label>Brand</label>
          <div class="readonly-field">{{ listing.brand }}</div>
        </div>
        <div class="field">
          <label>Feature bullet 1</label>
          <div class="readonly-field">{{ listing.feature_bullet_1 }}</div>
        </div>
        <div class="field">
          <label>Feature bullet 2</label>
          <div class="readonly-field">{{ listing.feature_bullet_2 }}</div>
        </div>
        <div class="field">
          <label>Description</label>
          <div class="readonly-field">{{ listing.product_description }}</div>
        </div>
      </div>
      <ul v-if="draft.listing_validation.warnings?.length" class="warning-list">
        <li v-for="warning in draft.listing_validation.warnings" :key="warning">{{ warning }}</li>
      </ul>
    </div>
  </div>
</template>
