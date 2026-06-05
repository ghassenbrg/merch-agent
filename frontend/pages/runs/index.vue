<script setup lang="ts">
import type { RunDetail, RunResponse, RunSummary } from '~/composables/useApi'
import { ClipboardList, Play, RefreshCw } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const base = useApiBase()
const selectedRunId = ref<string | null>(null)
const isRunning = ref(false)
const actionMessage = ref('')

const { data: runs, pending, error, refresh } = await useFetch<RunSummary[]>(`${base}/api/runs`)

watchEffect(() => {
  if (!selectedRunId.value && runs.value?.length) {
    selectedRunId.value = runs.value[0].runId
  }
})

const { data: selectedRun, refresh: refreshSelected } = await useFetch<RunDetail | null>(
  () => selectedRunId.value ? `${base}/api/runs/${selectedRunId.value}` : null,
  { watch: [selectedRunId] },
)

async function runAutopilot() {
  isRunning.value = true
  actionMessage.value = ''
  try {
    const response = await $fetch<RunResponse>(`${base}/api/workflows/autopilot/run`, {
      method: 'POST',
      body: {
        count: 2,
        default_product: 'standard_tshirt',
        explore_marketplaces: true,
        touch_amazon: false,
      },
    })
    actionMessage.value = response.message
    selectedRunId.value = response.runId
    await Promise.all([refresh(), refreshSelected()])
  } finally {
    isRunning.value = false
  }
}
</script>

<template>
  <div class="section-stack">
    <header class="command-bar">
      <div class="command-copy">
        <h1 class="page-title">Runs</h1>
        <p class="page-subtitle">Local autopilot history, status outcomes, and run logs.</p>
      </div>
      <div class="toolbar">
        <button class="btn" :disabled="pending" @click="refresh">Refresh</button>
        <button class="btn primary" :disabled="isRunning" @click="runAutopilot">
          <RefreshCw v-if="isRunning" :size="15" class="spin" />
          <Play v-else :size="15" />
          {{ isRunning ? 'Running...' : 'Run Local Autopilot' }}
        </button>
      </div>
    </header>

    <div v-if="actionMessage" class="notice">
      <ClipboardList :size="17" />
      <span>{{ actionMessage }}</span>
    </div>

    <div class="dashboard-grid">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Run History</h2>
            <span class="draft-meta">{{ runs?.length || 0 }} runs</span>
          </div>
        </div>
        <div v-if="pending" class="empty">Loading runs...</div>
        <div v-else-if="error" class="empty">Backend is not available at {{ base }}.</div>
        <div v-else class="draft-list">
          <button
            v-for="run in runs"
            :key="run.runId"
            class="draft-row"
            :class="{ selected: run.runId === selectedRunId }"
            @click="selectedRunId = run.runId"
          >
            <div class="draft-title-line">
              <span class="draft-title">{{ run.runId }}</span>
              <StatusBadge :status="run.status" />
            </div>
            <div class="draft-meta">{{ run.mode }} · {{ run.created_at }}</div>
            <div class="draft-card-footer">
              <span>{{ run.completed_at || 'In progress' }}</span>
              <strong>{{ run.generatedDraftCount }} drafts</strong>
            </div>
          </button>
          <div v-if="!runs?.length" class="empty compact">No local runs recorded.</div>
        </div>
      </section>

      <section v-if="selectedRun" class="section-stack">
        <div class="panel">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">{{ selectedRun.runId }}</h2>
              <span class="draft-meta">{{ selectedRun.created_at }} · {{ selectedRun.completed_at || 'In progress' }}</span>
            </div>
            <StatusBadge :status="selectedRun.status" />
          </div>
          <div class="panel-body section-stack">
            <div class="meta-grid">
              <div class="meta-box">
                <div class="meta-label">Mode</div>
                <div class="meta-value">{{ selectedRun.mode }}</div>
              </div>
              <div class="meta-box">
                <div class="meta-label">Generated Drafts</div>
                <div class="meta-value">{{ selectedRun.generatedDraftCount }}</div>
              </div>
            </div>
            <div class="table-list">
              <div v-for="(count, status) in selectedRun.statusOutcomes" :key="status" class="table-row">
                <span>
                  <strong>{{ status }}</strong>
                  <small>Status outcome</small>
                </span>
                <strong>{{ count }}</strong>
              </div>
              <div v-if="!Object.keys(selectedRun.statusOutcomes).length" class="empty compact">No draft outcomes for this run.</div>
            </div>
          </div>
        </div>

        <div class="detail-grid">
          <section class="panel">
            <div class="panel-header">
              <h2 class="panel-title">Generated Drafts</h2>
              <span class="draft-meta">{{ selectedRun.createdDraftIds.length }} packages</span>
            </div>
            <div class="panel-body table-list">
              <NuxtLink
                v-for="draftId in selectedRun.createdDraftIds"
                :key="draftId"
                class="table-row link-row"
                :to="`/drafts/${draftId}`"
              >
                <span>
                  <strong>{{ draftId }}</strong>
                  <small>Open package review</small>
                </span>
              </NuxtLink>
              <div v-if="!selectedRun.createdDraftIds.length" class="empty compact">No drafts were generated.</div>
            </div>
          </section>

          <section class="panel">
            <div class="panel-header">
              <h2 class="panel-title">Logs</h2>
              <span class="draft-meta">{{ selectedRun.logs.length }} entries</span>
            </div>
            <div class="panel-body table-list">
              <div v-for="log in selectedRun.logs" :key="`${log.created_at}-${log.message}`" class="table-row">
                <span>
                  <strong>{{ log.message }}</strong>
                  <small>{{ log.level }} · {{ log.created_at }}</small>
                </span>
              </div>
              <div v-if="!selectedRun.logs.length" class="empty compact">No logs recorded.</div>
            </div>
          </section>
        </div>
      </section>

      <section v-else class="panel">
        <div class="empty">Select a run to inspect.</div>
      </section>
    </div>
  </div>
</template>
