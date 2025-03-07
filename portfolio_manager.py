import yfinance as yf
import mysql.connector
# import numpy as np
# import pandas as pd
from finta import TA
import warnings

warnings.filterwarnings("ignore", message="The 'unit' keyword in TimedeltaIndex construction is deprecated and will be removed in a future version")


# Step 1: Database Setup
conn = mysql.connector.connect(
    host="localhost",
    user="avensun",
    password="Aven890831@@",
    database="DSCI560"
)

cursor = conn.cursor()

# Step 2: Define Database Tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS past_stocks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(10),
        date DATE,
        open FLOAT,
        high FLOAT,
        low FLOAT,
        close FLOAT,
        volume INT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS portfolios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) UNIQUE NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS portfolio_stocks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        portfolio_id INT,
        symbol VARCHAR(10),
        FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS real_time_stocks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(10),
        datetime DATETIME,
        open INT,
        high INT,
        low INT,
        close INT,
        volume INT,
        SMA FLOAT,
        RSI FLOAT,
        OBV FLOAT,
        MACD FLOAT,
        `SIGNAL` FLOAT
    )
''')


# Step 3: Fetch and Store Stock Data
def fetch_and_store_stock_data(symbol, start_date, end_date, cursor):
    if not validate_stock_symbol(symbol):
        print(f"Invalid stock symbol: {symbol}")
        return

    data = yf.download(symbol, start=start_date, end=end_date)
    data.reset_index(inplace=True)

    for _, row in data.iterrows():
        formatted_date = row['Date'].strftime('%Y-%m-%d')
        cursor.execute(
            "INSERT IGNORE INTO past_stocks (symbol, date, open, high, low, close, volume) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (symbol, formatted_date, row['Open'], row['High'], row['Low'], row['Close'], row['Volume'])
        )

    conn.commit()


# Step 4: User Input
def create_portfolio(name):
    cursor.execute("INSERT INTO portfolios (name) VALUES (%s)", (name,))
    conn.commit()


def add_stocks_to_portfolio(portfolio_name, symbols):
    cursor.execute("SELECT id FROM portfolios WHERE name = %s LIMIT 1", (portfolio_name,))
    portfolio_id = cursor.fetchone()

    if not portfolio_id:
        print(f"Portfolio not found: {portfolio_name}")
        return

    for s in symbols:
        cursor.execute("SELECT symbol FROM real_time_stocks WHERE symbol = %s LIMIT 1", (s,))
        stock_symbol = cursor.fetchone()
        if not stock_symbol:
            print(f"Invalid stock symbol: {s}")
        else:
            cursor.execute("INSERT INTO portfolio_stocks (portfolio_id, symbol) VALUES (%s, %s)", (portfolio_id[0], stock_symbol[0],))
            print(f"Added {s} to portfolio.")

    conn.commit()


# Step 5: User Options
def display_portfolios():
    cursor.execute("SELECT * FROM portfolios")
    portfolios = cursor.fetchall()
    for portfolio in portfolios:
        print(f"Portfolio ID: {portfolio[0]} | Name: {portfolio[1]}")


def add_stock_to_portfolio(portfolio_name, symbol, start_date, end_date):
    cursor.execute("SELECT id FROM portfolios WHERE name = %s LIMIT 1", (portfolio_name,))
    portfolio_id = cursor.fetchone()

    if not portfolio_id:
        print(f"Portfolio not found: {portfolio_name}")
        return

    if not validate_stock_symbol(symbol):
        print(f"Invalid stock symbol: {symbol}")
        return

    fetch_and_store_stock_data(symbol, start_date, end_date, cursor)
    cursor.execute("SELECT symbol FROM past_stocks WHERE symbol = %s LIMIT 1", (symbol,))
    stock_symbol = cursor.fetchone()
    cursor.execute("INSERT IGNORE INTO portfolio_stocks (portfolio_id, symbol) VALUES (%s, %s)", (portfolio_id[0], stock_symbol[0]))
    conn.commit()
    print(f"Added {symbol} to portfolio.")


def remove_stock_from_portfolio(portfolio_name, symbol):
    cursor.execute("SELECT id FROM portfolios WHERE name = %s LIMIT 1", (portfolio_name,))
    portfolio_id = cursor.fetchone()

    if not portfolio_id:
        print(f"Portfolio not found: {portfolio_name}")
        return

    if not validate_stock_symbol(symbol):
        print(f"Invalid stock symbol: {symbol}")
        return

    cursor.execute("DELETE FROM portfolio_stocks WHERE portfolio_id = %s AND symbol = %s", (portfolio_id[0], symbol))
    conn.commit()
    print(f"Removed {symbol} from portfolio.")


def display_portfolio_details(portfolios_name):
    cursor.execute("SELECT portfolios.name, GROUP_CONCAT(DISTINCT ps.symbol) as stocks "
                   "FROM portfolios "
                   "LEFT JOIN portfolio_stocks ps ON portfolios.id = ps.portfolio_id "
                   "WHERE portfolios.name = %s "
                   "GROUP BY portfolios.name", (portfolios_name,))
    portfolios = cursor.fetchall()
    for portfolio in portfolios:
        print(f"Portfolio Name: {portfolio[0]}")
        print(f"Stocks in Portfolio: {portfolio[1]}\n")


def validate_stock_symbol(symbol):
    symbol = symbol.strip()
    if not symbol:
        return False

    # Check if the symbol is available on yfinance
    try:
        yf.Ticker(symbol).info
        return True
    except:
        return False


# Step 6: Collect & Storing Real Time Data & Cleaning Dataset
def collect_and_store(tickers, period='10d', interval='5m'):
    if isinstance(tickers, str):
        tickers = [tickers]  # Convert a single ticker string into a list

    data = yf.download(tickers=tickers, period=period, interval=interval, group_by='ticker')

    for ticker in tickers:
        if len(tickers) > 1:
            ticker_data = data[ticker].reset_index()
        else:
            ticker_data = data.reset_index()  # Single ticker, no multi-level DataFrame

        ticker_data['SMA'] = TA.SMA(ticker_data, 15)
        ticker_data['RSI'] = TA.RSI(ticker_data)
        ticker_data['OBV'] = TA.OBV(ticker_data)
        ticker_data[['MACD', 'SIGNAL']] = TA.MACD(ticker_data)

        ticker_data = ticker_data.fillna(0)
        store_real_time_data(ticker, ticker_data)

def store_real_time_data(ticker, data):
    for _, row in data.iterrows():
        datetime_str = row['Datetime'].strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT IGNORE INTO real_time_stocks (symbol, datetime, open, high, low, close, volume, SMA, RSI, OBV, MACD, `SIGNAL`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (ticker, datetime_str, row['Open'], row['High'], row['Low'], row['Close'], row['Volume'], row['SMA'], row['RSI'], row['OBV'], row['MACD'], row['SIGNAL'])
        )
    conn.commit()

def main_part1():
    # Step 7: Manage Portfolio
    while True:
        print("-----------------------------------------")
        print("Portfolio Management Menu:")
        print("0. Create Portfolio")
        print("1. Add Stock to Portfolio")
        print("2. Remove Stock from Portfolio")
        print("3. Display Portfolio Details")
        print("4. Select Date Range")
        print("5. Quit")
        choice = input("Enter your choice (0/1/2/3/4/5): ")
        print("-----------------------------------------")
        print("")

        if choice == '0':
            name = input("Please Enter Your Desire Portfolio Name: ")
            create_portfolio(name)
            symbols = input("Enter stock symbols separated by commas (e.g., AAPL, MSFT): ")
            symbols = [x.strip() for x in symbols.split(",")]
            collect_and_store(symbols)
            add_stocks_to_portfolio(name, symbols)
            display_portfolios()
        elif choice == '1':
            portfolio_name = input("Enter the portfolio name: ")
            symbols = input("Enter stock symbols separated by commas (e.g., AAPL, MSFT): ")
            symbols = [x.strip() for x in symbols.split(",")]
            collect_and_store(symbols)
            add_stocks_to_portfolio(portfolio_name, symbols)
        elif choice == '2':
            portfolio_name = input("Enter the portfolio name: ")
            symbol = input("Enter the stock symbol to remove: ")
            remove_stock_from_portfolio(portfolio_name, symbol)
        elif choice == '3':
            portfolio_name = input("Enter the portfolio name: ")
            display_portfolio_details(portfolio_name)
        elif choice == '4':
            portfolio_name = input("Enter the portfolio name: ")
            symbol = input("Enter the stock symbol: ")
            start_date = input("Enter start date (YYYY-MM-DD): ")
            end_date = input("Enter end date (YYYY-MM-DD): ")
            add_stock_to_portfolio(portfolio_name, symbol, start_date, end_date)
        elif choice == '5':
            break
        else:
            print("Invalid choice. Please enter a valid option.")


if __name__ == "__main__":
    main_part1()
    conn.close()
# Close the database connection when done


