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
  return String(label).trim().toLowerCase().replace(/\s+/g, ' ')
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

function htmlEscape(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function selectedItems(items) {
  return items.filter((item) => item.selected)
}

function selectedProduct(draft) {
  return selectedItems(draft.products)[0] || draft.products[0]
}

function selectedLanguages(draft) {
  const languages = new Set(selectedItems(draft.marketplaces).map((marketplace) => marketplace.language_group || 'English'))
  return Object.keys(draft.listing_groups).filter((language) => languages.has(language))
}

function buildMockPage(draft, dangerousLabels) {
  const product = selectedProduct(draft)
  const products = draft.products.map((item) => (
    `<option value="${htmlEscape(item.code)}">${htmlEscape(item.label || item.code)}</option>`
  )).join('')
  const marketplaces = draft.marketplaces.map((marketplace) => (
    `<label><input type="checkbox" data-amazon-draft-marketplace="${htmlEscape(marketplace.code)}"> ${htmlEscape(marketplace.code)}</label>`
  )).join('')
  const languageSections = Object.entries(draft.listing_groups).map(([language, listing]) => {
    const inputs = Object.keys(fieldLabels).map((field) => (
      `<label>${fieldLabels[field]}<textarea data-amazon-draft-listing="${htmlEscape(language)}:${field}">${htmlEscape(listing[field] || '')}</textarea></label>`
    )).join('')
    return `
      <section data-amazon-draft-language="${htmlEscape(language)}">
        <button type="button" data-amazon-draft-language-toggle="${htmlEscape(language)}">Expand ${htmlEscape(language)}</button>
        <div class="language-fields">${inputs}</div>
      </section>
    `
  }).join('')
  const dangerousButtons = dangerousLabels.map((label) => (
    `<button type="button" data-amazon-dangerous-action="${htmlEscape(label)}">${htmlEscape(label)}</button>`
  )).join('')

  return `
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Amazon Draft Assist Dry Run</title>
        <style>
          body { font-family: Inter, system-ui, sans-serif; margin: 24px; color: #102125; background: #eef4f6; }
          main { max-width: 1040px; margin: 0 auto; display: grid; gap: 16px; }
          section, header { background: white; border: 1px solid #d9e5e8; border-radius: 8px; padding: 16px; }
          label { display: grid; gap: 6px; margin: 8px 0; font-weight: 700; }
          input, textarea, select { border: 1px solid #b7cbd0; border-radius: 8px; min-height: 34px; padding: 7px 9px; font: inherit; }
          textarea { min-height: 62px; }
          button { min-height: 34px; border-radius: 8px; border: 1px solid #b7cbd0; background: #fff; margin: 4px 6px 4px 0; font-weight: 800; }
          [data-amazon-draft-action="save-draft"] { background: #0f8f86; color: white; border-color: #0f8f86; }
          [data-amazon-dangerous-action] { background: #fff0ee; color: #bd3b2f; border-color: #f4c4be; }
          .status { color: #07645f; font-weight: 800; }
          .language-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
        </style>
      </head>
      <body>
        <main>
          <header>
            <h1>Amazon Draft Assist Dry Run</h1>
            <p class="status" data-amazon-draft-field="dry-run-status">Local mock only. No Amazon URL opened.</p>
            <p>Draft: ${htmlEscape(draft.listing_groups.English?.design_title || draft.draft_id)}</p>
            <p>Product: ${htmlEscape(product.label || product.code)}</p>
          </header>
          <section>
            <h2>Artwork and products</h2>
            <input data-amazon-draft-field="upload-input" type="file" aria-label="Upload design">
            <p data-amazon-draft-field="upload-status">No file selected</p>
            <label>Product type<select data-amazon-draft-field="product-type">${products}</select></label>
            <div>${marketplaces}</div>
            <label>Price<input data-amazon-draft-field="price" inputmode="decimal"></label>
          </section>
          <section>
            <h2>Translations</h2>
            <label><input type="radio" name="translation" data-amazon-draft-field="translation-own"> No, I'll provide my own translations</label>
          </section>
          ${languageSections}
          <section>
            <h2>Warnings</h2>
            <div data-amazon-draft-field="warnings"></div>
            <button type="button" data-amazon-draft-action="save-draft">Save Draft</button>
            ${dangerousButtons}
          </section>
        </main>
      </body>
    </html>
  `
}

async function screenshot(page, screenshotDir, stepNumber, stepName, steps) {
  await fs.mkdir(screenshotDir, { recursive: true })
  const filename = `${String(stepNumber).padStart(2, '0')}-${stepName}.png`
  const target = path.join(screenshotDir, filename)
  await page.screenshot({ path: target, fullPage: true })
  steps.push({ step: stepName, screenshot: target })
}

async function main() {
  const inputIndex = process.argv.indexOf('--input')
  if (inputIndex < 0 || !process.argv[inputIndex + 1]) {
    throw new Error('Usage: node amazon_draft_dry_run.mjs --input /path/input.json')
  }

  const input = JSON.parse(await fs.readFile(process.argv[inputIndex + 1], 'utf8'))
  const {
    draft,
    job_id: jobId,
    profile_dir: profileDir,
    screenshot_dir: screenshotDir,
    selector_map: selectorMap,
    dangerous_action_labels: dangerousLabels,
    safe_action_labels: safeLabels,
  } = input
  const selectorsUsed = []
  const used = (key, replacements = {}) => {
    const selector = selectorFor(selectorMap, key, replacements)
    selectorsUsed.push({ key, selector })
    return selector
  }

  await fs.mkdir(profileDir, { recursive: true })
  const context = await chromium.launchPersistentContext(profileDir, {
    headless: true,
    viewport: { width: 1280, height: 900 },
  })
  const page = await context.newPage()
  const steps = []

  try {
    const dangerousChecks = dangerousLabels.map((label) => ({
      label,
      blocked: !isSafeAction(label, safeLabels, dangerousLabels),
    }))
    if (dangerousChecks.some((check) => !check.blocked)) {
      throw new Error('Dangerous action blocker failed')
    }

    const safeSaveLabel = 'Save Draft'
    if (!isSafeAction(safeSaveLabel, safeLabels, dangerousLabels)) {
      throw new Error('Save Draft was not recognized as a safe label')
    }

    await page.setContent(buildMockPage(draft, dangerousLabels), { waitUntil: 'domcontentloaded' })
    await screenshot(page, screenshotDir, 1, 'open-create-product-mock', steps)

    await page.locator(used('upload_input')).evaluate((input) => {
      input.dataset.dryRunTouched = 'true'
    })
    await page.locator(used('upload_status')).evaluate((node, value) => {
      node.textContent = value
    }, `Dry-run selected ${draft.design?.final_png || 'final.png'}`)
    await screenshot(page, screenshotDir, 2, 'upload-design-preview', steps)

    const product = selectedProduct(draft)
    await page.locator(used('product_type_select')).selectOption(product.code)
    await screenshot(page, screenshotDir, 3, 'select-product-type', steps)

    for (const marketplace of selectedItems(draft.marketplaces)) {
      await page.locator(used('marketplace_checkbox', { code: marketplace.code })).check()
    }
    await screenshot(page, screenshotDir, 4, 'select-marketplaces', steps)

    await page.locator(used('price_input')).fill(String(draft.price?.amount || ''))
    await screenshot(page, screenshotDir, 5, 'set-price', steps)

    await page.locator(used('translation_own_radio')).check()
    await screenshot(page, screenshotDir, 6, 'select-own-translations', steps)

    for (const language of selectedLanguages(draft)) {
      await page.locator(used('language_section_toggle', { language })).click()
    }
    await screenshot(page, screenshotDir, 7, 'expand-language-sections', steps)

    for (const language of selectedLanguages(draft)) {
      const listing = draft.listing_groups[language]
      for (const field of Object.keys(fieldLabels)) {
        await page.locator(used('listing_input', { language, field })).fill(String(listing[field] || ''))
      }
    }
    await screenshot(page, screenshotDir, 8, 'fill-listing-copy', steps)

    const warnings = await page.locator(used('warnings_panel')).textContent()
    if (warnings && warnings.trim()) {
      throw new Error(`Dry-run warning detected: ${warnings.trim()}`)
    }
    await screenshot(page, screenshotDir, 9, 'check-no-warnings', steps)

    const saveDraft = page.locator(used('save_draft_button'))
    const saveText = await saveDraft.textContent()
    if (!isSafeAction(saveText, safeLabels, dangerousLabels)) {
      throw new Error(`Save draft selector resolved to unsafe label: ${saveText}`)
    }
    await page.locator('[data-amazon-draft-field="dry-run-status"]').evaluate((node) => {
      node.textContent = 'DRY RUN COMPLETE - Save Draft was identified but not clicked.'
    })
    await screenshot(page, screenshotDir, 10, 'stop-before-save-draft', steps)

    console.log(JSON.stringify({
      job_id: jobId,
      mode: 'playwright_dry_run_local_mock',
      status: 'AMAZON_DRAFT_DRY_RUN_COMPLETED',
      browser_profile: profileDir,
      touch_amazon: false,
      save_draft_clicked: false,
      publish_allowed: false,
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
