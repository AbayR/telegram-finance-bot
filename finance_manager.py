import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Set up the database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///transactions.db")  # Default to SQLite
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the Category model
class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

# Define the Transaction model
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    category = relationship("Category")
    description = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Function to add a new category
def add_category(name: str) -> str:
    session = SessionLocal()
    if session.query(Category).filter_by(name=name.lower()).first():
        session.close()
        return "❌ Category already exists."
    
    new_category = Category(name=name.lower())
    session.add(new_category)
    session.commit()
    session.close()
    return f"✅ Category '{name}' added successfully."

# Function to update an existing category
def update_category(old_name: str, new_name: str) -> str:
    session = SessionLocal()
    category = session.query(Category).filter_by(name=old_name.lower()).first()
    if not category:
        session.close()
        return "❌ Category not found."
    
    category.name = new_name.lower()
    session.commit()
    session.close()
    return f"✅ Category '{old_name}' updated to '{new_name}'."

# Function to retrieve all categories
def get_all_categories():
    session = SessionLocal()
    categories = session.query(Category).all()
    session.close()
    return [category.name for category in categories]

# Function to log a transaction with dynamic category support
def log_transaction(amount: str, category_name: str, description: str = "") -> str:
    session = SessionLocal()
    amount = float(amount)
    
    # Get or create category
    category = session.query(Category).filter_by(name=category_name.lower()).first()
    if not category:
        session.close()
        return f"❌ Category '{category_name}' does not exist."
    
    new_transaction = Transaction(amount=amount, category_id=category.id, description=description)
    session.add(new_transaction)
    session.commit()
    session.close()
    return f"✅ Transaction logged successfully for {category_name} with amount {amount}."

# Function to retrieve transactions by category
def get_transactions_by_category(category_name: str):
    session = SessionLocal()
    category = session.query(Category).filter_by(name=category_name.lower()).first()
    if not category:
        session.close()
        return []
    
    transactions = session.query(Transaction).filter_by(category_id=category.id).all()
    session.close()
    return transactions

# Function to retrieve all transactions
def get_all_transactions():
    session = SessionLocal()
    try:
        # Use eager loading to load categories with transactions
        transactions = session.query(Transaction).options(joinedload(Transaction.category)).all()
        return transactions
    finally:
        session.close()
