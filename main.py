import yfinance as yf
import os
import csv
import pandas as pd
import matplotlib.pyplot as plt
import requests

def ensure_output_dir():
    if not os.path.exists('output'):
        os.makedirs('output')

class Stock:
    def __init__(self, ticker):
        self.quantity = None
        self.symbol = ticker.upper()
        self.ticker = yf.Ticker(self.symbol)
        self.data = None

    def get_data(self, period="1mo", interval="1d", refresh=False):
        if self.data is None or refresh:
            try:
                self.data = self.ticker.history(period=period, interval=interval)
            except Exception as e:
                print(f"Error fetching data for {self.symbol}: {e}")
                return None
        return self.data

    def get_price(self):
        data = self.get_data()
        if data is None or data.empty:
            return None
        try:
            price = data['Close'].iloc[-1]
        except Exception as e:
            print(f"Error fetching price for {self.symbol}: {e}")
            return None
        return price

    def get_value(self):
        return self.get_price() * self.quantity

    def get_daily_change_percent(self):
        data = self.get_data()
        # We need at least two days of data to compare today vs yesterday
        if data is None or len(data) < 2:
            return None
        try:
            yesterday_close = data['Close'].iloc[-2]
            today_close = data['Close'].iloc[-1]

            # Calculate percentage change
            change_percent = ((today_close - yesterday_close) / yesterday_close) * 100
            return change_percent
        except Exception as e:
            print(f"Error calculating daily change for {self.symbol}: {e}")
            return None

    def plot_history(self):
        data = self.get_data()
        if data is None:
            return None
        print(data.head())
        sma_5 = data['Close'].rolling(window=5).mean()
        # print days where the close price is greater than the 5-day SMA
        buy_signals = data['Close'] > sma_5
        plot_signals = data[buy_signals]
        print("Buy signals:")
        print(data[buy_signals])
        # Graphing
        plt.figure(figsize=(10, 10))
        plt.plot(data['Close'], label='Price', color='blue')
        plt.plot(sma_5, label='5-day SMA', color='red')
        plt.scatter(plot_signals.index, plot_signals['Close'], color='green', label='Buy Signals', marker='^', zorder=3)
        plt.title(f'{self.symbol} Price History')
        plt.xlabel('Date')
        plt.xticks(rotation=45)
        plt.ylabel('Price ($)')
        plt.legend()
        # Save instead of blocking GUI show to avoid macOS backend hang
        plt.tight_layout()
        ensure_output_dir()
        out_path = os.path.join('output', f"{self.symbol}_history.png")
        plt.savefig(out_path)
        plt.close()
        print(f"Saved history chart to '{out_path}'.")

class Portfolio:
    def __init__(self):
        self.stocks = {}
        # Load the existing portfolio if available
        if os.path.exists('output/portfolio.csv'):
            try:
                with open('output/portfolio.csv', 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        ticker = row['Ticker']
                        qty = int(row['Quantity'])

                        stock = Stock(ticker)
                        stock.quantity = qty
                        self.stocks[ticker] = stock
                print(f"Loaded {len(self.stocks)} stocks from portfolio.csv")
            except Exception as e:
                print(f"Error loading portfolio: {e}")

    def __str__(self):
        result = "Portfolio Holdings:\n"
        # Added 'Change %' to the header
        result += f"{'Ticker':<10} {'Price':<10} {'Change %':<10} {'Qty':<10} {'Value':<10}\n"
        result += "-" * 52 + "\n"

        for ticker, stock in self.stocks.items():
            price = stock.get_price()
            qty = stock.quantity
            change = stock.get_daily_change_percent()

            if price is not None and qty is not None:
                value = price * qty

                # Format the change string (e.g., +1.25% or -0.50%)
                if change is not None:
                    # The '+' forces a plus sign for positive numbers
                    change_str = f"{change:>+7.2f}%"
                else:
                    change_str = "N/A"

                result += f"{ticker:<10} ${price:<9.2f} {change_str:<10} {qty:<10} ${value:.2f}\n"
            else:
                result += f"{ticker}: Error (Price: {price}, Qty: {qty})\n"
        return result

    def add_stock(self, ticker, quantity):
        if ticker in self.stocks:
            print(f"Stock {ticker} is already in portfolio.")
            return

        print(f"Validating {ticker}...")
        new_stock = Stock(ticker)

        # The Bouncer: Check if we can actually get a price
        if new_stock.get_price() is None:
            print(f"Error: '{ticker}' appears to be an invalid ticker symbol.")
        else:
            self.stocks[ticker] = new_stock
            new_stock.quantity = quantity
            print(f"Added {ticker} to portfolio.")

    def remove_stock(self, ticker):
        if ticker in self.stocks:
            self.stocks.pop(ticker)
            print(f"Removed stock {ticker} from portfolio")
        else:
            print(f"Stock {ticker} is not in portfolio")

    def save_to_csv(self):
        ensure_output_dir()
        with open('output/portfolio.csv', 'w', newline='') as csvfile:
            fieldnames = ['Ticker', 'Quantity']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for ticker, stock in self.stocks.items():
                writer.writerow({'Ticker': ticker, 'Quantity': stock.quantity})
        print(f"Saved portfolio to 'output/portfolio.csv'")

    def generate_chart(self):
        if not self.stocks:
            print("No stocks in portfolio to generate chart for.")
            return
        try:
            valid_stocks = []
            for ticker, stock in self.stocks.items():
                price = stock.get_price()
                if price is not None:
                    valid_stocks.append((ticker, price))
            sorted_stocks = sorted(valid_stocks, key=lambda x: x[1], reverse=True)
            top5 = sorted_stocks[:5]
            tickers = [stock[0] for stock in top5]
            prices = [stock[1] for stock in top5]
            plt.bar(tickers, prices, color='blue', width=0.5, align='center')
            plt.xlabel('Stock Ticker')
            plt.ylabel('Price in USD ($)')
            plt.title('Stock Price Watchlist')
            # display the graph (save instead of show to avoid GUI backend blocking)
            plt.tight_layout()
            ensure_output_dir()
            plt.savefig('output/chart.png')
            plt.close()
            print("Saved bar chart to 'output/chart.png'.")
        except Exception as e:
            print(f"Error generating chart: {e}")

    def get_total_value(self):
        total_value = sum(stock.get_value() for stock in self.stocks.values())
        return total_value

def main():
    portfolio = Portfolio()
    # enter stock ticker
    print("Welcome to the Alpha Dashboard!")
    print("===============================")
    while True:
        user_choice = input("What would you like to do? (add, remove, view, history, chart, exit): ")
        if user_choice.lower() not in ['add', 'remove', 'view', 'history', 'chart', 'exit', 'e', 'q']:
            print("Invalid choice. Please select from the available options.")
            continue
        match user_choice.lower():
            case "add":
                user_input = input("Enter ticker: ").upper().strip()
                quantity = int(input("Enter quantity: "))
                portfolio.add_stock(user_input, quantity)
            case "remove":
                user_input = input("Enter ticker to remove: ").upper().strip()
                portfolio.remove_stock(user_input)
            case "view":
                print(portfolio)  # No ticker needed!
            case "history":
                user_input = input("Enter ticker: ").upper().strip()
                # Does it already exist in portfolio?
                if user_input in portfolio.stocks:
                    portfolio.stocks[user_input].plot_history()  # Reuse existing
                else:
                    stock = Stock(user_input)  # Only create new if necessary
                    stock.plot_history()
            case "chart":
                portfolio.generate_chart()
            case "exit" | "e" | "q":
                print("Thank you for using this stock checker.")
                portfolio.save_to_csv()
                portfolio.generate_chart()
                break
if __name__ == "__main__":
    main()