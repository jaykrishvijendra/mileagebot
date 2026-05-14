from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.models.entry import today_str


def date_keyboard(today: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"Today ({today})", callback_data=f"date:{today}"),
        InlineKeyboardButton("Enter manually", callback_data="date:manual"),
    ]])


def class_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Class 3", callback_data="class:3"),
        InlineKeyboardButton("Class 4", callback_data="class:4"),
    ]])


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Submit", callback_data="confirm:yes"),
        InlineKeyboardButton("✏️ Edit", callback_data="confirm:edit"),
        InlineKeyboardButton("❌ Cancel", callback_data="confirm:cancel"),
    ]])


def sanity_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yes, confirm", callback_data="sanity:yes"),
        InlineKeyboardButton("❌ Cancel", callback_data="sanity:cancel"),
    ]])
