
from __future__ import annotations

import logging
from typing import Any

from telegram import InlineKeyboardMarkup, Message, CallbackQuery

logger = logging.getLogger(__name__)


def fmt_record_button(record: dict) -> str:

    rtype = record.get("type", "?")
    name = record.get("name", "?")
    return f"{rtype} | {name}"


def fmt_ttl(ttl: int) -> str:
    if ttl == 1:
        return "Auto"
    if ttl < 60:
        return f"{ttl}s"
    if ttl < 3600:
        return f"{ttl // 60}m"
    if ttl < 86400:
        return f"{ttl // 3600}h"
    return f"{ttl // 86400}d"


def fmt_record_detail(record: dict) -> str:

    proxied = record.get("proxied")
    proxied_str = "✅ Yes" if proxied else "❌ No"
    ttl_str = fmt_ttl(record.get("ttl", 1))

    lines = [
        f"<b>Type:</b>    {record.get('type', '?')}",
        f"<b>Name:</b>    <code>{record.get('name', '?')}</code>",
        f"<b>Content:</b> <code>{record.get('content', '?')}</code>",
        f"<b>TTL:</b>     {ttl_str}",
        f"<b>Proxied:</b> {proxied_str}",
    ]

    if record.get("type") == "MX":
        priority = record.get("priority", "?")
        lines.append(f"<b>Priority:</b> {priority}")
    elif record.get("type") == "SRV":
        data = record.get("data", {})
        lines.append(f"<b>Service:</b>  {data.get('service', '?')}")
        lines.append(f"<b>Proto:</b>    {data.get('proto', '?')}")
        lines.append(f"<b>Priority:</b> {data.get('priority', '?')}")
        lines.append(f"<b>Weight:</b>   {data.get('weight', '?')}")
        lines.append(f"<b>Port:</b>     {data.get('port', '?')}")
        lines.append(f"<b>Target:</b>   {data.get('target', '?')}")

    return "\n".join(lines)


def paginate(items: list[Any], page: int, page_size: int) -> tuple[list[Any], int, int]:

    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = start + page_size
    return items[start:end], total_pages, page


async def safe_edit_or_reply(
    update_obj: Message | CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> None:
    

    from telegram.error import BadRequest

    try:
        if isinstance(update_obj, CallbackQuery):
            await update_obj.edit_message_text(
                text, reply_markup=reply_markup, parse_mode=parse_mode
            )
        else:
            await update_obj.reply_text(
                text, reply_markup=reply_markup, parse_mode=parse_mode
            )
    except BadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        raise
