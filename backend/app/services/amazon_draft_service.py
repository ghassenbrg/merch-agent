from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.core.paths import DATA_DIR, REPO_ROOT
from app.db.database import get_connection
from app.db.repositories import (
    insert_amazon_draft_attempt,
    insert_draft_event,
    upsert_draft_projection,
)
from app.models.schemas import AmazonDraftRequest, Draft, JobResponse
from app.services.config_service import get_config
from app.services.draft_service import require_draft


DANGEROUS_TEXT = [
    "publish",
    "submit",
    "submit for review",
    "make live",
    "update live listing",
    "create product",
]

SAFE_TEXT = [
    "save draft",
    "save as draft",
]


def _normalize_action(label: str) -> str:
    return " ".join(label.strip().lower().split())


def is_dangerous_action(label: str) -> bool:
    normalized = _normalize_action(label)
    return any(term in normalized for term in DANGEROUS_TEXT)


def is_safe_action(label: str) -> bool:
    normalized = _normalize_action(label)
    if is_dangerous_action(normalized):
        return False
    return any(term in normalized for term in SAFE_TEXT)


def _amazon_ui_contract() -> dict:
    payload = get_config().amazon_upload_ui.get("amazon_upload_ui", {})
    selector_map = payload.get("selector_map", {})
    required_selectors = [
        "upload_input",
        "upload_status",
        "product_type_select",
        "marketplace_checkbox",
        "price_input",
        "translation_own_radio",
        "language_section_toggle",
        "listing_input",
        "warnings_panel",
        "save_draft_button",
    ]
    missing = [selector for selector in required_selectors if not selector_map.get(selector)]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Amazon upload selector map is missing: {', '.join(missing)}",
        )
    return payload


def _selected_product(draft: Draft) -> dict:
    return next((product for product in draft.products if product.get("selected")), draft.products[0])


def _selected_products(draft: Draft) -> list[dict]:
    return [product for product in draft.products if product.get("selected")]


def _selected_marketplaces(draft: Draft) -> list[dict]:
    return [marketplace for marketplace in draft.marketplaces if marketplace.get("selected")]


def _validate_ready_for_amazon_assist(draft: Draft) -> None:
    if draft.status != "READY_FOR_AMAZON_DRAFT":
        raise HTTPException(status_code=400, detail="Draft is not ready for Amazon.")
    if draft.amazon_draft.get("saved"):
        raise HTTPException(status_code=400, detail="Draft already saved to Amazon.")
    if draft.amazon_draft.get("publish_allowed") is not False:
        raise HTTPException(status_code=400, detail="Publish must remain disabled.")
    if draft.amazon_draft.get("locked"):
        raise HTTPException(status_code=409, detail="Amazon Draft Assist is already running for this draft.")
    if not _selected_marketplaces(draft):
        raise HTTPException(status_code=400, detail="At least one marketplace must be selected.")
    if len(_selected_products(draft)) != 1:
        raise HTTPException(status_code=400, detail="Amazon Draft Assist requires exactly one selected product.")
    if not draft.price.get("royalty_positive"):
        raise HTTPException(status_code=400, detail="Royalty must be positive before Amazon Draft Assist.")


def _validate_live_request(request: AmazonDraftRequest) -> None:
    missing: list[str] = []
    if not request.manual_ui_triggered:
        missing.append("manual_ui_triggered")
    if not request.save_draft_only_confirmed:
        missing.append("save_draft_only_confirmed")
    if not request.visible_browser_confirmed:
        missing.append("visible_browser_confirmed")
    if not request.phase8_safety_confirmed:
        missing.append("phase8_safety_confirmed")
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Controlled live save requires explicit UI confirmations: {', '.join(missing)}.",
        )


def _relative_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _configured_runtime_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "data":
        return DATA_DIR.joinpath(*path.parts[1:])
    return REPO_ROOT / path


def _lock_draft_for_amazon_assist(draft: Draft, job_id: str, mode: str) -> None:
    previous_status = draft.status
    draft.status = "AMAZON_DRAFT_IN_PROGRESS"
    draft.amazon_draft["locked"] = True
    draft.amazon_draft["lock_job_id"] = job_id
    draft.amazon_draft["lock_started_at"] = datetime.now(UTC).isoformat()
    draft.amazon_draft["saved"] = False

    with get_connection() as connection:
        upsert_draft_projection(connection, draft)
        insert_draft_event(
            connection,
            draft.draft_id,
            "amazon_draft_dry_run_started" if mode == "dry_run" else "amazon_draft_live_save_started",
            "Amazon Draft Assist dry run locked the draft locally."
            if mode == "dry_run"
            else "Controlled live Amazon Draft Assist locked the draft before browser save.",
            previous_status,
            draft.status,
            {"job_id": job_id, "touch_amazon": mode != "dry_run", "mode": mode},
        )


def _complete_dry_run(draft: Draft, job_id: str, report: dict) -> None:
    previous_status = draft.status
    screenshot_paths = [
        _relative_path(step["screenshot"])
        for step in report.get("screenshots", [])
    ]
    draft.status = "READY_FOR_AMAZON_DRAFT"
    draft.amazon_draft["locked"] = False
    draft.amazon_draft["lock_job_id"] = None
    draft.amazon_draft["last_job_id"] = job_id
    draft.amazon_draft["saved"] = False
    draft.amazon_draft["last_dry_run"] = {
        "job_id": job_id,
        "mode": report["mode"],
        "status": report["status"],
        "completed_at": datetime.now(UTC).isoformat(),
        "browser_profile": _relative_path(report["browser_profile"]),
        "screenshots": screenshot_paths,
        "touch_amazon": False,
        "save_draft_clicked": False,
        "publish_allowed": False,
    }

    with get_connection() as connection:
        upsert_draft_projection(connection, draft)
        insert_amazon_draft_attempt(
            connection,
            draft.draft_id,
            job_id,
            "playwright_dry_run",
            "AMAZON_DRAFT_DRY_RUN_COMPLETED",
            "Playwright dry run completed on a local mock page; no Amazon draft was saved.",
            report,
        )
        insert_draft_event(
            connection,
            draft.draft_id,
            "amazon_draft_dry_run_completed",
            "Amazon Draft Assist dry run completed; Save Draft was not clicked.",
            previous_status,
            draft.status,
            {
                "job_id": job_id,
                "touch_amazon": False,
                "screenshot_count": len(screenshot_paths),
            },
        )


def _fail_dry_run(draft: Draft, job_id: str, message: str) -> None:
    previous_status = draft.status
    draft.status = "AMAZON_DRAFT_FAILED"
    draft.amazon_draft["locked"] = False
    draft.amazon_draft["lock_job_id"] = None
    draft.amazon_draft["saved"] = False
    draft.amazon_draft["eligible"] = False
    draft.amazon_draft["last_dry_run"] = {
        "job_id": job_id,
        "status": "AMAZON_DRAFT_DRY_RUN_FAILED",
        "message": message,
        "touch_amazon": False,
        "save_draft_clicked": False,
    }

    with get_connection() as connection:
        upsert_draft_projection(connection, draft)
        insert_amazon_draft_attempt(
            connection,
            draft.draft_id,
            job_id,
            "playwright_dry_run",
            "AMAZON_DRAFT_DRY_RUN_FAILED",
            message,
            {"touch_amazon": False, "error": message},
        )
        insert_draft_event(
            connection,
            draft.draft_id,
            "amazon_draft_dry_run_failed",
            message,
            previous_status,
            draft.status,
            {"job_id": job_id, "touch_amazon": False},
        )


def _live_screenshot_paths(report: dict) -> list[str]:
    return [
        _relative_path(step["screenshot"])
        for step in report.get("screenshots", [])
        if step.get("screenshot")
    ]


def _validate_live_report(report: dict) -> None:
    if report.get("touch_amazon") is not True:
        raise RuntimeError("Live save report did not confirm Amazon interaction.")
    if report.get("save_draft_clicked") is not True:
        raise RuntimeError("Live save report did not confirm Save Draft was clicked.")
    if report.get("publish_allowed") is not False:
        raise RuntimeError("Live save report violated publish safety boundaries.")
    if report.get("visible_browser") is not True or report.get("headless") is not False:
        raise RuntimeError("Live save must run in a visible controlled browser session.")
    step_names = {step.get("step") for step in report.get("screenshots", [])}
    if "before-save-draft" not in step_names or "after-save-draft" not in step_names:
        raise RuntimeError("Live save report must include before and after Save Draft screenshots.")


def _complete_live_save(draft: Draft, job_id: str, report: dict) -> None:
    _validate_live_report(report)
    previous_status = draft.status
    screenshot_paths = _live_screenshot_paths(report)
    draft.status = "AMAZON_DRAFT_SAVED"
    draft.amazon_draft["locked"] = False
    draft.amazon_draft["lock_job_id"] = None
    draft.amazon_draft["last_job_id"] = job_id
    draft.amazon_draft["eligible"] = False
    draft.amazon_draft["saved"] = True
    draft.amazon_draft["saved_at"] = datetime.now(UTC).isoformat()
    draft.amazon_draft["last_live_save"] = {
        "job_id": job_id,
        "mode": report["mode"],
        "status": report["status"],
        "completed_at": datetime.now(UTC).isoformat(),
        "browser_profile": _relative_path(report["browser_profile"]),
        "screenshots": screenshot_paths,
        "touch_amazon": True,
        "save_draft_clicked": True,
        "publish_allowed": False,
        "selected_product": report.get("selected_product"),
        "selected_marketplaces": report.get("selected_marketplaces", []),
    }

    with get_connection() as connection:
        upsert_draft_projection(connection, draft)
        insert_amazon_draft_attempt(
            connection,
            draft.draft_id,
            job_id,
            "controlled_live_save",
            "AMAZON_DRAFT_SAVED",
            "Controlled live Amazon draft save completed with Save Draft only.",
            report,
        )
        insert_draft_event(
            connection,
            draft.draft_id,
            "amazon_draft_live_save_completed",
            "Controlled live Amazon draft save completed; draft was saved only.",
            previous_status,
            draft.status,
            {
                "job_id": job_id,
                "touch_amazon": True,
                "screenshot_count": len(screenshot_paths),
            },
        )


def _fail_live_save(draft: Draft, job_id: str, message: str, report: dict | None = None) -> None:
    previous_status = draft.status
    screenshot_paths = _live_screenshot_paths(report or {})
    draft.status = "AMAZON_DRAFT_FAILED"
    draft.amazon_draft["locked"] = False
    draft.amazon_draft["lock_job_id"] = None
    draft.amazon_draft["saved"] = False
    draft.amazon_draft["eligible"] = False
    draft.amazon_draft["last_live_save"] = {
        "job_id": job_id,
        "status": "AMAZON_DRAFT_FAILED",
        "message": message,
        "touch_amazon": True,
        "save_draft_clicked": bool((report or {}).get("save_draft_clicked")),
        "publish_allowed": False,
        "screenshots": screenshot_paths,
    }

    with get_connection() as connection:
        upsert_draft_projection(connection, draft)
        insert_amazon_draft_attempt(
            connection,
            draft.draft_id,
            job_id,
            "controlled_live_save",
            "AMAZON_DRAFT_FAILED",
            message,
            report or {"touch_amazon": True, "error": message},
        )
        insert_draft_event(
            connection,
            draft.draft_id,
            "amazon_draft_live_save_failed",
            message,
            previous_status,
            draft.status,
            {
                "job_id": job_id,
                "touch_amazon": True,
                "screenshot_count": len(screenshot_paths),
            },
        )


def _run_playwright_dry_run(draft: Draft, job_id: str, ui_contract: dict) -> dict:
    dry_run = ui_contract.get("dry_run", {})
    profile_dir = _configured_runtime_path(dry_run.get(
        "controlled_profile_dir",
        "data/browser-profiles/amazon-draft-dry-run",
    ))
    screenshot_root = _configured_runtime_path(dry_run.get(
        "screenshot_dir",
        "data/screenshots/amazon-draft-dry-run",
    ))
    screenshot_dir = screenshot_root / draft.draft_id / job_id
    input_path = DATA_DIR / "logs" / f"amazon_draft_dry_run_{job_id}.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "job_id": job_id,
        "draft": draft.model_dump(mode="json"),
        "profile_dir": str(profile_dir),
        "screenshot_dir": str(screenshot_dir),
        "selector_map": ui_contract["selector_map"],
        "dangerous_action_labels": ui_contract.get("dangerous_action_labels", DANGEROUS_TEXT),
        "safe_action_labels": ui_contract.get("safe_action_labels", SAFE_TEXT),
    }
    input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    script = REPO_ROOT / "agent" / "merch_agent" / "browser" / "amazon_draft_dry_run.mjs"
    completed = subprocess.run(
        ["node", str(script), "--input", str(input_path)],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=45,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "Playwright dry run failed."
        raise RuntimeError(detail)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("Playwright dry run did not return a report.")
    report = json.loads(lines[-1])
    if report.get("touch_amazon") is not False or report.get("save_draft_clicked") is not False:
        raise RuntimeError("Dry-run report violated Amazon safety boundaries.")
    return report


def _run_playwright_live_save(draft: Draft, job_id: str, ui_contract: dict) -> dict:
    live = ui_contract.get("live", {})
    create_product_url = live.get("create_product_url")
    if not create_product_url:
        raise RuntimeError("Amazon live create-product URL is not configured.")
    profile_dir = _configured_runtime_path(live.get(
        "controlled_profile_dir",
        "data/browser-profiles/amazon-draft-live",
    ))
    screenshot_root = _configured_runtime_path(live.get(
        "screenshot_dir",
        "data/screenshots/amazon-draft-live",
    ))
    screenshot_dir = screenshot_root / draft.draft_id / job_id
    input_path = DATA_DIR / "logs" / f"amazon_draft_live_save_{job_id}.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "job_id": job_id,
        "draft": draft.model_dump(mode="json"),
        "profile_dir": str(profile_dir),
        "screenshot_dir": str(screenshot_dir),
        "create_product_url": create_product_url,
        "selector_map": live.get("selector_map", ui_contract["selector_map"]),
        "dangerous_action_labels": ui_contract.get("dangerous_action_labels", DANGEROUS_TEXT),
        "safe_action_labels": ui_contract.get("safe_action_labels", SAFE_TEXT),
    }
    input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    script = REPO_ROOT / "agent" / "merch_agent" / "browser" / "amazon_draft_live_save.mjs"
    completed = subprocess.run(
        ["node", str(script), "--input", str(input_path)],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=300,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "Playwright live save failed."
        raise RuntimeError(detail)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("Playwright live save did not return a report.")
    report = json.loads(lines[-1])
    _validate_live_report(report)
    return report


def start_amazon_draft(draft_id: str, request: AmazonDraftRequest | None = None) -> JobResponse:
    request = request or AmazonDraftRequest()
    draft = require_draft(draft_id)
    _validate_ready_for_amazon_assist(draft)
    if request.mode == "controlled_live_save":
        _validate_live_request(request)
    ui_contract = _amazon_ui_contract()

    job_id = f"job_{uuid4().hex[:12]}"
    _lock_draft_for_amazon_assist(draft, job_id, request.mode)

    if request.mode == "dry_run":
        try:
            report = _run_playwright_dry_run(draft, job_id, ui_contract)
        except Exception as error:
            _fail_dry_run(draft, job_id, str(error))
            raise HTTPException(status_code=500, detail=f"Amazon Draft Assist dry run failed: {error}") from error

        _complete_dry_run(draft, job_id, report)
        return JobResponse(
            jobId=job_id,
            status="AMAZON_DRAFT_DRY_RUN_COMPLETED",
            message="Amazon Draft Assist dry run completed locally. No Amazon draft was saved.",
        )

    try:
        report = _run_playwright_live_save(draft, job_id, ui_contract)
        _complete_live_save(draft, job_id, report)
    except Exception as error:
        _fail_live_save(draft, job_id, str(error))
        raise HTTPException(status_code=500, detail=f"Controlled live Amazon draft save failed: {error}") from error

    return JobResponse(
        jobId=job_id,
        status="AMAZON_DRAFT_SAVED",
        message="Controlled live Amazon draft save completed. Save Draft was clicked; no publish action was used.",
    )
