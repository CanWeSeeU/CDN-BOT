from __future__ import annotations

import logging

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from cdn_dns_manager_bot.cloudflare_api import CloudflareAPI, CloudflareAPIError
from cdn_dns_manager_bot.keyboards.inline import dns_list_keyboard, record_detail_keyboard
from cdn_dns_manager_bot.utils.decorators import admin_only
from cdn_dns_manager_bot.utils.helpers import fmt_record_detail

logger = logging.getLogger(__name__)


async def _fetch_records(
    context: ContextTypes.DEFAULT_TYPE,
    zone_id: str,
    force_refresh: bool = False,
) -> list[dict]:
    db = context.bot_data["db"]

    if not force_refresh:
        cached = await db.get_cached_dns_records(zone_id)
        if cached is not None:
            logger.debug("DNS records for zone %s served from cache", zone_id)
            return cached

    async with CloudflareAPI() as cf:
        records = await cf.get_dns_records(zone_id)

    await db.cache_dns_records(zone_id, records)
    return records


@admin_only
async def dns_list_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    parts = query.data.split(":")
    page = int(parts[2]) if len(parts) > 2 else 0

    user_id = update.effective_user.id 
    db = context.bot_data["db"]
    zone = await db.get_selected_zone(user_id)

    if zone is None:
        await query.edit_message_text("⚠️ No zone selected. Use /start to pick one.")
        return

    await query.edit_message_text("⏳ Loading DNS records…")

    try:
        records = await _fetch_records(context, zone["zone_id"])
    except CloudflareAPIError as exc:
        logger.error("CF error fetching records: %s", exc)
        await query.edit_message_text(f"❌ Cloudflare error:\n<code>{exc}</code>", parse_mode="HTML")
        return
    except httpx.HTTPError as exc:
        logger.error("Network error fetching records: %s", exc)
        await query.edit_message_text("❌ Network error. Please try again.")
        return

    if not records:
        from cdn_dns_manager_bot.keyboards.inline import back_to_menu_keyboard
        await query.edit_message_text(
            f"📭 No DNS records found in <b>{zone['zone_name']}</b>.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    total = len(records)
    await query.edit_message_text(
        f"📋 <b>{zone['zone_name']}</b> — {total} record{'s' if total != 1 else ''}\n"
        "Select a record to view details:",
        reply_markup=dns_list_keyboard(records, page),
        parse_mode="HTML",
    )


@admin_only
async def dns_refresh_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer("🔄 Refreshing…")

    user_id = update.effective_user.id 
    db = context.bot_data["db"]
    zone = await db.get_selected_zone(user_id)

    if zone is None:
        await query.edit_message_text("⚠️ No zone selected. Use /start to pick one.")
        return

    await db.invalidate_dns_cache(zone["zone_id"])

    try:
        records = await _fetch_records(context, zone["zone_id"], force_refresh=True)
    except CloudflareAPIError as exc:
        logger.error("CF error on refresh: %s", exc)
        await query.edit_message_text(f"❌ Cloudflare error:\n<code>{exc}</code>", parse_mode="HTML")
        return
    except httpx.HTTPError as exc:
        logger.error("Network error on refresh: %s", exc)
        await query.edit_message_text("❌ Network error. Please try again.")
        return

    total = len(records)
    await query.edit_message_text(
        f"✅ Refreshed!  Found {total} record{'s' if total != 1 else ''}.\n\n"
        f"📋 <b>{zone['zone_name']}</b>\n"
        "Select a record to view details:",
        reply_markup=dns_list_keyboard(records, 0),
        parse_mode="HTML",
    )


@admin_only
async def record_view_handler(
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
        logger.error("CF error fetching record %s: %s", record_id, exc)
        await query.edit_message_text(f"❌ Cloudflare error:\n<code>{exc}</code>", parse_mode="HTML")
        return
    except httpx.HTTPError as exc:
        logger.error("Network error fetching record %s: %s", record_id, exc)
        await query.edit_message_text("❌ Network error. Please try again.")
        return

    text = fmt_record_detail(record)
    await query.edit_message_text(
        text,
        reply_markup=record_detail_keyboard(record_id, page),
        parse_mode="HTML",
    )
