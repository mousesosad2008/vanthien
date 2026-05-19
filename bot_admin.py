import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Environment Variables ─────────────────────────────────────────────────────
ADMIN_BOT_TOKEN         = os.environ.get("ADMIN_BOT_TOKEN", "")
CUSTOMER_CARE_BOT_TOKEN = os.environ.get("CUSTOMER_CARE_BOT_TOKEN", "")
ADMIN_CHAT_ID           = int(os.environ.get("ADMIN_CHAT_ID", "6021515792"))

GROUP_CHAT_ID    = int(os.environ.get("GROUP_CHAT_ID", "0"))
PAYMENT_KEYWORD  = os.environ.get("PAYMENT_KEYWORD", "THANH_TOAN:")

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_LUOT_KICH = 5
DATA_FILE = "user_data.json"

# ── Admin state tracking ─────────────────────────────────────────────────────
admin_state: dict = {}  # {"step": "waiting_user_id" | "waiting_luot_kich", "target_user_id": int}

PACKAGE_LABELS = {
    "donate":     "💳 Donate & Kích Hoạt",
    "locket_vip": "⭐ Locket 1 Năm (VIP)",
}


# ── User Data (shared file with bot CSKH) ────────────────────────────────────

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(data: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "activated": False,
            "luot_kich": 0,
            "month": None,
            "name": "",
        }
    current_month = datetime.now().strftime("%Y-%m")
    if data[uid].get("month") != current_month and data[uid]["activated"]:
        data[uid]["luot_kich"] = DEFAULT_LUOT_KICH
        data[uid]["month"] = current_month
        save_data(data)
    return data[uid]

def activate_user(data: dict, user_id: int, name: str) -> None:
    uid = str(user_id)
    current_month = datetime.now().strftime("%Y-%m")
    if uid not in data:
        data[uid] = {
            "activated": True,
            "luot_kich": DEFAULT_LUOT_KICH,
            "month": current_month,
            "name": name,
        }
    else:
        data[uid]["activated"] = True
        if data[uid].get("month") != current_month:
            data[uid]["luot_kich"] = DEFAULT_LUOT_KICH
            data[uid]["month"] = current_month
        data[uid]["name"] = name
    save_data(data)


# ── Keyboards ─────────────────────────────────────────────────────────────────

def kb_back_vip() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Quay lại Menu", callback_data="back_vip")],
    ])

def kb_dns_after_activate() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Cài DNS", callback_data="cai_dns")],
        [InlineKeyboardButton("⬅️ Quay lại Menu", callback_data="back_vip")],
    ])

def kb_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Cấp lượt kích hoạt", callback_data="admin_cap_luot")],
        [InlineKeyboardButton("🔍 Xem thông tin user", callback_data="admin_xem_user")],
        [InlineKeyboardButton("📋 Danh sách tất cả user", callback_data="admin_list_users")],
    ])


# ── Handlers ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text(
            "⛔ <b>Bạn không có quyền sử dụng bot này.</b>\n\n"
            "Bot chỉ dành cho admin.",
            parse_mode="HTML",
        )
        return
    admin_state.clear()
    await update.message.reply_text(
        "👋 <b>Bot Admin Quản Lý</b>\n\n"
        "Chọn chức năng bên dưới:\n\n"
        "🎁 <b>Cấp lượt kích hoạt</b> — Nhập ID user + số lượt\n"
        "🔍 <b>Xem thông tin user</b> — Xem lượt kích hoạt của user\n"
        "📋 <b>Danh sách user</b> — Xem tất cả user đã đăng ký\n\n"
        "Bot cũng tự động nhận thông báo xác nhận từ bot CSKH.",
        parse_mode="HTML",
        reply_markup=kb_admin_menu(),
    )


def parse_payment_info(text: str) -> dict | None:
    if PAYMENT_KEYWORD not in text:
        return None
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    if "chat_id" not in result:
        return None
    return result


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if msg is None:
        return
    chat_id = msg.chat.id
    if GROUP_CHAT_ID != 0 and chat_id != GROUP_CHAT_ID:
        return
    if GROUP_CHAT_ID == 0 and msg.chat.type == "private":
        return

    text = msg.text or msg.caption or ""
    payment_info = parse_payment_info(text)
    if payment_info is None:
        return

    customer_chat_id = int(payment_info["chat_id"])
    ten      = payment_info.get("ten", "Không rõ")
    so_tien  = payment_info.get("so_tien", "Không rõ")
    noi_dung = payment_info.get("noi_dung", "Không có")

    notification_text = (
        "🔔 <b>Thông báo thanh toán mới!</b>\n\n"
        f"👤 <b>Tên:</b> {ten}\n"
        f"💰 <b>Số tiền:</b> {so_tien} VNĐ\n"
        f"📋 <b>Nội dung:</b> {noi_dung}\n"
        f"🆔 <b>Chat ID khách:</b> <code>{customer_chat_id}</code>"
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "✅ Xác nhận đã nhận tiền",
            callback_data=f"confirm:{customer_chat_id}:donate"
        )
    ]])

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=notification_text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    logger.info(f"Payment notification forwarded to admin for customer {customer_chat_id}")


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin text input for setting user credits."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    text = (update.message.text or "").strip()
    if not text:
        return

    step = admin_state.get("step")

    if step == "waiting_user_id":
        try:
            target_id = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ ID không hợp lệ. Vui lòng nhập ID dạng số (ví dụ: 6021515792):",
                parse_mode="HTML",
            )
            return
        admin_state["target_user_id"] = target_id
        admin_state["step"] = "waiting_luot_kich"
        await update.message.reply_text(
            f"✅ ID user: <code>{target_id}</code>\n\n"
            "Nhập <b>số lượt kích hoạt</b> muốn cấp cho user này:",
            parse_mode="HTML",
        )

    elif step == "waiting_luot_kich":
        try:
            luot = int(text)
            if luot < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "❌ Số lượt không hợp lệ. Vui lòng nhập số nguyên >= 0:",
                parse_mode="HTML",
            )
            return
        target_id = admin_state["target_user_id"]
        user_data = load_data()
        u = get_user(user_data, target_id)
        u["luot_kich"] = luot
        save_data(user_data)
        admin_state.clear()
        await update.message.reply_text(
            f"🎉 <b>Đã cấp {luot} lượt kích hoạt cho user</b> <code>{target_id}</code>!\n\n"
            f"📌 Lượt kích hoạt hiện tại: <b>{luot}</b>",
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )

    elif step == "waiting_view_user_id":
        try:
            target_id = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ ID không hợp lệ. Vui lòng nhập ID dạng số:",
                parse_mode="HTML",
            )
            return
        admin_state.clear()
        user_data = load_data()
        uid = str(target_id)
        if uid in user_data:
            u = user_data[uid]
            await update.message.reply_text(
                f"📋 <b>Thông tin user</b> <code>{target_id}</code>:\n\n"
                f"✅ Đã kích hoạt: <b>{'Có' if u.get('activated') else 'Chưa'}</b>\n"
                f"🔢 Lượt kích hoạt: <b>{u.get('luot_kich', 0)}</b>\n"
                f"📅 Tháng: <b>{u.get('month', 'N/A')}</b>\n"
                f"👤 Tên: <b>{u.get('name', 'N/A')}</b>",
                parse_mode="HTML",
                reply_markup=kb_admin_menu(),
            )
        else:
            await update.message.reply_text(
                f"❌ Không tìm thấy user <code>{target_id}</code> trong hệ thống.",
                parse_mode="HTML",
                reply_markup=kb_admin_menu(),
            )


async def handle_confirm_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if update.effective_chat.id != ADMIN_CHAT_ID:
        await query.answer("⛔ Bạn không có quyền thực hiện hành động này.", show_alert=True)
        return

    data = query.data

    # ── Admin menu buttons ──
    if data == "admin_cap_luot":
        admin_state.clear()
        admin_state["step"] = "waiting_user_id"
        await query.edit_message_text(
            "🎁 <b>Cấp lượt kích hoạt</b>\n\n"
            "Nhập <b>ID Telegram</b> của user cần cấp lượt:",
            parse_mode="HTML",
        )
        return

    if data == "admin_xem_user":
        admin_state.clear()
        admin_state["step"] = "waiting_view_user_id"
        await query.edit_message_text(
            "🔍 <b>Xem thông tin user</b>\n\n"
            "Nhập <b>ID Telegram</b> của user cần xem:",
            parse_mode="HTML",
        )
        return

    if data == "admin_list_users":
        admin_state.clear()
        user_data = load_data()
        if not user_data:
            await query.edit_message_text(
                "📋 <b>Chưa có user nào trong hệ thống.</b>",
                parse_mode="HTML",
                reply_markup=kb_admin_menu(),
            )
            return
        lines = ["📋 <b>Danh sách user:</b>\n"]
        for uid, info in user_data.items():
            status = "✅" if info.get("activated") else "❌"
            luot = info.get("luot_kich", 0)
            name = info.get("name", "")
            display = f" ({name})" if name else ""
            lines.append(f"{status} <code>{uid}</code>{display} — {luot} lượt")
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )
        return

    if data == "admin_back_menu":
        admin_state.clear()
        await query.edit_message_text(
            "👋 <b>Bot Admin Quản Lý</b>\n\n"
            "Chọn chức năng bên dưới:",
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )
        return

    # Load dữ liệu mới nhất từ file (vì bot CSKH có thể đã cập nhật)
    user_data = load_data()

    # ── Xác nhận thanh toán (kích hoạt tài khoản lần đầu) ──
    if data.startswith("confirm:"):
        parts       = data.split(":")
        customer_id = int(parts[1])
        package     = parts[2] if len(parts) > 2 else "unknown"
        label       = PACKAGE_LABELS.get(package, package)

        name = user_data.get(str(customer_id), {}).get("name", "")
        activate_user(user_data, customer_id, name)

        try:
            cskh_bot = Bot(token=CUSTOMER_CARE_BOT_TOKEN)
            await cskh_bot.send_message(
                chat_id=customer_id,
                text=(
                    "🎉 <b>Tài khoản đã được kích hoạt!</b>\n\n"
                    f"📦 Gói: {label}\n\n"
                    "Cảm ơn bạn đã ủng hộ! Admin đã xác nhận nhận tiền "
                    "và kích hoạt thành công. 💖\n\n"
                    "Bấm nút bên dưới để quay lại menu."
                ),
                parse_mode="HTML",
                reply_markup=kb_back_vip(),
            )
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                f"✅ Đã xác nhận và kích hoạt cho khách <code>{customer_id}</code>!",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to notify customer: {e}")
            await query.answer("❌ Lỗi khi gửi thông báo cho khách!", show_alert=True)

    # ── Xác nhận kích hoạt link user ──
    # (Bot CSKH đã trừ luot_kich khi user ấn nút, không cần trừ lại ở đây)
    elif data.startswith("confirm_link:"):
        customer_id = int(data.split(":")[1])

        u = get_user(user_data, customer_id)

        if u["luot_kich"] == 0:
            extra_msg = "\n\n⚠️ Bạn đã hết lượt kích hoạt trong tháng! Nạp thêm 10k để mua 5 lượt."
        else:
            extra_msg = ""

        try:
            cskh_bot = Bot(token=CUSTOMER_CARE_BOT_TOKEN)
            await cskh_bot.send_message(
                chat_id=customer_id,
                text=(
                    "🎉 <b>Link đã được kích hoạt thành công!</b>\n\n"
                    f"📌 Lượt kích hoạt còn lại: <b>{u['luot_kich']}</b>\n\n"
                    "📡 <b>Hướng dẫn giữ Gold bằng DNS:</b>\n"
                    "Bấm nút bên dưới để xem hướng dẫn cài DNS. 👇"
                    f"{extra_msg}"
                ),
                parse_mode="HTML",
                reply_markup=kb_dns_after_activate(),
            )
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                f"✅ Đã kích hoạt link cho khách <code>{customer_id}</code>! "
                f"(còn {u['luot_kich']} lượt)",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to notify customer: {e}")
            await query.answer("❌ Lỗi khi gửi thông báo cho khách!", show_alert=True)

    # ── Xác nhận kích hoạt lại ──
    # (Bot CSKH đã trừ luot_kich khi user ấn nút, không cần trừ lại ở đây)
    elif data.startswith("confirm_reactivate:"):
        customer_id = int(data.split(":")[1])

        u = get_user(user_data, customer_id)

        if u["luot_kich"] == 0:
            extra_msg = "\n\n⚠️ Bạn đã hết lượt kích hoạt trong tháng! Nạp thêm 10k để mua 5 lượt."
        else:
            extra_msg = ""

        try:
            cskh_bot = Bot(token=CUSTOMER_CARE_BOT_TOKEN)
            await cskh_bot.send_message(
                chat_id=customer_id,
                text=(
                    "🎉 <b>Đã kích hoạt lại thành công!</b>\n\n"
                    f"📌 Lượt kích hoạt còn lại: <b>{u['luot_kich']}</b>\n\n"
                    "📡 <b>Hướng dẫn giữ Gold bằng DNS:</b>\n"
                    "Bấm nút bên dưới để xem hướng dẫn cài DNS. 👇"
                    f"{extra_msg}"
                ),
                parse_mode="HTML",
                reply_markup=kb_dns_after_activate(),
            )
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                f"✅ Đã kích hoạt lại cho khách <code>{customer_id}</code>! "
                f"(còn {u['luot_kich']} lượt)",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to notify customer: {e}")
            await query.answer("❌ Lỗi khi gửi thông báo cho khách!", show_alert=True)

    # ── Xác nhận mua thêm 5 lượt ──
    elif data.startswith("confirm_extra:"):
        customer_id = int(data.split(":")[1])

        u = get_user(user_data, customer_id)
        u["luot_kich"] += 5
        save_data(user_data)

        try:
            cskh_bot = Bot(token=CUSTOMER_CARE_BOT_TOKEN)
            await cskh_bot.send_message(
                chat_id=customer_id,
                text=(
                    "🎉 <b>Đã cộng thêm 5 lượt kích hoạt!</b>\n\n"
                    f"📌 Lượt kích hoạt hiện tại: <b>{u['luot_kich']}</b>\n\n"
                    "Cảm ơn bạn đã ủng hộ! 💖"
                ),
                parse_mode="HTML",
                reply_markup=kb_back_vip(),
            )
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                f"✅ Đã cộng 5 lượt cho khách <code>{customer_id}</code>! "
                f"(tổng: {u['luot_kich']} lượt)",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to notify customer: {e}")
            await query.answer("❌ Lỗi khi gửi thông báo cho khách!", show_alert=True)


# ── Run ───────────────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_confirm_button))
    app.add_handler(MessageHandler(
        filters.Chat(ADMIN_CHAT_ID) & filters.TEXT & ~filters.COMMAND,
        handle_admin_text,
    ))
    app.add_handler(MessageHandler(
        ~filters.Chat(ADMIN_CHAT_ID) & ~filters.COMMAND,
        handle_group_message,
    ))

    logger.info("Bot Kiểm Duyệt is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    if not ADMIN_BOT_TOKEN:
        logger.error("Missing ADMIN_BOT_TOKEN environment variable.")
    else:
        main()
