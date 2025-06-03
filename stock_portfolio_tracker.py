import requests
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from dataclasses import dataclass
import time

@dataclass
class Stock:
    symbol: str
    shares: float
    purchase_price: float
    purchase_date: str
    current_price: float = 0.0
    
    @property
    def total_value(self) -> float:
        return self.shares * self.current_price
    
    @property
    def total_cost(self) -> float:
        return self.shares * self.purchase_price
    
    @property
    def gain_loss(self) -> float:
        return self.total_value - self.total_cost
    
    @property
    def gain_loss_percentage(self) -> float:
        if self.total_cost == 0:
            return 0.0
        return (self.gain_loss / self.total_cost) * 100

class StockDataAPI:
    def __init__(self, api_key: str = "452XSQ6WDN73XVTP"):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        
    def get_stock_price(self, symbol: str) -> Optional[float]:
        
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            
            if 'Global Quote' in data:
                price = float(data['Global Quote']['05. price'])
                return price
            else:
                # Fallback to demo data for demonstration
                return self._get_demo_price(symbol)
                
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            return self._get_demo_price(symbol)
    
    def _get_demo_price(self, symbol: str) -> float:
        """Demo prices for testing when API is not available"""
        demo_prices = {
            'AAPL': 175.50,
            'GOOGL': 2850.00,
            'MSFT': 350.25,
            'TSLA': 225.80,
            'AMZN': 145.30,
            'NVDA': 875.40,
            'META': 485.60,
            'NFLX': 425.90
        }
        
        # Add some random variation to make it look realistic
        import random
        base_price = demo_prices.get(symbol.upper(), 100.0)
        variation = random.uniform(-0.05, 0.05) 
        return round(base_price * (1 + variation), 2)

class PortfolioDatabase:
    
    def __init__(self, db_path: str = "portfolio.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                shares REAL NOT NULL,
                purchase_price REAL NOT NULL,
                purchase_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                shares REAL NOT NULL,
                price REAL NOT NULL,
                transaction_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_holding(self, symbol: str, shares: float, purchase_price: float, purchase_date: str):
        """Add a new stock holding to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO holdings (symbol, shares, purchase_price, purchase_date)
            VALUES (?, ?, ?, ?)
        ''', (symbol.upper(), shares, purchase_price, purchase_date))
        
        # Also record as a transaction
        cursor.execute('''
            INSERT INTO transactions (symbol, transaction_type, shares, price, transaction_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol.upper(), 'BUY', shares, purchase_price, purchase_date))
        
        conn.commit()
        conn.close()
    
    def remove_holding(self, symbol: str, shares: float, sale_price: float):
        """Remove or reduce a stock holding"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current holdings for this symbol
        cursor.execute('''
            SELECT SUM(shares) FROM holdings WHERE symbol = ?
        ''', (symbol.upper(),))
        
        result = cursor.fetchone()
        current_shares = result[0] if result[0] else 0
        
        if current_shares < shares:
            conn.close()
            raise ValueError(f"Cannot sell {shares} shares. Only {current_shares} shares available.")
        
        # Record the sale transaction
        cursor.execute('''
            INSERT INTO transactions (symbol, transaction_type, shares, price, transaction_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol.upper(), 'SELL', shares, sale_price, datetime.now().strftime('%Y-%m-%d')))
        
        # Remove shares (FIFO - First In, First Out)
        remaining_to_sell = shares
        cursor.execute('''
            SELECT id, shares FROM holdings 
            WHERE symbol = ? AND shares > 0 
            ORDER BY purchase_date ASC
        ''', (symbol.upper(),))
        
        holdings = cursor.fetchall()
        
        for holding_id, holding_shares in holdings:
            if remaining_to_sell <= 0:
                break
                
            if holding_shares <= remaining_to_sell:
                # Remove entire holding
                cursor.execute('DELETE FROM holdings WHERE id = ?', (holding_id,))
                remaining_to_sell -= holding_shares
            else:
                # Reduce holding
                new_shares = holding_shares - remaining_to_sell
                cursor.execute('UPDATE holdings SET shares = ? WHERE id = ?', (new_shares, holding_id))
                remaining_to_sell = 0
        
        conn.commit()
        conn.close()
    
    def get_all_holdings(self) -> List[Tuple]:
        """Get all current holdings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, SUM(shares) as total_shares, 
                   AVG(purchase_price) as avg_price,
                   MIN(purchase_date) as first_purchase
            FROM holdings 
            WHERE shares > 0
            GROUP BY symbol
        ''')
        
        holdings = cursor.fetchall()
        conn.close()
        return holdings
    
    def get_transactions(self, symbol: str = None) -> List[Tuple]:
        """Get transaction history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT * FROM transactions 
                WHERE symbol = ? 
                ORDER BY transaction_date DESC
            ''', (symbol.upper(),))
        else:
            cursor.execute('''
                SELECT * FROM transactions 
                ORDER BY transaction_date DESC
            ''')
        
        transactions = cursor.fetchall()
        conn.close()
        return transactions

class PortfolioTracker:
    """Main portfolio tracking class"""
    
    def __init__(self, api_key: str = "demo"):
        self.api = StockDataAPI(api_key)
        self.db = PortfolioDatabase()
        self.stocks: List[Stock] = []
    
    def add_stock(self, symbol: str, shares: float, purchase_price: float, 
                  purchase_date: str = None):
        """Add a stock to the portfolio"""
        if purchase_date is None:
            purchase_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            self.db.add_holding(symbol, shares, purchase_price, purchase_date)
            print(f"✅ Added {shares} shares of {symbol.upper()} at ${purchase_price:.2f}")
        except Exception as e:
            print(f"❌ Error adding stock: {e}")
    
    def remove_stock(self, symbol: str, shares: float, sale_price: float = None):
        """Remove/sell stocks from portfolio"""
        if sale_price is None:
            current_price = self.api.get_stock_price(symbol)
            sale_price = current_price if current_price else 0
        
        try:
            self.db.remove_holding(symbol, shares, sale_price)
            print(f"✅ Sold {shares} shares of {symbol.upper()} at ${sale_price:.2f}")
        except Exception as e:
            print(f"❌ Error selling stock: {e}")
    
    def update_prices(self):
        """Update current prices for all holdings"""
        print("📊 Updating stock prices...")
        holdings = self.db.get_all_holdings()
        self.stocks = []
        
        for symbol, shares, avg_price, first_purchase in holdings:
            current_price = self.api.get_stock_price(symbol)
            if current_price:
                stock = Stock(
                    symbol=symbol,
                    shares=shares,
                    purchase_price=avg_price,
                    purchase_date=first_purchase,
                    current_price=current_price
                )
                self.stocks.append(stock)
                time.sleep(0.1)  # Rate limiting for API calls
        
        print("✅ Prices updated!")
    
    def display_portfolio(self):
        """Display current portfolio status"""
        if not self.stocks:
            self.update_prices()
        
        if not self.stocks:
            print("📈 Your portfolio is empty. Add some stocks to get started!")
            return
        
        print("\n" + "="*80)
        print("📊 PORTFOLIO SUMMARY")
        print("="*80)
        
        total_value = 0
        total_cost = 0
        
        print(f"{'Symbol':<8} {'Shares':<10} {'Avg Cost':<12} {'Current':<12} {'Value':<12} {'Gain/Loss':<15} {'%':<8}")
        print("-" * 80)
        
        for stock in self.stocks:
            total_value += stock.total_value
            total_cost += stock.total_cost
            
            gain_loss_str = f"${stock.gain_loss:+.2f}"
            percentage_str = f"{stock.gain_loss_percentage:+.1f}%"
            
            print(f"{stock.symbol:<8} {stock.shares:<10.2f} ${stock.purchase_price:<11.2f} "
                  f"${stock.current_price:<11.2f} ${stock.total_value:<11.2f} "
                  f"{gain_loss_str:<15} {percentage_str:<8}")
        
        print("-" * 80)
        total_gain_loss = total_value - total_cost
        total_percentage = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0
        
        print(f"{'TOTAL':<8} {'':<10} {'':<12} {'':<12} ${total_value:<11.2f} "
              f"${total_gain_loss:+.2f}       {total_percentage:+.1f}%")
        print("="*80)
    
    def display_transactions(self, symbol: str = None):
        """Display transaction history"""
        transactions = self.db.get_transactions(symbol)
        
        if not transactions:
            print("📝 No transactions found.")
            return
        
        print(f"\n📝 TRANSACTION HISTORY" + (f" - {symbol.upper()}" if symbol else ""))
        print("-" * 70)
        print(f"{'Date':<12} {'Symbol':<8} {'Type':<6} {'Shares':<10} {'Price':<12}")
        print("-" * 70)
        
        for transaction in transactions:
            _, symbol, trans_type, shares, price, trans_date, _ = transaction
            print(f"{trans_date:<12} {symbol:<8} {trans_type:<6} {shares:<10.2f} ${price:<11.2f}")
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary as dictionary"""
        if not self.stocks:
            self.update_prices()
        
        total_value = sum(stock.total_value for stock in self.stocks)
        total_cost = sum(stock.total_cost for stock in self.stocks)
        total_gain_loss = total_value - total_cost
        total_percentage = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0
        
        return {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_gain_loss': total_gain_loss,
            'total_percentage': total_percentage,
            'number_of_holdings': len(self.stocks),
            'holdings': [
                {
                    'symbol': stock.symbol,
                    'shares': stock.shares,
                    'current_price': stock.current_price,
                    'total_value': stock.total_value,
                    'gain_loss': stock.gain_loss,
                    'gain_loss_percentage': stock.gain_loss_percentage
                }
                for stock in self.stocks
            ]
        }

def main():
    """Main function to run the portfolio tracker"""
    print("🚀 Welcome to Stock Portfolio Tracker!")
    print("="*50)
    
    # Initialize portfolio tracker
    tracker = PortfolioTracker(api_key="452XSQ6WDN73XVTP")
    
    while True:
        print("\n📋 MENU:")
        print("1. Add Stock")
        print("2. Sell Stock")
        print("3. View Portfolio")
        print("4. Update Prices")
        print("5. View Transactions")
        print("6. Portfolio Summary (JSON)")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == '1':
            symbol = input("Enter stock symbol: ").strip().upper()
            try:
                shares = float(input("Enter number of shares: "))
                price = float(input("Enter purchase price per share: $"))
                date = input("Enter purchase date (YYYY-MM-DD) or press Enter for today: ").strip()
                
                if not date:
                    date = None
                
                tracker.add_stock(symbol, shares, price, date)
            except ValueError:
                print("❌ Invalid input. Please enter valid numbers.")
        
        elif choice == '2':
            symbol = input("Enter stock symbol to sell: ").strip().upper()
            try:
                shares = float(input("Enter number of shares to sell: "))
                price_input = input("Enter sale price per share (or press Enter for current price): $").strip()
                
                sale_price = float(price_input) if price_input else None
                tracker.remove_stock(symbol, shares, sale_price)
            except ValueError:
                print("❌ Invalid input. Please enter valid numbers.")
        
        elif choice == '3':
            tracker.display_portfolio()
        
        elif choice == '4':
            tracker.update_prices()
        
        elif choice == '5':
            symbol = input("Enter stock symbol (or press Enter for all transactions): ").strip()
            tracker.display_transactions(symbol if symbol else None)
        
        elif choice == '6':
            summary = tracker.get_portfolio_summary()
            print("\n📊 Portfolio Summary (JSON):")
            print(json.dumps(summary, indent=2))
        
        elif choice == '7':
            print("👋 Thank you for using Stock Portfolio Tracker!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-7.")

if __name__ == "__main__":
    main()