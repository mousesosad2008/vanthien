"""
Bot By Mouse — Unified Telegram Bot
Gom tat ca chuc nang CSKH + Kiem Duyet vao 1 bot duy nhat.
Chi admin (ADMIN_CHAT_ID) moi co quyen dieu chinh thong so.
"""

import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
BOT_TOKEN     = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "6021515792"))

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

def activate_user(data: dict, user_id: int, package: str = "donate") -> dict:
    u = get_user(data, user_id)
    if not u["activated"]:
        u["activated"] = True
        u["luot_kich"] = DEFAULT_LUOT_KICH
        u["month"] = datetime.now().strftime("%Y-%m")
    save_data(data)
    return u


user_data = load_data()

# Track users waiting to input link
waiting_for_link: dict = {}

# Admin state tracking for multi-step input
admin_state: dict = {}

# Admin simulation mode (to preview customer view)
admin_simulate: bool = False


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
        [InlineKeyboardButton("🛒 Mua thêm lượt kích", callback_data="mua_them_luot")],
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

def kb_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Cấp lượt kích hoạt", callback_data="admin_cap_luot")],
        [InlineKeyboardButton("🔍 Xem thông tin user", callback_data="admin_xem_user")],
        [InlineKeyboardButton("📋 Danh sách tất cả user", callback_data="admin_list_users")],
    ])


# ── Text Templates ────────────────────────────────────────────────────────────

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
    global user_data, admin_simulate
    user_data = load_data()
    admin_simulate = False

    # ── Admin menu ──
    if user.id == ADMIN_CHAT_ID:
        admin_state.clear()
        u = get_user(user_data, user.id)
        await update.message.reply_text(
            "👋 <b>Bot By Mouse — Admin Panel</b>\n\n"
            "Chọn chức năng bên dưới:\n\n"
            "🎁 <b>Cấp lượt kích hoạt</b> — Nhập ID user + số lượt\n"
            "🔍 <b>Xem thông tin user</b> — Xem lượt kích hoạt của user\n"
            "📋 <b>Danh sách user</b> — Xem tất cả user đã đăng ký\n"
            "👁️ <b>/gialap</b> — Xem giao diện phía khách hàng\n\n"
            "Bot cũng tự động nhận thông báo xác nhận từ người dùng.",
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )
        return

    # ── User menu ──
    u = get_user(user_data, user.id)
    save_data(user_data)

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


async def gialap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin-only: simulate the customer view."""
    user = update.effective_user
    if user.id != ADMIN_CHAT_ID:
        return

    global user_data, admin_simulate
    admin_simulate = True
    admin_state.clear()
    user_data = load_data()
    u = get_user(user_data, user.id)
    save_data(user_data)

    if u["activated"]:
        await update.message.reply_text(
            "👁️ <b>[GIẢ LẬP] Giao diện khách hàng:</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            + text_welcome_vip(user, u["luot_kich"]),
            parse_mode="HTML",
            reply_markup=kb_main_vip(),
        )
    else:
        await update.message.reply_text(
            "👁️ <b>[GIẢ LẬP] Giao diện khách hàng (chưa kích hoạt):</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            + text_welcome_old(user),
            parse_mode="HTML",
            reply_markup=kb_main_old(),
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    uid  = user.id

    # ── Admin text input (for multi-step flows, only when NOT simulating) ──
    if uid == ADMIN_CHAT_ID and admin_state.get("step") and not admin_simulate:
        await handle_admin_text(update, context)
        return

    # ── User link input ──
    if uid not in waiting_for_link:
        return

    link = update.message.text.strip()
    action = waiting_for_link.pop(uid)

    if action == "activate":
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text_notify_admin_link(user, link),
            parse_mode="HTML",
            reply_markup=kb_admin_activate_link(user.id),
        )
        await update.message.reply_text(
            "⏳ <b>Vui lòng chờ!</b>\n\n"
            "Link của bạn đã được gửi đến admin.\n"
            "Admin sẽ kiểm tra và kích hoạt cho bạn sớm nhất có thể. 🙏",
            parse_mode="HTML",
            reply_markup=kb_back_vip(),
        )

    elif action == "reactivate":
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text_notify_admin_reactivate(user, link),
            parse_mode="HTML",
            reply_markup=kb_admin_reactivate_link(user.id),
        )
        await update.message.reply_text(
            "⏳ <b>Vui lòng chờ!</b>\n\n"
            "Yêu cầu kích hoạt lại đã được gửi đến admin.\n"
            "Admin sẽ kích hoạt lại cho bạn sớm nhất có thể. 🙏",
            parse_mode="HTML",
            reply_markup=kb_back_vip(),
        )


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin text input for multi-step flows."""
    text = (update.message.text or "").strip()
    if not text:
        return

    global user_data
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
        uid_str = str(target_id)
        if uid_str in user_data:
            u = user_data[uid_str]
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


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user

    global user_data
    data = query.data

    # ══════════════════════════════════════════════════════════════════════════
    # ADMIN-ONLY BUTTONS (skip if admin is in simulation mode)
    # ══════════════════════════════════════════════════════════════════════════

    # ── Admin menu buttons ──
    if data == "admin_cap_luot":
        if user.id != ADMIN_CHAT_ID or admin_simulate:
            return
        admin_state.clear()
        admin_state["step"] = "waiting_user_id"
        await query.edit_message_text(
            "🎁 <b>Cấp lượt kích hoạt</b>\n\n"
            "Nhập <b>ID Telegram</b> của user cần cấp lượt:",
            parse_mode="HTML",
        )
        return

    if data == "admin_xem_user":
        if user.id != ADMIN_CHAT_ID or admin_simulate:
            return
        admin_state.clear()
        admin_state["step"] = "waiting_view_user_id"
        await query.edit_message_text(
            "🔍 <b>Xem thông tin user</b>\n\n"
            "Nhập <b>ID Telegram</b> của user cần xem:",
            parse_mode="HTML",
        )
        return

    if data == "admin_list_users":
        if user.id != ADMIN_CHAT_ID or admin_simulate:
            return
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
        if user.id != ADMIN_CHAT_ID or admin_simulate:
            return
        admin_state.clear()
        await query.edit_message_text(
            "👋 <b>Bot By Mouse — Admin Panel</b>\n\n"
            "Chọn chức năng bên dưới:",
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )
        return

    # ── Admin confirm buttons (payment, activate, reactivate, extra) ──
    if data.startswith("confirm:"):
        if user.id != ADMIN_CHAT_ID:
            return
        parts = data.split(":")
        customer_id = int(parts[1])
        package = parts[2]
        user_data = load_data()
        activate_user(user_data, customer_id, package)
        u = get_user(user_data, customer_id)
        u["name"] = u.get("name", "")
        save_data(user_data)
        await query.edit_message_text(
            f"✅ <b>Đã xác nhận thanh toán & kích hoạt!</b>\n\n"
            f"🆔 Customer ID: <code>{customer_id}</code>\n"
            f"📦 Gói: {PACKAGE_LABELS.get(package, package)}\n"
            f"🔢 Lượt kích hoạt: <b>{u['luot_kich']}</b>",
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )
        try:
            await context.bot.send_message(
                chat_id=customer_id,
                text=(
                    "🎉 <b>Tài khoản đã được kích hoạt!</b>\n\n"
                    f"📦 Gói: {PACKAGE_LABELS.get(package, package)}\n"
                    f"🔢 Lượt kích hoạt: <b>{u['luot_kich']}</b>\n\n"
                    "Gửi /start để bắt đầu sử dụng!"
                ),
                parse_mode="HTML",
                reply_markup=kb_dns_after_activate(),
            )
        except Exception as e:
            logger.error(f"Cannot notify customer {customer_id}: {e}")
        return

    if data.startswith("confirm_link:"):
        if user.id != ADMIN_CHAT_ID:
            return
        customer_id = int(data.split(":")[1])
        await query.edit_message_text(
            f"✅ <b>Đã xác nhận kích hoạt link!</b>\n"
            f"🆔 Customer: <code>{customer_id}</code>",
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )
        try:
            await context.bot.send_message(
                chat_id=customer_id,
                text=(
                    "🎉 <b>Link đã được kích hoạt thành công!</b>\n\n"
                    "Cảm ơn bạn đã sử dụng dịch vụ! 🙏"
                ),
                parse_mode="HTML",
                reply_markup=kb_dns_after_activate(),
            )
        except Exception as e:
            logger.error(f"Cannot notify customer {customer_id}: {e}")
        return

    if data.startswith("confirm_reactivate:"):
        if user.id != ADMIN_CHAT_ID:
            return
        customer_id = int(data.split(":")[1])
        await query.edit_message_text(
            f"✅ <b>Đã xác nhận kích hoạt lại!</b>\n"
            f"🆔 Customer: <code>{customer_id}</code>",
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )
        try:
            await context.bot.send_message(
                chat_id=customer_id,
                text=(
                    "🎉 <b>Tài khoản đã được kích hoạt lại thành công!</b>\n\n"
                    "Cảm ơn bạn đã sử dụng dịch vụ! 🙏"
                ),
                parse_mode="HTML",
                reply_markup=kb_dns_after_activate(),
            )
        except Exception as e:
            logger.error(f"Cannot notify customer {customer_id}: {e}")
        return

    if data.startswith("confirm_extra:"):
        if user.id != ADMIN_CHAT_ID:
            return
        customer_id = int(data.split(":")[1])
        user_data = load_data()
        u = get_user(user_data, customer_id)
        u["luot_kich"] += 5
        save_data(user_data)
        await query.edit_message_text(
            f"✅ <b>Đã xác nhận & cộng 5 lượt!</b>\n"
            f"🆔 Customer: <code>{customer_id}</code>\n"
            f"🔢 Lượt kích hoạt mới: <b>{u['luot_kich']}</b>",
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )
        try:
            await context.bot.send_message(
                chat_id=customer_id,
                text=(
                    "🎉 <b>Đã cộng thêm 5 lượt kích hoạt!</b>\n\n"
                    f"🔢 Lượt kích hoạt hiện tại: <b>{u['luot_kich']}</b>\n\n"
                    "Cảm ơn bạn đã ủng hộ! 🙏"
                ),
                parse_mode="HTML",
                reply_markup=kb_back_vip(),
            )
        except Exception as e:
            logger.error(f"Cannot notify customer {customer_id}: {e}")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # USER BUTTONS
    # ══════════════════════════════════════════════════════════════════════════

    # ── Old menu buttons (for non-activated users) ──
    if data in ("donate", "locket_vip"):
        package = data
        await query.edit_message_text(
            text=text_qr(package),
            parse_mode="HTML",
            reply_markup=kb_qr(package),
        )
        await query.message.chat.send_photo(
            photo=QR_URL,
            caption="📲 Quét mã QR để thanh toán",
        )

    elif data.startswith("paid:"):
        package = data.split(":", 1)[1]
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text_notify_admin(user, package),
            parse_mode="HTML",
            reply_markup=kb_admin_confirm(user.id, package),
        )
        await query.edit_message_text(
            text=(
                "⏳ <b>Xin vui lòng chờ!</b>\n\n"
                "Thông tin của bạn đã được gửi đến admin.\n"
                "Admin sẽ xác minh và kích hoạt tài khoản cho bạn sớm nhất có thể. 🙏"
            ),
            parse_mode="HTML",
            reply_markup=kb_back(),
        )

    elif data == "back":
        await query.edit_message_text(
            text=text_welcome_old(user),
            parse_mode="HTML",
            reply_markup=kb_main_old(),
        )

    elif data == "doi_ngon_ngu":
        await query.answer("Tính năng Đổi Ngôn Ngữ sắp ra mắt!", show_alert=True)

    # ── VIP menu buttons (for activated users) ──
    elif data == "kich_hoat_link":
        user_data = load_data()
        u = get_user(user_data, user.id)
        if u["luot_kich"] > 0:
            u["luot_kich"] -= 1
            save_data(user_data)
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

    elif data == "cai_dns":
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

    elif data == "yeu_cau_kich_hoat_lai":
        user_data = load_data()
        u = get_user(user_data, user.id)
        if u["luot_kich"] > 0:
            u["luot_kich"] -= 1
            save_data(user_data)
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

    elif data == "mua_them_luot":
        await query.edit_message_text(
            "🛒 <b>Mua thêm lượt kích hoạt</b>\n\n"
            "Nạp <b>10k</b> để nhận thêm <b>5 lượt</b> kích hoạt.\n\n"
            "Quét mã QR bên dưới để thanh toán.",
            parse_mode="HTML",
            reply_markup=kb_buy_extra(),
        )
        await query.message.chat.send_photo(
            photo=QR_URL,
            caption="📲 Quét mã QR để thanh toán 10k — mua 5 lượt kích hoạt",
        )

    elif data == "paid_extra":
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text_notify_admin_extra_payment(user),
            parse_mode="HTML",
            reply_markup=kb_admin_confirm_extra(user.id),
        )
        await query.edit_message_text(
            "⏳ <b>Vui lòng chờ!</b>\n\n"
            "Thông tin thanh toán đã được gửi đến admin.\n"
            "Admin sẽ xác nhận và cộng thêm 5 lượt kích hoạt cho bạn. 🙏",
            parse_mode="HTML",
            reply_markup=kb_back_vip(),
        )

    elif data == "back_vip":
        waiting_for_link.pop(user.id, None)
        user_data = load_data()
        u = get_user(user_data, user.id)
        await query.edit_message_text(
            text_welcome_vip(user, u["luot_kich"]),
            parse_mode="HTML",
            reply_markup=kb_main_vip(),
        )


# ── Run ───────────────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gialap", gialap))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message,
    ))

    logger.info("Bot By Mouse is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("Missing BOT_TOKEN environment variable.")
    else:
        main()
