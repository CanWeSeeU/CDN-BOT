from __future__ import annotations

import logging

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from cloudflare_api import CloudflareAPI, CloudflareAPIError
from keyboards.inline import back_to_menu_keyboard, delete_confirm_keyboard, dns_list_keyboard
from utils.decorators import admin_only
from utils.helpers import fmt_record_detail

logger = logging.getLogger(__name__)


@admin_only
async def delete_record_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    parts = query.data.split(":")
    record_id = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0

    user_id = update.effective_user.id  # type: ignore[union-attr]
    db = context.bot_data["db"]
    zone = await db.get_selected_zone(user_id)

    if zone is None:
        await query.edit_message_text("⚠️ No zone selected. Use /start to pick one.")
        return

    try:
        async with CloudflareAPI() as cf:
            record = await cf.get_dns_record(zone["zone_id"], record_id)
    except CloudflareAPIError as exc:
        logger.error("CF error fetching record for deletion: %s", exc)
        await query.edit_message_text(
            f"❌ Cloudflare error:\n<code>{exc}</code>", parse_mode="HTML"
        )
        return
    except httpx.HTTPError as exc:
        logger.error("Network error fetching record for deletion: %s", exc)
        await query.edit_message_text("❌ Network error. Please try again.")
        return

    detail = fmt_record_detail(record)
    await query.edit_message_text(
        f"🗑 <b>Delete Record?</b>\n\n{detail}\n\n"
        "⚠️ <b>Are you sure?</b>  This action cannot be undone.",
        reply_markup=delete_confirm_keyboard(record_id, page),
        parse_mode="HTML",
    )


@admin_only
async def delete_confirm_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    parts = query.data.split(":")
    record_id = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0

    user_id = update.effective_user.id  # type: ignore[union-attr]
    db = context.bot_data["db"]
    zone = await db.get_selected_zone(user_id)

    if zone is None:
        await query.edit_message_text("⚠️ No zone selected. Use /start to pick one.")
        return

    await query.edit_message_text("⏳ Deleting record…")

    try:
        async with CloudflareAPI() as cf:
            await cf.delete_dns_record(zone["zone_id"], record_id)
    except CloudflareAPIError as exc:
        logger.error("CF error deleting record %s: %s", record_id, exc)
        await query.edit_message_text(
            f"❌ Cloudflare error:\n<code>{exc}</code>",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    except httpx.HTTPError as exc:
        logger.error("Network error deleting record %s: %s", record_id, exc)
        await query.edit_message_text(
            "❌ Network error. Please try again.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    await db.invalidate_dns_cache(zone["zone_id"])
    logger.info("User %s deleted record %s from zone %s", user_id, record_id, zone["zone_id"])

    try:
        async with CloudflareAPI() as cf:
            records = await cf.get_dns_records(zone["zone_id"])
        await db.cache_dns_records(zone["zone_id"], records)
        total = len(records)
        await query.edit_message_text(
            f"✅ <b>Record deleted!</b>\n\n"
            f"📋 <b>{zone['zone_name']}</b> — {total} record{'s' if total != 1 else ''} remaining.\n"
            "Select a record to view details:",
            reply_markup=dns_list_keyboard(records, max(0, page - 1) if not records else page),
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.warning("Could not reload records after deletion: %s", exc)
        await query.edit_message_text(
            "✅ Record deleted successfully.",
            reply_markup=back_to_menu_keyboard(),
        )
