"""Telegram inline-approval bot (primary HITL path) + a local fallback that drives the
exact same resume mechanics, so the demo isn't hard-blocked on Telegram being reachable
on stage.

Requires python-telegram-bot v20+ (async API): Application, CallbackQueryHandler.
"""

import asyncio
import threading
from typing import Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

APPROVE_CALLBACK = "approve"
REJECT_CALLBACK = "reject"


async def send_approval_request(bot_token: str, chat_id: str, payload: dict) -> None:
    """Sends the inline-keyboard approval message. `payload` is the dict returned by
    workflow.py's `interrupt()` call (title, market_price, margin_pct)."""
    app = Application.builder().token(bot_token).build()
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Approve & Publish", callback_data=APPROVE_CALLBACK),
                InlineKeyboardButton("Reject", callback_data=REJECT_CALLBACK),
            ]
        ]
    )
    text = (
        f"New listing pending approval:\n\n"
        f"*{payload.get('title')}*\n"
        f"Market price: ${payload.get('market_price'):.2f}\n"
        f"Margin: {payload.get('margin_pct'):.1f}%\n\n"
        f"Approve publishing?"
    )
    async with app:
        await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=keyboard)


async def broadcast_deal(bot_token: str, chat_id: str, broadcast_copy: str) -> None:
    """Sends the CopywriterAgent's broadcast copy after a listing is published."""
    app = Application.builder().token(bot_token).build()
    async with app:
        await app.bot.send_message(chat_id=chat_id, text=broadcast_copy)


def start_approval_listener(bot_token: str, on_decision: Callable[[str], None]) -> Application:
    """Starts a background-thread polling bot that calls `on_decision("approve"|"reject")`
    when a button is tapped. Returns the Application so the caller can stop() it later."""

    async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        decision = "approve" if query.data == APPROVE_CALLBACK else "reject"
        on_decision(decision)
        await query.edit_message_text(f"Decision received: {decision.upper()}")

    application = Application.builder().token(bot_token).build()
    application.add_handler(CallbackQueryHandler(handle_callback))

    def _run():
        asyncio.set_event_loop(asyncio.new_event_loop())
        application.run_polling(close_loop=False, stop_signals=None)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return application


def resume_locally(graph, config: dict, decision: str) -> dict:
    """Local fallback for the approval step — same resume path as the Telegram callback,
    callable directly from a notebook cell (e.g. driven by `input()`) if Telegram is
    unreachable on stage. `decision` must be "approve" or "reject"."""
    from workflow import resume_graph

    return resume_graph(graph, config, decision)
