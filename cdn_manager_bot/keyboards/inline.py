from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import PAGE_SIZE, SUPPORTED_RECORD_TYPES, TTL_OPTIONS
from utils.helpers import fmt_record_button, paginate


def zones_keyboard(zones: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(z["name"], callback_data=f"zone:{z['id']}:{z['name']}")]
        for z in zones
    ]
    return InlineKeyboardMarkup(rows)


def domain_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📋 DNS Records", callback_data="dns:list:0")],
            [InlineKeyboardButton("➕ Add Record", callback_data="dns:add")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="dns:refresh")],
            [InlineKeyboardButton("🔙 Back", callback_data="back:zones")],
        ]
    )


def dns_list_keyboard(records: list[dict], page: int = 0) -> InlineKeyboardMarkup:

    page_records, total_pages, current_page = paginate(records, page, PAGE_SIZE)

    rows: list[list[InlineKeyboardButton]] = []
    for rec in page_records:
        label = fmt_record_button(rec)
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"rec:view:{rec['id']}:{current_page}")]
        )

    nav: list[InlineKeyboardButton] = []
    if current_page > 0:
        nav.append(InlineKeyboardButton("⬅ Previous", callback_data=f"dns:list:{current_page - 1}"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡ Next", callback_data=f"dns:list:{current_page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("🔙 Back", callback_data="back:domain_menu")])
    return InlineKeyboardMarkup(rows)


def record_detail_keyboard(record_id: str, page: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏ Edit", callback_data=f"rec:edit:{record_id}:{page}"),
                InlineKeyboardButton("🗑 Delete", callback_data=f"rec:delete:{record_id}:{page}"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data=f"dns:list:{page}")],
        ]
    )


def delete_confirm_keyboard(record_id: str, page: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Yes, delete", callback_data=f"rec:delete_confirm:{record_id}:{page}"
                ),
                InlineKeyboardButton(
                    "❌ No, cancel", callback_data=f"rec:view:{record_id}:{page}"
                ),
            ]
        ]
    )


def record_type_keyboard() -> InlineKeyboardMarkup:
    """Two columns of record type buttons."""
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(SUPPORTED_RECORD_TYPES), 2):
        row = [
            InlineKeyboardButton(
                SUPPORTED_RECORD_TYPES[i],
                callback_data=f"create:type:{SUPPORTED_RECORD_TYPES[i]}",
            )
        ]
        if i + 1 < len(SUPPORTED_RECORD_TYPES):
            row.append(
                InlineKeyboardButton(
                    SUPPORTED_RECORD_TYPES[i + 1],
                    callback_data=f"create:type:{SUPPORTED_RECORD_TYPES[i + 1]}",
                )
            )
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 Cancel", callback_data="back:domain_menu")])
    return InlineKeyboardMarkup(rows)


def ttl_keyboard(callback_prefix: str = "create:ttl") -> InlineKeyboardMarkup:
    """Inline TTL selection grid (two columns)."""
    options = list(TTL_OPTIONS.items())
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(options), 2):
        label1, val1 = options[i]
        row = [InlineKeyboardButton(label1, callback_data=f"{callback_prefix}:{val1}")]
        if i + 1 < len(options):
            label2, val2 = options[i + 1]
            row.append(
                InlineKeyboardButton(label2, callback_data=f"{callback_prefix}:{val2}")
            )
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def proxied_keyboard(callback_prefix: str = "create:proxied") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🟠 Proxied (CDN)", callback_data=f"{callback_prefix}:true"
                ),
                InlineKeyboardButton(
                    "⚪ DNS Only", callback_data=f"{callback_prefix}:false"
                ),
            ]
        ]
    )



def confirm_create_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="create:confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="back:domain_menu"),
            ]
        ]
    )



def edit_field_keyboard(record_id: str, page: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Name", callback_data=f"edit:field:name:{record_id}:{page}")],
            [InlineKeyboardButton("Content", callback_data=f"edit:field:content:{record_id}:{page}")],
            [InlineKeyboardButton("TTL", callback_data=f"edit:field:ttl:{record_id}:{page}")],
            [InlineKeyboardButton("Proxied", callback_data=f"edit:field:proxied:{record_id}:{page}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"rec:view:{record_id}:{page}")],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Back to menu", callback_data="back:domain_menu")]]
    )
