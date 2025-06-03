import requests
import json
from datetime import datetime

class SimplePortfolio:
    def __init__(self):
        # Store portfolio as a simple dictionary
        self.stocks = {}  
        
    def add_stock(self, symbol, shares, buy_price):
        
        symbol = symbol.upper()
        
        if symbol in self.stocks:
            # If stock exists, calculate average price
            old_shares = self.stocks[symbol]['shares']
            old_price = self.stocks[symbol]['buy_price']
            
            total_cost = (old_shares * old_price) + (shares * buy_price)
            total_shares = old_shares + shares
            avg_price = total_cost / total_shares
            
            self.stocks[symbol] = {'shares': total_shares, 'buy_price': avg_price}
        else:
            self.stocks[symbol] = {'shares': shares, 'buy_price': buy_price}
        
        print(f"✅ Added {shares} shares of {symbol} at ${buy_price}")
    
    def remove_stock(self, symbol):
        symbol = symbol.upper()
        if symbol in self.stocks:
            del self.stocks[symbol]
            print(f"✅ Removed {symbol} from portfolio")
        else:
            print(f"❌ {symbol} not found in portfolio")
    
    def get_current_price(self, symbol):
        try:
            # Using a free API 
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token=demo"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if 'c' in data and data['c'] > 0:
                return data['c']  # current price
            else:
                # Fallback demo prices
                demo_prices = {
                    'AAPL': 175.50, 'GOOGL': 140.25, 'MSFT': 350.80,
                    'TSLA': 225.30, 'AMZN': 145.60, 'NVDA': 875.20
                }
                return demo_prices.get(symbol, 100.0)
        except:
            # If API fails, return demo price
            return 100.0
    
    def show_portfolio(self):
        """Display the portfolio"""
        if not self.stocks:
            print("📈 Your portfolio is empty!")
            return
        
        print("\n" + "="*60)
        print("📊 YOUR PORTFOLIO")
        print("="*60)
        print(f"{'Stock':<8} {'Shares':<8} {'Buy Price':<12} {'Current':<12} {'Profit/Loss':<12}")
        print("-"*60)
        
        total_value = 0
        total_cost = 0
        
        for symbol, data in self.stocks.items():
            shares = data['shares']
            buy_price = data['buy_price']
            current_price = self.get_current_price(symbol)
            
            cost = shares * buy_price
            value = shares * current_price
            profit_loss = value - cost
            
            total_cost += cost
            total_value += value
            
            print(f"{symbol:<8} {shares:<8.1f} ${buy_price:<11.2f} ${current_price:<11.2f} ${profit_loss:<11.2f}")
        
        print("-"*60)
        total_profit_loss = total_value - total_cost
        print(f"TOTAL: Cost=${total_cost:.2f} | Value=${total_value:.2f} | Profit/Loss=${total_profit_loss:.2f}")
        print("="*60)

def main():
    """Main function to run the portfolio tracker"""
    print("🚀 Simple Stock Portfolio Tracker")
    print("="*40)
    
    portfolio = SimplePortfolio()
    
    while True:
        print("\n📋 What would you like to do?")
        print("1. Add Stock")
        print("2. Remove Stock") 
        print("3. View Portfolio")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            symbol = input("Stock symbol (e.g., AAPL): ").strip()
            try:
                shares = float(input("Number of shares: "))
                price = float(input("Price you bought at: $"))
                portfolio.add_stock(symbol, shares, price)
            except ValueError:
                print("❌ Please enter valid numbers")
        
        elif choice == '2':
            symbol = input("Stock symbol to remove: ").strip()
            portfolio.remove_stock(symbol)
        
        elif choice == '3':
            portfolio.show_portfolio()
        
        elif choice == '4':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Please enter 1, 2, 3, or 4")

if __name__ == "__main__":
    main()