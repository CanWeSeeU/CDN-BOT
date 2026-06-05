from __future__ import annotations

import logging
from typing import Any

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from cdn_dns_manager_bot.cloudflare_api import CloudflareAPI, CloudflareAPIError
from cdn_dns_manager_bot.keyboards.inline import (
    back_to_menu_keyboard,
    confirm_create_keyboard,
    proxied_keyboard,
    record_type_keyboard,
    ttl_keyboard,
)
from cdn_dns_manager_bot.utils.decorators import admin_only
from cdn_dns_manager_bot.utils.helpers import fmt_ttl
from cdn_dns_manager_bot.utils.validators import (
    is_valid_dns_name,
    is_valid_priority,
    is_valid_srv_port,
    is_valid_srv_weight,
    is_valid_ttl,
    parse_ttl,
    validate_record_content,
)

logger = logging.getLogger(__name__)

_PROXIABLE = {"A", "AAAA", "CNAME"}

_SRV_FIELDS = ["service", "proto", "priority", "weight", "port", "target"]
_SRV_PROMPTS = {
    "service": "Enter the SRV <b>service</b> name (e.g. <code>_sip</code>):",
    "proto": "Enter the SRV <b>protocol</b> (e.g. <code>_tcp</code> or <code>_udp</code>):",
    "priority": "Enter the SRV <b>priority</b> (0–65535):",
    "weight": "Enter the SRV <b>weight</b> (0–65535):",
    "port": "Enter the SRV <b>port</b> (0–65535):",
    "target": "Enter the SRV <b>target hostname</b>:",
}


def _build_summary(data: dict[str, Any]) -> str:
    rtype = data["type"]
    ttl_str = fmt_ttl(data["ttl"])
    proxied = data.get("proxied", False)
    proxied_str = "✅ Proxied" if proxied else "⚪ DNS Only"

    lines = [
        "📝 <b>Record Summary</b>",
        "",
        f"<b>Type:</b>    {rtype}",
        f"<b>Name:</b>    <code>{data['name']}</code>",
    ]

    if rtype == "SRV":
        srv = data["srv"]
        lines.append(f"<b>Service:</b>  {srv['service']}")
        lines.append(f"<b>Proto:</b>    {srv['proto']}")
        lines.append(f"<b>Priority:</b> {srv['priority']}")
        lines.append(f"<b>Weight:</b>   {srv['weight']}")
        lines.append(f"<b>Port:</b>     {srv['port']}")
        lines.append(f"<b>Target:</b>   <code>{srv['target']}</code>")
    else:
        lines.append(f"<b>Content:</b> <code>{data['content']}</code>")
        if rtype == "MX":
            lines.append(f"<b>Priority:</b> {data.get('priority', 10)}")

    lines.append(f"<b>TTL:</b>     {ttl_str}")
    if rtype in _PROXIABLE:
        lines.append(f"<b>Proxied:</b> {proxied_str}")

    lines.append("")
    lines.append("Confirm to create this record?")
    return "\n".join(lines)


def _build_cf_payload(data: dict[str, Any]) -> dict:
    """Convert wizard data dict into a Cloudflare API payload."""
    rtype = data["type"]
    payload: dict[str, Any] = {
        "type": rtype,
        "name": data["name"],
        "ttl": data["ttl"],
    }
    if rtype == "SRV":
        srv = data["srv"]
        payload["data"] = {
            "service": srv["service"],
            "proto": srv["proto"],
            "priority": int(srv["priority"]),
            "weight": int(srv["weight"]),
            "port": int(srv["port"]),
            "target": srv["target"],
        }
    else:
        payload["content"] = data["content"]
        if rtype == "MX":
            payload["priority"] = int(data.get("priority", 10))
        if rtype in _PROXIABLE:
            payload["proxied"] = data.get("proxied", False)
    return payload


@admin_only
async def add_record_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle ``dns:add`` callback — show record type selector."""
    query = update.callback_query
    assert query is not None
    await query.answer()

    user_id = update.effective_user.id  # type: ignore[union-attr]
    db = context.bot_data["db"]
    await db.clear_state(user_id)

    await query.edit_message_text(
        "➕ <b>Create DNS Record</b>\n\nStep 1: Choose record type:",
        reply_markup=record_type_keyboard(),
        parse_mode="HTML",
    )


@admin_only
async def type_chosen_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle ``create:type:<TYPE>`` callback."""
    query = update.callback_query
    assert query is not None
    await query.answer()

    rtype = query.data.split(":")[2].upper()
    user_id = update.effective_user.id  # type: ignore[union-attr]
    db = context.bot_data["db"]

    state: dict[str, Any] = {"step": "name", "type": rtype}
    await db.set_state(user_id, "create", state)

    await query.edit_message_text(
        f"➕ <b>Create {rtype} Record</b>\n\n"
        "Step 2: Enter the record <b>name</b>.\n"
        "Use <code>@</code> for the zone apex, or a subdomain like <code>api</code>.",
        parse_mode="HTML",
    )


@admin_only
async def create_text_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Route incoming text messages during the create wizard.

    This handler is registered as a MessageHandler and only fires when
    user state key is ``"create"``.
    """
    message = update.message
    assert message is not None
    user_id = update.effective_user.id  # type: ignore[union-attr]
    db = context.bot_data["db"]
    text = (message.text or "").strip()

    state_row = await db.get_state(user_id)
    if state_row is None or state_row[0] != "create":
        return  # Not in create wizard

    state = state_row[1]
    step = state.get("step")
    rtype = state.get("type", "A")

    if step == "name":
        await _handle_name_input(message, db, user_id, text, state, rtype)
    elif step == "content":
        await _handle_content_input(message, db, user_id, text, state, rtype)
    elif step == "mx_priority":
        await _handle_mx_priority(message, db, user_id, text, state)
    elif step == "srv":
        await _handle_srv_field(message, db, user_id, text, state)


async def _handle_name_input(
    message: Any,
    db: Any,
    user_id: int,
    text: str,
    state: dict,
    rtype: str,
) -> None:
    if not is_valid_dns_name(text):
        await message.reply_text(
            "❌ Invalid DNS name.  Use letters, digits, hyphens, dots.  "
            "Example: <code>api.example.com</code> or <code>@</code>.",
            parse_mode="HTML",
        )
        return

    state["name"] = text
    if rtype == "SRV":
        state["step"] = "srv"
        state["srv_field_index"] = 0
        state["srv"] = {}
        await db.set_state(user_id, "create", state)
        field = _SRV_FIELDS[0]
        await message.reply_text(_SRV_PROMPTS[field], parse_mode="HTML")
    else:
        state["step"] = "content"
        await db.set_state(user_id, "create", state)
        await message.reply_text(
            f"Step 3: Enter the record <b>content</b> (value) for your {rtype} record:",
            parse_mode="HTML",
        )


async def _handle_content_input(
    message: Any,
    db: Any,
    user_id: int,
    text: str,
    state: dict,
    rtype: str,
) -> None:
    valid, err = validate_record_content(rtype, text)
    if not valid:
        await message.reply_text(err, parse_mode="HTML")
        return

    state["content"] = text

    if rtype == "MX":
        state["step"] = "mx_priority"
        await db.set_state(user_id, "create", state)
        await message.reply_text(
            "Step 3b: Enter the <b>MX priority</b> (0–65535), e.g. <code>10</code>:",
            parse_mode="HTML",
        )
        return

    state["step"] = "ttl"
    await db.set_state(user_id, "create", state)
    await message.reply_text(
        "Step 4: Choose <b>TTL</b>:",
        reply_markup=ttl_keyboard("create:ttl"),
        parse_mode="HTML",
    )


async def _handle_mx_priority(
    message: Any,
    db: Any,
    user_id: int,
    text: str,
    state: dict,
) -> None:
    if not is_valid_priority(text):
        await message.reply_text("❌ Priority must be an integer between 0 and 65535.")
        return

    state["priority"] = int(text)
    state["step"] = "ttl"
    await db.set_state(user_id, "create", state)
    await message.reply_text(
        "Step 4: Choose <b>TTL</b>:",
        reply_markup=ttl_keyboard("create:ttl"),
        parse_mode="HTML",
    )


async def _handle_srv_field(
    message: Any,
    db: Any,
    user_id: int,
    text: str,
    state: dict,
) -> None:
    idx: int = state.get("srv_field_index", 0)
    field = _SRV_FIELDS[idx]

    error: str | None = None
    if field == "priority":
        if not is_valid_priority(text):
            error = "❌ Priority must be 0–65535."
    elif field == "weight":
        if not is_valid_srv_weight(text):
            error = "❌ Weight must be 0–65535."
    elif field == "port":
        if not is_valid_srv_port(text):
            error = "❌ Port must be 0–65535."
    elif field == "target":
        if not is_valid_dns_name(text.rstrip(".")):
            error = "❌ Invalid target hostname."

    if error:
        await message.reply_text(error)
        return

    state["srv"][field] = text
    idx += 1

    if idx < len(_SRV_FIELDS):
        state["srv_field_index"] = idx
        await db.set_state(user_id, "create", state)
        next_field = _SRV_FIELDS[idx]
        await message.reply_text(_SRV_PROMPTS[next_field], parse_mode="HTML")
    else:
        state["step"] = "ttl"
        await db.set_state(user_id, "create", state)
        await message.reply_text(
            "Step 4: Choose <b>TTL</b>:",
            reply_markup=ttl_keyboard("create:ttl"),
            parse_mode="HTML",
        )


@admin_only
async def ttl_chosen_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle ``create:ttl:<seconds>``."""
    query = update.callback_query
    assert query is not None
    await query.answer()

    ttl_val = int(query.data.split(":")[2])
    if not is_valid_ttl(str(ttl_val)):
        await query.answer("❌ Invalid TTL value.", show_alert=True)
        return

    user_id = update.effective_user.id  # type: ignore[union-attr]
    db = context.bot_data["db"]
    state_row = await db.get_state(user_id)
    if state_row is None or state_row[0] != "create":
        return

    state = state_row[1]
    state["ttl"] = ttl_val
    rtype = state.get("type", "A")

    if rtype in _PROXIABLE:
        state["step"] = "proxied"
        await db.set_state(user_id, "create", state)
        await query.edit_message_text(
            "Step 5: Choose <b>proxy status</b>:",
            reply_markup=proxied_keyboard("create:proxied"),
            parse_mode="HTML",
        )
    else:
        state["step"] = "confirm"
        await db.set_state(user_id, "create", state)
        await query.edit_message_text(
            _build_summary(state),
            reply_markup=confirm_create_keyboard(),
            parse_mode="HTML",
        )


@admin_only
async def proxied_chosen_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle ``create:proxied:<bool>``."""
    query = update.callback_query
    assert query is not None
    await query.answer()

    proxied = query.data.split(":")[2] == "true"
    user_id = update.effective_user.id  # type: ignore[union-attr]
    db = context.bot_data["db"]
    state_row = await db.get_state(user_id)
    if state_row is None or state_row[0] != "create":
        return

    state = state_row[1]
    state["proxied"] = proxied
    state["step"] = "confirm"
    await db.set_state(user_id, "create", state)

    await query.edit_message_text(
        _build_summary(state),
        reply_markup=confirm_create_keyboard(),
        parse_mode="HTML",
    )


@admin_only
async def confirm_create_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    user_id = update.effective_user.id 
    db = context.bot_data["db"]
    zone = await db.get_selected_zone(user_id)
    state_row = await db.get_state(user_id)

    if zone is None or state_row is None or state_row[0] != "create":
        await query.edit_message_text(
            "⚠️ Session expired. Please start over.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    state = state_row[1]
    payload = _build_cf_payload(state)

    await query.edit_message_text("⏳ Creating DNS record…")

    try:
        async with CloudflareAPI() as cf:
            record = await cf.create_dns_record(zone["zone_id"], payload)
    except CloudflareAPIError as exc:
        logger.error("CF error creating record: %s", exc)
        await query.edit_message_text(
            f"❌ Cloudflare error:\n<code>{exc}</code>",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    except httpx.HTTPError as exc:
        logger.error("Network error creating record: %s", exc)
        await query.edit_message_text(
            "❌ Network error. Please try again.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    await db.clear_state(user_id)
    await db.invalidate_dns_cache(zone["zone_id"])

    logger.info(
        "User %s created %s record %s in zone %s",
        user_id,
        record.get("type"),
        record.get("id"),
        zone["zone_id"],
    )

    await query.edit_message_text(
        f"✅ <b>DNS record created!</b>\n\n"
        f"<b>Type:</b> {record.get('type')}\n"
        f"<b>Name:</b> <code>{record.get('name')}</code>\n"
        f"<b>ID:</b>   <code>{record.get('id')}</code>",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )
