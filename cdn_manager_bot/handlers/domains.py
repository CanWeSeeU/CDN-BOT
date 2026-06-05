from __future__ import annotations
import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes

from cdn_dns_manager_bot.cloudflare_api import CloudflareAPI, CloudflareAPIError
from cdn_dns_manager_bot.keyboards.inline import domain_menu_keyboard, zones_keyboard
from cdn_dns_manager_bot.utils.decorators import admin_only

logger = logging.getLogger(__name__)


@admin_only
async def zone_selected_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    _, zone_id, zone_name = query.data.split(":", 2)
    user_id = update.effective_user.id 

    db = context.bot_data["db"]
    await db.set_selected_zone(user_id, zone_id, zone_name)
    await db.invalidate_dns_cache(zone_id)

    logger.info("User %s selected zone %s (%s)", user_id, zone_name, zone_id)

    await query.edit_message_text(
        f"🌐 <b>{zone_name}</b>\n\nWhat would you like to do?",
        reply_markup=domain_menu_keyboard(),
        parse_mode="HTML",
    )


@admin_only
async def back_to_zones_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    await query.edit_message_text("⏳ Fetching your Cloudflare zones…")

    try:
        async with CloudflareAPI() as cf:
            zones = await cf.get_zones()
    except CloudflareAPIError as exc:
        logger.error("Cloudflare error fetching zones: %s", exc)
        await query.edit_message_text(f"❌ Cloudflare error:\n<code>{exc}</code>", parse_mode="HTML")
        return
    except httpx.HTTPError as exc:
        logger.error("Network error fetching zones: %s", exc)
        await query.edit_message_text("❌ Network error. Please try again.")
        return

    if not zones:
        await query.edit_message_text("⚠️ No zones found.")
        return

    context.bot_data["zones"] = {z["id"]: z for z in zones}
    await query.edit_message_text(
        "🌐 <b>Select a domain to manage:</b>",
        reply_markup=zones_keyboard(zones),
        parse_mode="HTML",
    )


@admin_only
async def back_to_domain_menu_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    user_id = update.effective_user.id  
    db = context.bot_data["db"]
    zone = await db.get_selected_zone(user_id)

    if zone is None:
        await query.edit_message_text("⚠️ No zone selected. Use /start to pick one.")
        return

    await query.edit_message_text(
        f"🌐 <b>{zone['zone_name']}</b>\n\nWhat would you like to do?",
        reply_markup=domain_menu_keyboard(),
        parse_mode="HTML",
    )
