export interface DraftSummary {
  draft_id: string
  status: string
  title: string
  niche: string
  score: number
  selected_marketplaces: string[]
  product_label: string
  eligible_for_amazon_draft: boolean
}

export interface DraftEvent {
  draft_id: string
  event_type: string
  from_status: string | null
  to_status: string | null
  message: string
  created_at: string
}

export interface DraftChange {
  field: string
  before: any
  after: any
  created_at: string
  note: string
}

export interface DraftArtifact {
  key: string
  label: string
  kind: string
  path: string
  url: string
  exists: boolean
}

export interface Draft {
  draft_id: string
  status: string
  niche: string
  summary: string
  score: Record<string, number>
  products: Array<Record<string, any>>
  marketplaces: Array<Record<string, any>>
  translation_mode: string
  design: Record<string, any>
  listing_groups: Record<string, Record<string, any>>
  validation: Record<string, any>
  listing_validation: Record<string, any>
  amazon_draft: Record<string, any>
  price: Record<string, any>
  research?: Record<string, any> | null
  change_history: DraftChange[]
}

export interface StatusResponse {
  draft_id: string
  status: string
  message: string
}

export interface RunResponse {
  runId: string
  status: string
  createdDraftIds: string[]
  message: string
}

export interface RunSummary {
  runId: string
  mode: string
  status: string
  created_at: string
  completed_at: string | null
  generatedDraftCount: number
  statusOutcomes: Record<string, number>
}

export interface RunDetail extends RunSummary {
  createdDraftIds: string[]
  logs: Array<{
    run_id: string
    level: string
    message: string
    created_at: string
  }>
}

export interface SchedulerStatus {
  schedulerEnabled: boolean
  stopSwitchEngaged: boolean
  running: boolean
  diskUsageMb: number
  diskLimitMb: number
  packagesGeneratedToday: number
  maxPackagesPerDay: number
  maxPackagesPerRun: number
  scheduledPackagesPerRun: number
  intervalMinutes: number
  cooldownMinutes: number
  nextRunAllowedAt: string | null
  lastScheduledRunId: string | null
  blockedReasons: string[]
}

export interface SchedulerRunResponse {
  status: string
  runId: string | null
  createdDraftIds: string[]
  message: string
  scheduler: SchedulerStatus
}

export interface ConfigResponse {
  product_templates: Record<string, any>
  marketplaces: Record<string, any>
  pricing: Record<string, any>
  validation: Record<string, any>
  amazon_upload_ui: Record<string, any>
  candidate_sources: Record<string, any>
  settings: Record<string, any>
}

export interface SettingsPatch {
  default_products?: string[]
  enabled_marketplaces?: string[]
  default_prices?: Record<string, any>
  autopilot_operations?: Record<string, any>
}

export const useApiBase = () => {
  const config = useRuntimeConfig()
  return config.public.apiBase as string
}

export const apiUrl = (path: string) => `${useApiBase()}${path}`
