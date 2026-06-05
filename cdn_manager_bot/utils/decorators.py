from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, Any

from telegram import Update
from telegram.ext import ContextTypes

from cdn_dns_manager_bot.config import ADMIN_ID

logger = logging.getLogger(__name__)


def admin_only(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any
    ) -> Any:
        user = update.effective_user
        if user is None or user.id != ADMIN_ID:
            uid = user.id if user else "unknown"
            logger.warning(
                "Unauthorized access attempt by user_id=%s on %s", uid, func.__name__
            )
            if update.callback_query:
                await update.callback_query.answer(
                    "Access Denied", show_alert=True
                )
            elif update.message:
                await update.message.reply_text("Access Denied")
            return None
        return await func(update, context, *args, **kwargs)

    return wrapper
