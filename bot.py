import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
from gpt_function_calls import get_gpt_recommendation
from finance_manager import SessionLocal, Transaction, log_transaction, add_category, update_category, get_all_categories, get_transactions_by_category, get_all_transactions, delete_category
from sqlalchemy.orm import joinedload

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

def dynamic_category_buttons(callback_prefix="category"):
    """
    Returns an inline keyboard of all categories with callback data formatted as:
    <callback_prefix>_<category_name>
    """
    categories = get_all_categories()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name.capitalize(), callback_data=f"{callback_prefix}_{name}")]
        for name in categories
    ])

# Start Command and Main Menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! I'm your financial assistant bot. Choose an option below to get started.",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("💸 Log Expense"), KeyboardButton("📊 View Transactions")],
            [KeyboardButton("➕ Add Category"), KeyboardButton("✏️ Update Category")],
            [KeyboardButton("🎯 Set Budget"), KeyboardButton("📊 View Summary")],
            [KeyboardButton("🤖 Get GPT Recommendation"), KeyboardButton("❌ Delete Category")]
        ], resize_keyboard=True)
    )

# Handle Main Menu Button clicks
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💸 Log Expense":
        await log_expense(update, context)
    elif text == "📊 View Transactions":
        await view_transactions(update, context)
    elif text == "➕ Add Category":
        context.user_data['adding_category'] = True
        await update.message.reply_text("Enter the name of the category:")
    elif text == "✏️ Update Category":
        context.user_data['updating_category'] = True
        await update.message.reply_text("Select a category to update:", 
                                        reply_markup=dynamic_category_buttons("update_category"))
    elif text == "🎯 Set Budget":
        context.user_data['setting_budget'] = True
        await update.message.reply_text("Enter your budget amount:")
    elif text == "📊 View Summary":
        await view_summary(update, context)
    elif text == "🤖 Get GPT Recommendation":
        context.user_data['getting_gpt'] = True
        await update.message.reply_text("Please enter a prompt for GPT recommendation:")
    elif text == "❌ Delete Category":
        context.user_data['deleting_category'] = True
        await update.message.reply_text("Select a category to delete:",
                                        reply_markup=dynamic_category_buttons("delete_category"))

# Log Expense: send inline keyboard for category selection
async def log_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = dynamic_category_buttons("log_category")
    if keyboard.inline_keyboard:
        await update.message.reply_text("Choose a category for logging an expense:", reply_markup=keyboard)
    else:
        await update.message.reply_text("No categories available. Please add a category first.")

# View Transactions: send inline keyboard for category selection
async def view_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = dynamic_category_buttons("view_category")
    if keyboard.inline_keyboard:
        await update.message.reply_text("Select a category to view transactions:", reply_markup=keyboard)
    else:
        await update.message.reply_text("No categories available.")

# View Summary: calculates total expenses and compares them to the set budget
async def view_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    budget = context.user_data.get('budget')
    session = SessionLocal()
    transactions = session.query(Transaction).all()
    session.close()
    total_expenses = sum(t.amount for t in transactions)
    if budget is None:
        await update.message.reply_text(f"You haven't set a budget yet.\nTotal expenses so far: {total_expenses}")
    else:
        remaining = budget - total_expenses
        await update.message.reply_text(f"Budget: {budget}\nTotal expenses: {total_expenses}\nRemaining: {remaining}")

# Unified text message handler that processes input based on current mode
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Adding a new category
    if context.user_data.get('adding_category'):
        result = add_category(text)
        await update.message.reply_text(result)
        context.user_data['adding_category'] = False
        return

    # Updating an existing category's name
    elif context.user_data.get('updating_category') and 'category_to_update' in context.user_data:
        old_name = context.user_data['category_to_update']
        result = update_category(old_name, text)
        await update.message.reply_text(result)
        context.user_data.pop('category_to_update', None)
        context.user_data['updating_category'] = False
        return

    # Processing GPT recommendation prompt
    elif context.user_data.get('getting_gpt'):
        response = get_gpt_recommendation(text)
        await update.message.reply_text(response)
        context.user_data['getting_gpt'] = False
        return

    # Setting a budget
    elif context.user_data.get('setting_budget'):
        try:
            budget = float(text)
            context.user_data['budget'] = budget
            await update.message.reply_text(f"Budget set to {budget}")
        except ValueError:
            await update.message.reply_text("Please enter a valid number for the budget.")
        context.user_data['setting_budget'] = False
        return

    # Logging expense amount (after a category is selected)
    elif context.user_data.get('category'):
        try:
            float(text)  # Validate number conversion
            result = log_transaction(text, context.user_data["category"])
            await update.message.reply_text(result)
        except ValueError:
            await update.message.reply_text("Please enter a valid number for the amount.")
        context.user_data.pop("category", None)
        return

    # In deletion mode, remind user to use inline buttons
    elif context.user_data.get('deleting_category'):
        await update.message.reply_text("Please select a category to delete using the inline buttons.")
        return

    else:
        await update.message.reply_text("I didn't understand that. Please select an option from the menu.")

# Callback handler for expense logging: category button pressed
async def handle_log_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prefix = "log_category_"
    if query.data.startswith(prefix):
        category_name = query.data[len(prefix):]
        context.user_data["category"] = category_name 
        await query.edit_message_text(f"Category '{category_name.capitalize()}' selected. Now, please enter the amount.")

# Callback handler for viewing transactions: category button pressed
async def handle_view_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prefix = "view_category_"
    if query.data.startswith(prefix):
        category_name = query.data[len(prefix):]
        transactions = get_transactions_by_category(category_name)
        if not transactions:
            await query.edit_message_text(f"No transactions found for '{category_name.capitalize()}'.")
        else:
            transaction_details = "\n".join([
                f"💵 {t.amount} on {t.date.strftime('%Y-%m-%d')}" for t in transactions
            ])
            await query.edit_message_text(f"Transactions for '{category_name.capitalize()}':\n{transaction_details}")

# Callback handler for updating category: category button pressed
async def handle_update_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prefix = "update_category_"
    if query.data.startswith(prefix):
        category_name = query.data[len(prefix):]
        context.user_data['category_to_update'] = category_name  
        await query.edit_message_text(f"Category '{category_name.capitalize()}' selected. Now, please enter the new name for this category.")

# Callback handler for deleting category: category button pressed
async def handle_delete_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prefix = "delete_category_"
    if query.data.startswith(prefix):
        category_name = query.data[len(prefix):]
        result = delete_category(category_name)
        await query.edit_message_text(result)
        context.user_data['deleting_category'] = False

# Main function to add handlers and start polling
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("transactions", get_all_transactions))
    
    # Callback Query Handlers for inline buttons
    app.add_handler(CallbackQueryHandler(handle_log_category_selection, pattern="^log_category_"))
    app.add_handler(CallbackQueryHandler(handle_view_category_selection, pattern="^view_category_"))
    app.add_handler(CallbackQueryHandler(handle_update_category_selection, pattern="^update_category_"))
    app.add_handler(CallbackQueryHandler(handle_delete_category_selection, pattern="^delete_category_"))
    
    # Main Menu Buttons Handler (using regex to match exact menu text)
    app.add_handler(MessageHandler(
        filters.Regex("^(💸 Log Expense|📊 View Transactions|➕ Add Category|✏️ Update Category|❌ Delete Category|🎯 Set Budget|📊 View Summary|🤖 Get GPT Recommendation)$"),
        handle_menu_buttons
    ))
    
    # Unified text message handler for processing input in different modes
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    app.run_polling()
