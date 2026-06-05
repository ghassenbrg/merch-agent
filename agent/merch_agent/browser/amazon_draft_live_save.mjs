import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '../../..')
const requireFromFrontend = createRequire(path.join(repoRoot, 'frontend', 'package.json'))
const { chromium } = requireFromFrontend('playwright')

const fieldLabels = {
  design_title: 'Design title',
  brand: 'Brand',
  feature_bullet_1: 'Feature bullet 1',
  feature_bullet_2: 'Feature bullet 2',
  product_description: 'Product description',
}

function normalizeActionLabel(label) {
  return String(label || '').trim().toLowerCase().replace(/\s+/g, ' ')
}

function isDangerousAction(label, dangerousLabels) {
  const normalized = normalizeActionLabel(label)
  return dangerousLabels.some((dangerous) => normalized.includes(normalizeActionLabel(dangerous)))
}

function isSafeAction(label, safeLabels, dangerousLabels) {
  const normalized = normalizeActionLabel(label)
  if (isDangerousAction(label, dangerousLabels)) return false
  return safeLabels.some((safe) => normalized.includes(normalizeActionLabel(safe)))
}

function requireSelector(selectorMap, key) {
  const selector = selectorMap[key]
  if (!selector) throw new Error(`Missing Amazon upload selector: ${key}`)
  return selector
}

function selectorFor(selectorMap, key, replacements = {}) {
  let selector = requireSelector(selectorMap, key)
  for (const [name, value] of Object.entries(replacements)) {
    selector = selector.replaceAll(`{${name}}`, String(value))
  }
  return selector
}

function selectedItems(items) {
  return items.filter((item) => item.selected)
}

function selectedProduct(draft) {
  const products = selectedItems(draft.products)
  if (products.length !== 1) throw new Error(`Expected exactly one selected product, found ${products.length}`)
  return products[0]
}

function selectedLanguages(draft) {
  const languages = new Set(selectedItems(draft.marketplaces).map((marketplace) => marketplace.language_group || 'English'))
  return Object.keys(draft.listing_groups).filter((language) => languages.has(language))
}

function resolveRepoPath(value) {
  const candidate = path.resolve(repoRoot, String(value || ''))
  if (!candidate.startsWith(repoRoot)) throw new Error(`Path escapes repository root: ${value}`)
  return candidate
}

async function screenshot(page, screenshotDir, stepNumber, stepName, steps) {
  await fs.mkdir(screenshotDir, { recursive: true })
  const filename = `${String(stepNumber).padStart(2, '0')}-${stepName}.png`
  const target = path.join(screenshotDir, filename)
  await page.screenshot({ path: target, fullPage: true })
  steps.push({ step: stepName, screenshot: target })
}

async function clickLanguageToggleIfNeeded(page, locator) {
  const count = await locator.count()
  if (count === 0) return
  await locator.first().click()
}

async function main() {
  const inputIndex = process.argv.indexOf('--input')
  if (inputIndex < 0 || !process.argv[inputIndex + 1]) {
    throw new Error('Usage: node amazon_draft_live_save.mjs --input /path/input.json')
  }

  const input = JSON.parse(await fs.readFile(process.argv[inputIndex + 1], 'utf8'))
  const {
    draft,
    job_id: jobId,
    profile_dir: profileDir,
    screenshot_dir: screenshotDir,
    create_product_url: createProductUrl,
    selector_map: selectorMap,
    dangerous_action_labels: dangerousLabels,
    safe_action_labels: safeLabels,
  } = input

  if (!String(createProductUrl).startsWith('https://merch.amazon.')) {
    throw new Error('Controlled live save requires an https://merch.amazon.* create-product URL')
  }

  const selectorsUsed = []
  const used = (key, replacements = {}) => {
    const selector = selectorFor(selectorMap, key, replacements)
    selectorsUsed.push({ key, selector })
    return selector
  }

  const dangerousChecks = dangerousLabels.map((label) => ({
    label,
    blocked: !isSafeAction(label, safeLabels, dangerousLabels),
  }))
  if (dangerousChecks.some((check) => !check.blocked)) {
    throw new Error('Dangerous action blocker failed')
  }

  await fs.mkdir(profileDir, { recursive: true })
  const context = await chromium.launchPersistentContext(profileDir, {
    headless: false,
    viewport: { width: 1280, height: 900 },
    slowMo: 75,
  })
  const page = await context.newPage()
  const steps = []

  try {
    const product = selectedProduct(draft)
    const marketplaces = selectedItems(draft.marketplaces)
    if (!marketplaces.length) throw new Error('Expected at least one selected marketplace')

    await page.goto(createProductUrl, { waitUntil: 'domcontentloaded' })
    await screenshot(page, screenshotDir, 1, 'open-create-product', steps)

    await page.locator(used('upload_input')).setInputFiles(resolveRepoPath(draft.design?.final_png))
    await page.locator(used('upload_status')).waitFor({ state: 'visible', timeout: 60000 }).catch(() => {})
    await screenshot(page, screenshotDir, 2, 'upload-design', steps)

    await page.locator(used('product_type_select')).selectOption(product.code)
    await screenshot(page, screenshotDir, 3, 'select-product-type', steps)

    for (const marketplace of marketplaces) {
      await page.locator(used('marketplace_checkbox', { code: marketplace.code })).check()
    }
    await screenshot(page, screenshotDir, 4, 'select-marketplaces', steps)

    await page.locator(used('price_input')).fill(String(draft.price?.amount || ''))
    await screenshot(page, screenshotDir, 5, 'set-price', steps)

    await page.locator(used('translation_own_radio')).check()
    await screenshot(page, screenshotDir, 6, 'select-own-translations', steps)

    for (const language of selectedLanguages(draft)) {
      await clickLanguageToggleIfNeeded(page, page.locator(used('language_section_toggle', { language })))
    }
    await screenshot(page, screenshotDir, 7, 'expand-language-sections', steps)

    for (const language of selectedLanguages(draft)) {
      const listing = draft.listing_groups[language]
      for (const field of Object.keys(fieldLabels)) {
        await page.locator(used('listing_input', { language, field })).fill(String(listing[field] || ''))
      }
    }
    await screenshot(page, screenshotDir, 8, 'fill-listing-copy', steps)

    const warnings = await page.locator(used('warnings_panel')).textContent().catch(() => '')
    if (warnings && warnings.trim()) {
      throw new Error(`Amazon warning detected before Save Draft: ${warnings.trim()}`)
    }
    await screenshot(page, screenshotDir, 9, 'check-no-warnings', steps)

    const saveDraft = page.locator(used('save_draft_button'))
    const saveText = await saveDraft.textContent()
    if (!isSafeAction(saveText, safeLabels, dangerousLabels)) {
      throw new Error(`Save draft selector resolved to unsafe label: ${saveText}`)
    }
    await screenshot(page, screenshotDir, 10, 'before-save-draft', steps)
    await saveDraft.click()
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {})
    await screenshot(page, screenshotDir, 11, 'after-save-draft', steps)

    console.log(JSON.stringify({
      job_id: jobId,
      mode: 'controlled_live_amazon_save_draft',
      status: 'AMAZON_DRAFT_SAVED',
      browser_profile: profileDir,
      visible_browser: true,
      headless: false,
      touch_amazon: true,
      save_draft_clicked: true,
      publish_allowed: false,
      selected_product: product.code,
      selected_marketplaces: marketplaces.map((marketplace) => marketplace.code),
      selector_keys_used: [...new Set(selectorsUsed.map((item) => item.key))],
      selectors_used: selectorsUsed,
      dangerous_action_checks: dangerousChecks,
      screenshots: steps,
    }))
  } finally {
    await context.close()
  }
}

main().catch((error) => {
  console.error(error.stack || String(error))
  process.exit(1)
})
