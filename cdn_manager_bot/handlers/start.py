from __future__ import annotations

import logging

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from cloudflare_api import CloudflareAPI, CloudflareAPIError
from keyboards.inline import zones_keyboard
from utils.decorators import admin_only

logger = logging.getLogger(__name__)


@admin_only
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if message is None:
        return

    db = context.bot_data["db"]
    user = update.effective_user
    logger.info("User %s triggered /start", user.id if user else "?")

    await message.reply_text("⏳ Fetching your Cloudflare zones…")

    try:
        async with CloudflareAPI() as cf:
            zones = await cf.get_zones()
    except CloudflareAPIError as exc:
        logger.error("Cloudflare API error on /start: %s", exc)
        await message.reply_text(
            f"❌ Cloudflare error:\n<code>{exc}</code>", parse_mode="HTML"
        )
        return
    except httpx.HTTPError as exc:
        logger.error("Network error on /start: %s", exc)
        await message.reply_text("❌ Network error while contacting Cloudflare. Please try again.")
        return

    if not zones:
        await message.reply_text(
            "⚠️ No zones found.  Make sure your API token has <b>Zone:Read</b> permission.",
            parse_mode="HTML",
        )
        return
    context.bot_data["zones"] = {z["id"]: z for z in zones}

    keyboard = zones_keyboard(zones)
    await message.reply_text(
        "🌐 <b>Select a domain to manage:</b>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
