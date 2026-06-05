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

export const useApiBase = () => {
  const config = useRuntimeConfig()
  return config.public.apiBase as string
}

export const apiUrl = (path: string) => `${useApiBase()}${path}`
