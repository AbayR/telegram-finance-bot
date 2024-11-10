import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
from gpt_function_calls import get_gpt_recommendation
from finance_manager import SessionLocal, Transaction
from sqlalchemy.orm import joinedload
from finance_manager import log_transaction, add_category, update_category, get_all_categories, get_transactions_by_category, get_all_transactions

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Helper to create dynamic category buttons
def dynamic_category_buttons():
    categories = get_all_categories()
    return InlineKeyboardMarkup([[InlineKeyboardButton(name.capitalize(), callback_data=f"category_{name}")] for name in categories])

# Start Command and Main Menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! I'm your financial assistant bot. Choose an option below to get started.",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("💸 Log Expense"), KeyboardButton("📊 View Transactions")],
            [KeyboardButton("➕ Add Category"), KeyboardButton("✏️ Update Category")],
            [KeyboardButton("🎯 Set Budget"), KeyboardButton("📊 View Summary")]
        ], resize_keyboard=True)
    )

# Handle Main Menu Buttons
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💸 Log Expense":
        await log_expense(update, context)
    elif text == "📊 View Transactions":
        await view_transactions(update, context)
    elif text == "➕ Add Category":
        await update.message.reply_text("Please enter the category name using: /add_category category_name")
    elif text == "✏️ Update Category":
        await update.message.reply_text("Please update a category using: /update_category old_name new_name")
    elif text == "🎯 Set Budget":
        await update.message.reply_text("🎯 Set Budget feature coming soon!")
    elif text == "📊 View Summary":
        await update.message.reply_text("📊 View Summary feature coming soon!")

# Log Expense with Dynamic Categories
async def log_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Choose a category for logging an expense:", reply_markup=dynamic_category_buttons())

# Get Transactions All
async def get_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    transactions = session.query(Transaction).options(joinedload(Transaction.category)).all()
    session.close()  # Close session after fetching data

    if not transactions:
        await update.message.reply_text("No transactions found.")
    else:
        transaction_details = "\n".join([
            f"💵 {t.amount} on {t.date.strftime('%Y-%m-%d')} ({t.category.name.capitalize()})" for t in transactions
        ])
        await update.message.reply_text(f"Transactions:\n{transaction_details}")
        
# Handle Category Selection for Expense Logging
async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category_name = query.data.split("_")[1]  # Extract category name from callback data
    context.user_data["category"] = category_name  # Store selected category in user data
    await query.edit_message_text(f"Category '{category_name.capitalize()}' selected. Now, please enter the amount.")

# Log the amount after category is selected
async def handle_amount_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = update.message.text  # Amount entered by the user
    category_name = context.user_data.get("category")
    
    if category_name:
        result = log_transaction(amount, category_name)
        await update.message.reply_text(result)
        context.user_data.pop("category")  # Clear stored category after logging
    else:
        await update.message.reply_text("Please choose a category first.")

# Display Transactions by Category
async def view_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Select a category to view transactions:", reply_markup=dynamic_category_buttons())

# Show Transactions for Selected Category
async def show_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category_name = query.data.split("_")[1]
    transactions = get_transactions_by_category(category_name)
    
    if not transactions:
        await query.edit_message_text(f"No transactions found for '{category_name.capitalize()}'.")
    else:
        transaction_details = "\n".join([f"💵 {t.amount} on {t.date.strftime('%Y-%m-%d')}" for t in transactions])
        await query.edit_message_text(f"Transactions for '{category_name.capitalize()}':\n{transaction_details}")

# Add a new category
async def add_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        category_name = update.message.text.split(" ", 1)[1]  # Expect format: /add_category category_name
        result = add_category(category_name)
        await update.message.reply_text(result)
    except IndexError:
        await update.message.reply_text("Please provide a category name using: /add_category category_name")

# Update an existing category
async def update_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = update.message.text.split(" ", 2)  # Expect format: /update_category old_name new_name
        result = update_category(args[1], args[2])
        await update.message.reply_text(result)
    except IndexError:
        await update.message.reply_text("Please provide both old and new category names using: /update_category old_name new_name")

# Main Function
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Command Handlers for Direct Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_category", add_category_handler))
    app.add_handler(CommandHandler("update_category", update_category_handler))
    app.add_handler(CommandHandler("transactions", get_transactions))
    
    # Inline button callback handlers for categories and transactions
    app.add_handler(CallbackQueryHandler(handle_category_selection, pattern="^category_"))
    app.add_handler(CallbackQueryHandler(show_transactions, pattern="^category_"))

    # Menu button handlers for main menu items
    app.add_handler(MessageHandler(filters.Regex("^(💸 Log Expense|📊 View Transactions|➕ Add Category|✏️ Update Category|🎯 Set Budget|📊 View Summary)$"), handle_menu_buttons))
    
    # Message handler for amount entry after category is selected
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^\d+(\.\d{1,2})?$"), handle_amount_entry))
    
    app.run_polling()
