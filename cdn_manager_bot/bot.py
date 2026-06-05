from __future__ import annotations
import logging
import re
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import cdn_dns_manager_bot.config as config
from cdn_dns_manager_bot.config import BOT_TOKEN, setup_logging
from cdn_dns_manager_bot.database import Database
from cdn_dns_manager_bot.handlers.create_record import (
    add_record_handler,
    confirm_create_handler,
    create_text_handler,
    proxied_chosen_handler,
    ttl_chosen_handler,
    type_chosen_handler,
)
from cdn_dns_manager_bot.handlers.delete_record import delete_confirm_handler, delete_record_handler
from cdn_dns_manager_bot.handlers.dns import dns_list_handler, dns_refresh_handler, record_view_handler
from cdn_dns_manager_bot.handlers.domains import (
    back_to_domain_menu_handler,
    back_to_zones_handler,
    zone_selected_handler,
)
from cdn_dns_manager_bot.handlers.edit_record import (
    edit_field_handler,
    edit_proxied_chosen_handler,
    edit_record_handler,
    edit_text_handler,
    edit_ttl_chosen_handler,
)
from cdn_dns_manager_bot.handlers.start import start_handler

setup_logging()
logger = logging.getLogger(__name__)


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or user.id != config.ADMIN_ID:
        if update.message:
            await update.message.reply_text("Access Denied")
        return

    db: Database = context.bot_data["db"]
    state_row = await db.get_state(user.id)

    if state_row is None:
        return  

    state_key = state_row[0]
    if state_key == "create":
        await create_text_handler(update, context)
    elif state_key == "edit":
        await edit_text_handler(update, context)


async def post_init(application: Application) -> None:  
    """Connect the database and store it in bot_data."""
    db = Database()
    await db.connect()
    application.bot_data["db"] = db
    logger.info("Bot initialised and database connected.")


async def post_shutdown(application: Application) -> None:  
    """Close the database on shutdown."""
    db: Database = application.bot_data.get("db")
    if db:
        await db.close()
    logger.info("Bot shut down cleanly.")


def main() -> None:
    """Build and run the bot."""
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start_handler))

    app.add_handler(CallbackQueryHandler(zone_selected_handler, pattern=r"^zone:"))
    app.add_handler(CallbackQueryHandler(back_to_zones_handler, pattern=r"^back:zones$"))
    app.add_handler(
        CallbackQueryHandler(back_to_domain_menu_handler, pattern=r"^back:domain_menu$")
    )

    app.add_handler(CallbackQueryHandler(dns_list_handler, pattern=r"^dns:list:"))
    app.add_handler(CallbackQueryHandler(dns_refresh_handler, pattern=r"^dns:refresh$"))
    app.add_handler(CallbackQueryHandler(record_view_handler, pattern=r"^rec:view:"))

    app.add_handler(CallbackQueryHandler(add_record_handler, pattern=r"^dns:add$"))
    app.add_handler(CallbackQueryHandler(type_chosen_handler, pattern=r"^create:type:"))
    app.add_handler(CallbackQueryHandler(ttl_chosen_handler, pattern=r"^create:ttl:"))
    app.add_handler(CallbackQueryHandler(proxied_chosen_handler, pattern=r"^create:proxied:"))
    app.add_handler(CallbackQueryHandler(confirm_create_handler, pattern=r"^create:confirm$"))

    app.add_handler(CallbackQueryHandler(edit_record_handler, pattern=r"^rec:edit:"))
    app.add_handler(CallbackQueryHandler(edit_field_handler, pattern=r"^edit:field:"))
    app.add_handler(CallbackQueryHandler(edit_ttl_chosen_handler, pattern=r"^edit:ttl:"))
    app.add_handler(
        CallbackQueryHandler(edit_proxied_chosen_handler, pattern=r"^edit:proxied:")
    )

    app.add_handler(CallbackQueryHandler(delete_record_handler, pattern=r"^rec:delete:"))
    app.add_handler(
        CallbackQueryHandler(delete_confirm_handler, pattern=r"^rec:delete_confirm:")
    )

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_router)
    )

    logger.info("Starting Cloudflare DNS Manager Bot…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
