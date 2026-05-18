import os
import json
import asyncio
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
CUSTOMER_CARE_BOT_TOKEN = os.environ.get("CUSTOMER_CARE_BOT_TOKEN", "")
ADMIN_BOT_TOKEN         = os.environ.get("ADMIN_BOT_TOKEN", "")
ADMIN_CHAT_ID           = int(os.environ.get("ADMIN_CHAT_ID", "6021515792"))

# ── Constants ─────────────────────────────────────────────────────────────────
QR_URL = (
    "https://img.vietqr.io/image/MB-160220081111-compact2.png"
    "?accountName=PHAM+VAN+THIEN&addInfo=ck+cho+Thien"
)
URL_HO_TRO = "https://zalo.me/0968187142"
DNS_LINK   = "http://lockkethienchipp.click"
VIDEO_PATH = "dns_guide.mp4"

DEFAULT_GOI       = "⭐ VIP"
DEFAULT_LUOT_KICH = 5

PACKAGE_LABELS = {
    "donate":     "💳 Donate & Kích Hoạt",
    "locket_vip": "⭐ Locket 1 Năm (VIP)",
}

DATA_FILE = "user_data.json"


# ── User Data Management ─────────────────────────────────────────────────────

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def reload_user_data() -> dict:
    """Reload user data from file (admin bot may have changed it)."""
    global user_data
    user_data = load_data()
    return user_data

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


user_data = load_data()

# Track users waiting to input link
waiting_for_link = {}


# ── Keyboards ─────────────────────────────────────────────────────────────────

def kb_main_old() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Donate & Kích Hoạt", callback_data="donate")],
        [InlineKeyboardButton("⭐ Locket 1 Năm (VIP)",  callback_data="locket_vip")],
        [
            InlineKeyboardButton("🌐 Đổi Ngôn Ngữ", callback_data="doi_ngon_ngu"),
            InlineKeyboardButton("🆘 Hỗ Trợ",        url=URL_HO_TRO),
        ],
    ])

def kb_main_vip() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔗 Kích hoạt bằng link user", callback_data="kich_hoat_link"),
            InlineKeyboardButton("📡 Cài DNS", callback_data="cai_dns"),
        ],
        [
            InlineKeyboardButton("🔄 Yêu cầu kích hoạt lại", callback_data="yeu_cau_kich_hoat_lai"),
            InlineKeyboardButton("🆘 Hỗ trợ khách hàng", url=URL_HO_TRO),
        ],
    ])

def kb_qr(package: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tôi đã thanh toán", callback_data=f"paid:{package}")],
        [InlineKeyboardButton("⬅️ Quay lại",          callback_data="back")],
    ])

def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Quay lại", callback_data="back")],
    ])

def kb_back_vip() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Quay lại Menu", callback_data="back_vip")],
    ])

def kb_admin_confirm(customer_id: int, package: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Xác nhận đã nhận tiền",
            callback_data=f"confirm:{customer_id}:{package}"
        )],
    ])

def kb_admin_activate_link(customer_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Đã kích hoạt",
            callback_data=f"confirm_link:{customer_id}"
        )],
    ])

def kb_admin_reactivate_link(customer_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Đã kích hoạt lại",
            callback_data=f"confirm_reactivate:{customer_id}"
        )],
    ])

def kb_admin_confirm_extra(customer_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Xác nhận đã nhận tiền & +5 lượt",
            callback_data=f"confirm_extra:{customer_id}"
        )],
    ])

def kb_buy_extra() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Đã thanh toán 10k", callback_data="paid_extra")],
        [InlineKeyboardButton("⬅️ Quay lại Menu", callback_data="back_vip")],
    ])

def kb_dns_after_activate() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Cài DNS", callback_data="cai_dns")],
        [InlineKeyboardButton("⬅️ Quay lại Menu", callback_data="back_vip")],
    ])


# ── Texts ─────────────────────────────────────────────────────────────────────

def text_welcome_old(user) -> str:
    name = user.full_name or user.first_name or "Người dùng"
    return (
        f"👤 User: {name}\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"📦 Gói: {DEFAULT_GOI}\n"
        f"📌 Trạng thái: 🔒 Không giới hạn lượt kick\n\n"
        "💖 Hy vọng mỗi người sử dụng ủng hộ bọn mình 5-10k tùy mỗi người, "
        "cảm ơn mọi người đã ủng hộ!"
    )

def text_welcome_vip(user, luot_kich: int) -> str:
    name = user.full_name or user.first_name or "Người dùng"
    return (
        "🎉 <b>Locket Gold Bot By Văn Thiện</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👤 User: {name}\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"🏷️ Gói: {DEFAULT_GOI}\n"
        f"📌 Trạng thái: lượt kích trong tháng là <b>{luot_kich}</b> !"
    )

def text_qr(package: str) -> str:
    label = PACKAGE_LABELS.get(package, package)
    return (
        f"💳 <b>Thanh toán — {label}</b>\n\n"
        "Vui lòng quét mã QR bên dưới để chuyển khoản.\n"
        "Sau khi thanh toán, bấm <b>✅ Tôi đã thanh toán</b> để thông báo admin."
    )

def text_notify_admin(user, package: str) -> str:
    label = PACKAGE_LABELS.get(package, package)
    name  = user.full_name or user.first_name or "Người dùng"
    uname = f"@{user.username}" if user.username else "_(không có)_"
    return (
        "🔔 <b>Khách hàng mới cần xác minh!</b>\n\n"
        f"👤 Tên: {name}\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"📱 Username: {uname}\n"
        f"📦 Gói đăng ký: {label}\n\n"
        "Bấm nút bên dưới sau khi đã kiểm tra và xác nhận nhận tiền."
    )

def text_notify_admin_link(user, link: str) -> str:
    name  = user.full_name or user.first_name or "Người dùng"
    uname = f"@{user.username}" if user.username else "_(không có)_"
    return (
        "🔗 <b>Yêu cầu kích hoạt bằng link user!</b>\n\n"
        f"👤 Tên: {name}\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"📱 Username: {uname}\n"
        f"🔗 Link: {link}\n\n"
        "Bấm nút bên dưới sau khi đã kích hoạt."
    )

def text_notify_admin_reactivate(user, link: str) -> str:
    name  = user.full_name or user.first_name or "Người dùng"
    uname = f"@{user.username}" if user.username else "_(không có)_"
    return (
        "🔄 <b>Yêu cầu kích hoạt lại!</b>\n\n"
        f"👤 Tên: {name}\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"📱 Username: {uname}\n"
        f"🔗 Link: {link}\n\n"
        "Bấm nút bên dưới sau khi đã kích hoạt lại."
    )

def text_notify_admin_extra_payment(user) -> str:
    name  = user.full_name or user.first_name or "Người dùng"
    uname = f"@{user.username}" if user.username else "_(không có)_"
    return (
        "💰 <b>Khách mua thêm 5 lượt kích hoạt (10k)!</b>\n\n"
        f"👤 Tên: {name}\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"📱 Username: {uname}\n\n"
        "Bấm nút bên dưới sau khi đã xác nhận nhận tiền."
    )

DNS_GUIDE_TEXT = (
    "📡 <b>Hướng dẫn cài DNS cho iOS</b>\n"
    "━━━━━━━━━━━━━━━━━━━\n\n"
    "📲 <b>Bước 1:</b> Mở Safari trên iPhone\n\n"
    f"📲 <b>Bước 2:</b> Truy cập link: {DNS_LINK}\n\n"
    "📲 <b>Bước 3:</b> Bấm <b>\"Allow\"</b> khi được hỏi để tải profile\n\n"
    "📲 <b>Bước 4:</b> Vào <b>Cài đặt → Cài đặt chung → VPN & Quản lý thiết bị</b>\n\n"
    "📲 <b>Bước 5:</b> Bấm vào profile vừa tải → <b>Cài đặt</b> → Nhập mật khẩu\n\n"
    "📲 <b>Bước 6:</b> Hoàn tất! DNS đã được cài đặt ✅\n\n"
    "🎬 Xem video hướng dẫn bên dưới 👇"
)


# ── Handlers ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    reload_user_data()
    u = get_user(user_data, user.id)

    if u["activated"]:
        await update.message.reply_text(
            text_welcome_vip(user, u["luot_kich"]),
            parse_mode="HTML",
            reply_markup=kb_main_vip(),
        )
    else:
        await update.message.reply_text(
            text_welcome_old(user),
            parse_mode="HTML",
            reply_markup=kb_main_old(),
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    uid  = user.id

    if uid not in waiting_for_link:
        return

    link = update.message.text.strip()
    action = waiting_for_link.pop(uid)

    reload_user_data()
    u = get_user(user_data, uid)
    if u["luot_kich"] > 0:
        u["luot_kich"] -= 1
        save_data(user_data)

    if action == "activate":
        try:
            admin_bot = Bot(token=ADMIN_BOT_TOKEN)
            await admin_bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=text_notify_admin_link(user, link),
                parse_mode="HTML",
                reply_markup=kb_admin_activate_link(user.id),
            )
        except Exception as e:
            logger.error(f"Admin bot error: {e}")

        await update.message.reply_text(
            "⏳ <b>Vui lòng chờ!</b>\n\n"
            "Link của bạn đã được gửi đến admin.\n"
            "Admin sẽ kiểm tra và kích hoạt cho bạn sớm nhất có thể. 🙏",
            parse_mode="HTML",
            reply_markup=kb_back_vip(),
        )

    elif action == "reactivate":
        try:
            admin_bot = Bot(token=ADMIN_BOT_TOKEN)
            await admin_bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=text_notify_admin_reactivate(user, link),
                parse_mode="HTML",
                reply_markup=kb_admin_reactivate_link(user.id),
            )
        except Exception as e:
            logger.error(f"Admin bot error: {e}")

        await update.message.reply_text(
            "⏳ <b>Vui lòng chờ!</b>\n\n"
            "Yêu cầu kích hoạt lại đã được gửi đến admin.\n"
            "Admin sẽ kích hoạt lại cho bạn sớm nhất có thể. 🙏",
            parse_mode="HTML",
            reply_markup=kb_back_vip(),
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # ── Old menu buttons (for non-activated users) ──

    if query.data in ("donate", "locket_vip"):
        package = query.data
        await query.edit_message_text(
            text=text_qr(package),
            parse_mode="HTML",
            reply_markup=kb_qr(package),
        )
        await query.message.chat.send_photo(
            photo=QR_URL,
            caption="📲 Quét mã QR để thanh toán",
        )

    elif query.data.startswith("paid:"):
        package = query.data.split(":", 1)[1]

        try:
            admin_bot = Bot(token=ADMIN_BOT_TOKEN)
            await admin_bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=text_notify_admin(user, package),
                parse_mode="HTML",
                reply_markup=kb_admin_confirm(user.id, package),
            )
        except Exception as e:
            logger.error(f"Admin bot error: {e}")

        await query.edit_message_text(
            text=(
                "⏳ <b>Xin vui lòng chờ!</b>\n\n"
                "Thông tin của bạn đã được gửi đến admin.\n"
                "Admin sẽ xác minh và kích hoạt tài khoản cho bạn sớm nhất có thể. 🙏"
            ),
            parse_mode="HTML",
            reply_markup=kb_back(),
        )

    elif query.data == "back":
        await query.edit_message_text(
            text=text_welcome_old(user),
            parse_mode="HTML",
            reply_markup=kb_main_old(),
        )

    elif query.data == "doi_ngon_ngu":
        await query.answer("Tính năng Đổi Ngôn Ngữ sắp ra mắt!", show_alert=True)

    # ── VIP menu buttons (for activated users) ──

    elif query.data == "kich_hoat_link":
        reload_user_data()
        u = get_user(user_data, user.id)
        if u["luot_kich"] > 0:
            waiting_for_link[user.id] = "activate"
            await query.edit_message_text(
                "🔗 <b>Kích hoạt bằng link user</b>\n\n"
                f"Bạn còn <b>{u['luot_kich']}</b> lượt kích hoạt trong tháng.\n\n"
                "Vui lòng nhập link user của bạn:",
                parse_mode="HTML",
                reply_markup=kb_back_vip(),
            )
        else:
            await query.edit_message_text(
                "⚠️ <b>Hết lượt kích hoạt!</b>\n\n"
                "Bạn đã hết lượt kích hoạt trong tháng.\n"
                "Vui lòng nạp thêm <b>10k</b> để nhận thêm "
                "<b>5 lượt</b> kích hoạt.\n\n"
                "Quét mã QR bên dưới để thanh toán.",
                parse_mode="HTML",
                reply_markup=kb_buy_extra(),
            )
            await query.message.chat.send_photo(
                photo=QR_URL,
                caption="📲 Quét mã QR để thanh toán 10k — mua 5 lượt kích hoạt",
            )

    elif query.data == "cai_dns":
        await query.edit_message_text(
            DNS_GUIDE_TEXT,
            parse_mode="HTML",
            reply_markup=kb_back_vip(),
        )
        if os.path.exists(VIDEO_PATH):
            with open(VIDEO_PATH, "rb") as video_file:
                await query.message.chat.send_video(
                    video=video_file,
                    caption="🎬 Video hướng dẫn cài DNS",
                )

    elif query.data == "yeu_cau_kich_hoat_lai":
        reload_user_data()
        u = get_user(user_data, user.id)
        if u["luot_kich"] > 0:
            waiting_for_link[user.id] = "reactivate"
            await query.edit_message_text(
                "🔄 <b>Yêu cầu kích hoạt lại</b>\n\n"
                f"Bạn còn <b>{u['luot_kich']}</b> lượt kích hoạt trong tháng.\n\n"
                "Vui lòng nhập link user của bạn:",
                parse_mode="HTML",
                reply_markup=kb_back_vip(),
            )
        else:
            await query.edit_message_text(
                "⚠️ <b>Hết lượt kích hoạt!</b>\n\n"
                "Bạn đã hết lượt kích hoạt trong tháng.\n"
                "Vui lòng nạp thêm <b>10k</b> để nhận thêm "
                "<b>5 lượt</b> kích hoạt.\n\n"
                "Quét mã QR bên dưới để thanh toán.",
                parse_mode="HTML",
                reply_markup=kb_buy_extra(),
            )
            await query.message.chat.send_photo(
                photo=QR_URL,
                caption="📲 Quét mã QR để thanh toán 10k — mua 5 lượt kích hoạt",
            )

    elif query.data == "paid_extra":
        try:
            admin_bot = Bot(token=ADMIN_BOT_TOKEN)
            await admin_bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=text_notify_admin_extra_payment(user),
                parse_mode="HTML",
                reply_markup=kb_admin_confirm_extra(user.id),
            )
        except Exception as e:
            logger.error(f"Admin bot error: {e}")

        await query.edit_message_text(
            "⏳ <b>Vui lòng chờ!</b>\n\n"
            "Thông tin thanh toán đã được gửi đến admin.\n"
            "Admin sẽ xác nhận và cộng thêm 5 lượt kích hoạt cho bạn. 🙏",
            parse_mode="HTML",
            reply_markup=kb_back_vip(),
        )

    elif query.data == "back_vip":
        waiting_for_link.pop(user.id, None)
        reload_user_data()
        u = get_user(user_data, user.id)
        await query.edit_message_text(
            text_welcome_vip(user, u["luot_kich"]),
            parse_mode="HTML",
            reply_markup=kb_main_vip(),
        )


# ── Run ───────────────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(CUSTOMER_CARE_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text_message
    ))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot CSKH is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    if not CUSTOMER_CARE_BOT_TOKEN:
        logger.error("Missing CUSTOMER_CARE_BOT_TOKEN environment variable.")
    else:
        main()
