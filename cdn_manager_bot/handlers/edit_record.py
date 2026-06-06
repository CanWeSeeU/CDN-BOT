from __future__ import annotations

import logging
from typing import Any

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from cloudflare_api import CloudflareAPI, CloudflareAPIError
from keyboards.inline import (
    back_to_menu_keyboard,
    edit_field_keyboard,
    proxied_keyboard,
    record_detail_keyboard,
    ttl_keyboard,
)
from utils.decorators import admin_only
from utils.helpers import fmt_record_detail, fmt_ttl
from utils.validators import (
    is_valid_dns_name,
    is_valid_ttl,
    validate_record_content,
)

logger = logging.getLogger(__name__)

_PROXIABLE = {"A", "AAAA", "CNAME"}


@admin_only
async def edit_record_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:

    query = update.callback_query
    assert query is not None
    await query.answer()

    parts = query.data.split(":")
    record_id = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0

    user_id = update.effective_user.id  
    db = context.bot_data["db"]
    zone = await db.get_selected_zone(user_id)

    if zone is None:
        await query.edit_message_text("⚠️ No zone selected. Use /start to pick one.")
        return

    try:
        async with CloudflareAPI() as cf:
            record = await cf.get_dns_record(zone["zone_id"], record_id)
    except CloudflareAPIError as exc:
        logger.error("CF error fetching record for edit: %s", exc)
        await query.edit_message_text(f"❌ Cloudflare error:\n<code>{exc}</code>", parse_mode="HTML")
        return
    except httpx.HTTPError as exc:
        logger.error("Network error fetching record for edit: %s", exc)
        await query.edit_message_text("❌ Network error. Please try again.")
        return
    state: dict[str, Any] = {
        "record": record,
        "record_id": record_id,
        "page": page,
        "step": "choose_field",
    }
    await db.set_state(user_id, "edit", state)

    detail = fmt_record_detail(record)
    await query.edit_message_text(
        f"✏ <b>Edit Record</b>\n\n{detail}\n\n<b>Choose a field to edit:</b>",
        reply_markup=edit_field_keyboard(record_id, page),
        parse_mode="HTML",
    )



@admin_only
async def edit_field_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    parts = query.data.split(":")
    field = parts[2]
    record_id = parts[3]
    page = int(parts[4]) if len(parts) > 4 else 0

    user_id = update.effective_user.id  # type: ignore[union-attr]
    db = context.bot_data["db"]
    state_row = await db.get_state(user_id)

    if state_row is None or state_row[0] != "edit":
        await query.edit_message_text("⚠️ Session expired. Please start over.")
        return

    state = state_row[1]
    state["editing_field"] = field
    state["step"] = f"edit_{field}"
    await db.set_state(user_id, "edit", state)

    record = state.get("record", {})

    if field == "ttl":
        current_ttl = fmt_ttl(record.get("ttl", 1))
        await query.edit_message_text(
            f"Choose new <b>TTL</b> (current: {current_ttl}):",
            reply_markup=ttl_keyboard(f"edit:ttl"),
            parse_mode="HTML",
        )
    elif field == "proxied":
        rtype = record.get("type", "A")
        if rtype not in _PROXIABLE:
            await query.answer(
                "⚠️ Proxied is only available for A, AAAA, CNAME records.",
                show_alert=True,
            )
            return
        current = "Proxied" if record.get("proxied") else "DNS Only"
        await query.edit_message_text(
            f"Choose new <b>proxy status</b> (current: {current}):",
            reply_markup=proxied_keyboard("edit:proxied"),
            parse_mode="HTML",
        )
    elif field == "name":
        current_name = record.get("name", "")
        await query.edit_message_text(
            f"Enter new <b>name</b> (current: <code>{current_name}</code>):",
            parse_mode="HTML",
        )
    elif field == "content":
        current_content = record.get("content", "")
        await query.edit_message_text(
            f"Enter new <b>content</b> (current: <code>{current_content}</code>):",
            parse_mode="HTML",
        )



@admin_only
async def edit_ttl_chosen_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    ttl_val = int(query.data.split(":")[2])
    user_id = update.effective_user.id 
    db = context.bot_data["db"]
    state_row = await db.get_state(user_id)

    if state_row is None or state_row[0] != "edit":
        return

    state = state_row[1]
    state["record"]["ttl"] = ttl_val
    state["step"] = "choose_field"
    await db.set_state(user_id, "edit", state)
    await _submit_edit(query, db, user_id, state, context)


@admin_only
async def edit_proxied_chosen_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    proxied = query.data.split(":")[2] == "true"
    user_id = update.effective_user.id  
    db = context.bot_data["db"]
    state_row = await db.get_state(user_id)

    if state_row is None or state_row[0] != "edit":
        return

    state = state_row[1]
    state["record"]["proxied"] = proxied
    state["step"] = "choose_field"
    await db.set_state(user_id, "edit", state)
    await _submit_edit(query, db, user_id, state, context)


@admin_only
async def edit_text_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.message
    assert message is not None
    user_id = update.effective_user.id 
    db = context.bot_data["db"]
    text = (message.text or "").strip()

    state_row = await db.get_state(user_id)
    if state_row is None or state_row[0] != "edit":
        return

    state = state_row[1]
    step = state.get("step", "")
    record = state.get("record", {})
    rtype = record.get("type", "A")

    if step == "edit_name":
        if not is_valid_dns_name(text):
            await message.reply_text(
                "❌ Invalid DNS name. Example: <code>api.example.com</code> or <code>@</code>.",
                parse_mode="HTML",
            )
            return
        state["record"]["name"] = text
        state["step"] = "choose_field"
        await db.set_state(user_id, "edit", state)
        await _submit_edit_message(message, db, user_id, state, context)

    elif step == "edit_content":
        valid, err = validate_record_content(rtype, text)
        if not valid:
            await message.reply_text(err, parse_mode="HTML")
            return
        state["record"]["content"] = text
        state["step"] = "choose_field"
        await db.set_state(user_id, "edit", state)
        await _submit_edit_message(message, db, user_id, state, context)

async def _submit_edit(
    query: Any,
    db: Any,
    user_id: int,
    state: dict,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    zone = await db.get_selected_zone(user_id)
    if zone is None:
        await query.edit_message_text("⚠️ No zone selected. Use /start.")
        return

    record = state["record"]
    record_id = state["record_id"]
    page = state.get("page", 0)

    payload = {
        "type": record["type"],
        "name": record["name"],
        "content": record.get("content", ""),
        "ttl": record.get("ttl", 1),
    }
    if record.get("type") in _PROXIABLE:
        payload["proxied"] = record.get("proxied", False)
    if record.get("type") == "MX":
        payload["priority"] = record.get("priority", 10)

    await query.edit_message_text("⏳ Updating record…")

    try:
        async with CloudflareAPI() as cf:
            updated = await cf.update_dns_record(zone["zone_id"], record_id, payload)
    except CloudflareAPIError as exc:
        logger.error("CF error updating record: %s", exc)
        await query.edit_message_text(
            f"❌ Cloudflare error:\n<code>{exc}</code>",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    except httpx.HTTPError as exc:
        logger.error("Network error updating record: %s", exc)
        await query.edit_message_text(
            "❌ Network error. Please try again.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    await db.clear_state(user_id)
    await db.invalidate_dns_cache(zone["zone_id"])

    logger.info("User %s updated record %s in zone %s", user_id, record_id, zone["zone_id"])

    detail = fmt_record_detail(updated)
    await query.edit_message_text(
        f"✅ <b>Record updated!</b>\n\n{detail}",
        reply_markup=record_detail_keyboard(record_id, page),
        parse_mode="HTML",
    )


async def _submit_edit_message(
    message: Any,
    db: Any,
    user_id: int,
    state: dict,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    zone = await db.get_selected_zone(user_id)
    if zone is None:
        await message.reply_text("⚠️ No zone selected. Use /start.")
        return

    record = state["record"]
    record_id = state["record_id"]
    page = state.get("page", 0)

    payload = {
        "type": record["type"],
        "name": record["name"],
        "content": record.get("content", ""),
        "ttl": record.get("ttl", 1),
    }
    if record.get("type") in _PROXIABLE:
        payload["proxied"] = record.get("proxied", False)
    if record.get("type") == "MX":
        payload["priority"] = record.get("priority", 10)

    await message.reply_text("⏳ Updating record…")

    try:
        async with CloudflareAPI() as cf:
            updated = await cf.update_dns_record(zone["zone_id"], record_id, payload)
    except CloudflareAPIError as exc:
        logger.error("CF error updating record: %s", exc)
        await message.reply_text(
            f"❌ Cloudflare error:\n<code>{exc}</code>",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    except httpx.HTTPError as exc:
        logger.error("Network error updating record: %s", exc)
        await message.reply_text(
            "❌ Network error. Please try again.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    await db.clear_state(user_id)
    await db.invalidate_dns_cache(zone["zone_id"])

    logger.info("User %s updated record %s in zone %s", user_id, record_id, zone["zone_id"])

    detail = fmt_record_detail(updated)
    await message.reply_text(
        f"✅ <b>Record updated!</b>\n\n{detail}",
        reply_markup=record_detail_keyboard(record_id, page),
        parse_mode="HTML",
    )
