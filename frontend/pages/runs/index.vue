<script setup lang="ts">
import type { RunDetail, RunResponse, RunSummary, SchedulerRunResponse, SchedulerStatus } from '~/composables/useApi'
import { ClipboardList, Play, RefreshCw, ShieldCheck } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const base = useApiBase()
const apiOptions = useApiFetchOptions()
const apiHeaders = useApiHeaders()
const selectedRunId = ref<string | null>(null)
const isRunning = ref(false)
const isSchedulerBusy = ref(false)
const actionMessage = ref('')
const liveResearchEnabled = ref(false)

const { data: runs, pending, error, refresh } = await useFetch<RunSummary[]>(`${base}/api/runs`, apiOptions)
const { data: scheduler, refresh: refreshScheduler } = await useFetch<SchedulerStatus>(`${base}/api/workflows/autopilot/scheduler`, apiOptions)
const { data: config } = await useFetch<any>(`${base}/api/config`, apiOptions)

watchEffect(() => {
  if (!selectedRunId.value && runs.value?.length) {
    selectedRunId.value = runs.value[0].runId
  }
  liveResearchEnabled.value = Boolean(config.value?.settings?.autopilot_operations?.live_research_enabled)
})

const { data: selectedRun, refresh: refreshSelected } = await useAsyncData<RunDetail | null>(
  'selected-run-detail',
  async () => {
    if (!selectedRunId.value) return null
    return await $fetch<RunDetail>(`${base}/api/runs/${selectedRunId.value}`, {
      headers: apiHeaders,
    })
  },
  { watch: [selectedRunId], default: () => null },
)

async function refreshRuns() {
  await refresh()
}

async function runAutopilot() {
  isRunning.value = true
  actionMessage.value = ''
  try {
    const response = await $fetch<RunResponse>(`${base}/api/workflows/autopilot/run`, {
      method: 'POST',
      headers: apiHeaders,
      body: {
        count: 2,
        default_product: 'standard_tshirt',
        explore_marketplaces: true,
        touch_amazon: false,
        production_mode: liveResearchEnabled.value,
      },
    })
    actionMessage.value = response.message
    selectedRunId.value = response.runId
    await Promise.all([refresh(), refreshSelected()])
  } finally {
    isRunning.value = false
  }
}

async function runScheduledTick() {
  isSchedulerBusy.value = true
  actionMessage.value = ''
  try {
    const response = await $fetch<SchedulerRunResponse>(`${base}/api/workflows/autopilot/scheduler/tick`, {
      method: 'POST',
      headers: apiHeaders,
    })
    actionMessage.value = response.message
    if (response.runId) {
      selectedRunId.value = response.runId
    }
    await Promise.all([refresh(), refreshSelected(), refreshScheduler()])
  } finally {
    isSchedulerBusy.value = false
  }
}

async function setSchedulerStop(engaged: boolean) {
  isSchedulerBusy.value = true
  actionMessage.value = ''
  try {
    await $fetch(`${base}/api/workflows/autopilot/scheduler/${engaged ? 'stop' : 'resume'}`, {
      method: 'POST',
      headers: apiHeaders,
    })
    actionMessage.value = engaged
      ? 'Scheduled local autopilot stop switch engaged.'
      : 'Scheduled local autopilot stop switch released.'
    await refreshScheduler()
  } finally {
    isSchedulerBusy.value = false
  }
}
</script>

<template>
  <div class="section-stack">
    <header class="command-bar">
      <div class="command-copy">
        <h1 class="page-title">Runs</h1>
        <p class="page-subtitle">Local autopilot history, status outcomes, generated package links, and run logs.</p>
      </div>
      <div class="toolbar">
        <button class="btn" :disabled="pending" @click="refreshRuns">Refresh</button>
        <label class="toggle-row inline-toggle">
          <span>
            <strong>Live research</strong>
            <small>Persist web snapshots before scoring.</small>
          </span>
          <input v-model="liveResearchEnabled" type="checkbox" />
        </label>
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

    <section v-if="scheduler" class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">Scheduler Operations</h2>
          <span class="draft-meta">Scheduled autopilot creates local packages only. Amazon Draft Assist is manual-only.</span>
        </div>
        <StatusBadge :status="scheduler.blockedReasons.length ? 'BLOCKED' : 'READY'" />
      </div>
      <div class="panel-body section-stack">
        <div class="meta-grid">
          <div class="meta-box">
            <div class="meta-label">Scheduler</div>
            <div class="meta-value">{{ scheduler.schedulerEnabled ? 'Enabled' : 'Disabled' }}</div>
          </div>
          <div class="meta-box">
            <div class="meta-label">Stop Switch</div>
            <div class="meta-value">{{ scheduler.stopSwitchEngaged ? 'Engaged' : 'Released' }}</div>
          </div>
          <div class="meta-box">
            <div class="meta-label">Today</div>
            <div class="meta-value">{{ scheduler.packagesGeneratedToday }} / {{ scheduler.maxPackagesPerDay }}</div>
          </div>
          <div class="meta-box">
            <div class="meta-label">Disk</div>
            <div class="meta-value">{{ scheduler.diskUsageMb }} / {{ scheduler.diskLimitMb }} MB</div>
          </div>
        </div>
        <div class="table-list">
          <div class="table-row">
            <span>
              <strong>{{ scheduler.scheduledPackagesPerRun }} scheduled · {{ scheduler.maxPackagesPerRun }} max per run</strong>
              <small>{{ scheduler.intervalMinutes }} minute interval · {{ scheduler.cooldownMinutes }} minute cooldown · next allowed {{ scheduler.nextRunAllowedAt || 'now' }}</small>
            </span>
            <ShieldCheck :size="17" />
          </div>
          <div v-if="scheduler.blockedReasons.length" class="table-row">
            <span>
              <strong>{{ scheduler.blockedReasons.join(', ') }}</strong>
              <small>Current scheduler gate</small>
            </span>
          </div>
          <div v-else class="table-row">
            <span>
              <strong>Ready for the next scheduled local run</strong>
              <small>Scheduled jobs cannot call Amazon Draft Assist.</small>
            </span>
          </div>
        </div>
        <div class="toolbar">
          <button class="btn" :disabled="isSchedulerBusy" @click="runScheduledTick">
            <RefreshCw v-if="isSchedulerBusy" :size="15" class="spin" />
            <Play v-else :size="15" />
            Run Due Scheduled Job
          </button>
          <button v-if="!scheduler.stopSwitchEngaged" class="btn danger" :disabled="isSchedulerBusy" @click="setSchedulerStop(true)">
            Engage Stop Switch
          </button>
          <button v-else class="btn" :disabled="isSchedulerBusy" @click="setSchedulerStop(false)">
            Release Stop Switch
          </button>
        </div>
      </div>
    </section>

    <div class="dashboard-grid">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Run History</h2>
            <span class="draft-meta">{{ runs?.length || 0 }} runs</span>
          </div>
        </div>
        <div v-if="pending" class="empty state-box">Loading local run history from {{ base }}...</div>
        <div v-else-if="error" class="empty state-box">Backend is not available at {{ base }}. Runs cannot be reviewed until FastAPI is online.</div>
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
          <div v-if="!runs?.length" class="empty compact">No local runs recorded. Generate packages from the dashboard to create history.</div>
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
              <div v-if="!selectedRun.createdDraftIds.length" class="empty compact">No drafts were generated by this local run.</div>
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
        <div class="empty state-box">Select a run to inspect local generation logs and package links.</div>
      </section>
    </div>
  </div>
</template>
