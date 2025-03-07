import yfinance as yf
import mysql.connector
import pandas as pd
from finta import TA
import warnings
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pmdarima.arima import auto_arima
import matplotlib.dates as mdates

warnings.filterwarnings("ignore",
                        message="The 'unit' keyword in TimedeltaIndex construction is deprecated and will be removed in a future version")

# Initialize Cash Balance
initial_budget = float(input("Enter Your Initial Budget: "))

# Database Setup (Same as Part 1)
conn = mysql.connector.connect(
    host="localhost",
    user="avensun",
    password="Aven890831@@",
    database="DSCI560"
)
cursor = conn.cursor()

# Define Algorithm Parameters
short_window = 50  # Short moving average window
long_window = 200  # Long moving average window


# ARIMA Model
def arima_forecast(series, start_date):
    historical_start_date = start_date - timedelta(days=150)
    historical_data = series.loc[historical_start_date:start_date]
    model_autoARIMA = auto_arima(historical_data, start_p=1, start_q=1,
                                 test='adf',  # use adf-test to find optimal 'd'
                                 max_p=3, max_q=3,  # maximum p and q
                                 m=1,  # frequency of series
                                 d=None,  # let model determine 'd'
                                 seasonal=True,  # Seasonal model
                                 start_P=0,
                                 D=2,
                                 trace=False,
                                 error_action='ignore',
                                 suppress_warnings=True,
                                 stepwise=True)
    forecast, conf_int = model_autoARIMA.predict(n_periods=15, return_conf_int=True)
    return forecast, conf_int


# Helper function to calculate slope
def calculate_slope(forecast, periods=15):
    y1 = forecast.iloc[0] if isinstance(forecast, pd.Series) else forecast[0]
    y2 = forecast.iloc[-1] if isinstance(forecast, pd.Series) else forecast[-1]
    x1, x2 = 0, periods - 1
    return (y2 - y1) / (x2 - x1)


def arima_forecast_with_slope(series, start_date, periods=15):
    forecast, conf_int = arima_forecast(series, start_date)
    slope = calculate_slope(forecast, periods)
    return forecast, conf_int, slope


# MACD
def calculate_macd(data, short_window=12, long_window=26, signal_window=9):
    # Calculate the short and long EMAs
    data['EMA_short'] = data['close'].ewm(span=short_window, adjust=False).mean()
    data['EMA_long'] = data['close'].ewm(span=long_window, adjust=False).mean()

    # Calculate the MACD line
    data['MACD'] = data['EMA_short'] - data['EMA_long']

    # Calculate the signal line
    data['Signal_Line'] = data['MACD'].ewm(span=signal_window, adjust=False).mean()

    # Calculate the MACD histogram
    data['MACD_Histogram'] = data['MACD'] - data['Signal_Line']


def strategies(data, start_date, end_date):
    position = 0
    buy_signals = []
    sell_signals = []
    arima_predictions = []
    signals = []  # Initialize an empty list to store final signals

    # Calculate additional indicators if not already present
    if 'SMA' not in data.columns:
        data['SMA_Short'] = data['close'].rolling(window=short_window).mean()
        data['SMA_Long'] = data['close'].rolling(window=long_window).mean()
    if 'RSI' not in data.columns:
        data['RSI'] = TA.RSI(data, 14)
    if 'OBV' not in data.columns:
        data['OBV'] = TA.OBV(data)

    # Calculate MACD
    calculate_macd(data)

    # Initialize signal columns
    data['SMA_signal'] = 0
    data['RSI_signal'] = 0
    data['OBV_signal'] = 0
    data['MACD_signal'] = 0
    data['ARIMA_signal'] = 0

    # Generate signals based on conditions
    data.loc[data['SMA_Short'] > data['SMA_Long'], 'SMA_signal'] = 1
    data.loc[data['SMA_Short'] < data['SMA_Long'], 'SMA_signal'] = -1
    data.loc[data['RSI'] < 30, 'RSI_signal'] = 1
    data.loc[data['RSI'] > 70, 'RSI_signal'] = -1
    data.loc[data['OBV'] > data['OBV'].ewm(span=20).mean(), 'OBV_signal'] = 1
    data.loc[data['OBV'] < data['OBV'].ewm(span=20).mean(), 'OBV_signal'] = -1
    data.loc[data['MACD'] > data['Signal_Line'], 'MACD_signal'] = 1
    data.loc[data['MACD'] < data['Signal_Line'], 'MACD_signal'] = -1

    data['date'] = pd.to_datetime(data['date'])
    data.set_index('date', inplace=True)
    data.index = pd.DatetimeIndex(data.index).to_period('D')

    # Filter the data to only include the date range for generating signals
    data_for_signals = data[start_date:end_date].copy()

    # Iterate over the data in steps of 15 days for ARIMA
    for i in range(0, len(data_for_signals), 15):
        forecast, conf_int, slope = arima_forecast_with_slope(data['close'], data_for_signals.index[i])
        arima_predictions.append((data_for_signals.index[i], forecast, conf_int))
        data_for_signals['ARIMA_slope'] = slope

        # Use the slope as a signal (e.g., if the slope is higher than a threshold, it might indicate an uptrend)
        slope_signal = 1 if slope > 0 else -1 if slope < 0 else 0

        # Include your slope_signal logic here, for example:
        if slope_signal == 1:
            data_for_signals['ARIMA_signal'] = 1
        elif slope_signal == -1:
            data_for_signals['ARIMA_signal'] = -1
        else:
            data_for_signals['ARIMA_signal'] = 0

    # Implement voting system
    data_for_signals = implement_weighted_voting_system(data_for_signals)

    # Determine final action
    for i, signal in enumerate(data_for_signals['final_signal']):
        if signal > 0:
            if position != 1:
                signals.append(1)  # Buy signal
                buy_signals.append((data_for_signals.index[i], data_for_signals['close'].iloc[i]))
                position = 1
            else:
                signals.append(0)
        elif signal < 0:
            if position != -1:
                signals.append(-1)  # Sell
                sell_signals.append((data_for_signals.index[i], data_for_signals['close'].iloc[i]))
                position = -1
            else:
                signals.append(0)
        else:
            signals.append(0)  # No action
    print(data_for_signals[['SMA_signal', 'RSI_signal', 'OBV_signal', 'MACD_signal', 'ARIMA_signal', 'weighted_score', 'final_signal']])
    return signals, arima_predictions, buy_signals, sell_signals


def implement_weighted_voting_system(data):
    # Define weights for each signal
    weights = {
        'SMA_signal': 0.2,
        'RSI_signal': 0.2,
        'OBV_signal': 0.2,
        'MACD_signal': 0.2,
        'ARIMA_signal': 0.2
    }

    # Calculate weighted score for each type of signal
    data['weighted_score'] = data['SMA_signal'] * weights['SMA_signal'] + \
                             data['RSI_signal'] * weights['RSI_signal'] + \
                             data['OBV_signal'] * weights['OBV_signal'] + \
                             data['MACD_signal'] * weights['MACD_signal'] + \
                             data['ARIMA_signal'] * weights['ARIMA_signal']

    # Initialize the final_signal column to 0 (no action) by default
    data['final_signal'] = 0

    # Generate a buy signal (1) if the weighted score of buy signals exceeds 50%
    data.loc[data['weighted_score'] > 0.3, 'final_signal'] = 1
    data.loc[data['weighted_score'] < -0.15, 'final_signal'] = -1
    return data


# sharp ratio
def sharp_ratio(symbols, start_date):
    risk_free_rate = 0.01

    # Subtract one year from the start_date
    historical_start_date = start_date - timedelta(days=365)

    # Fetch historical data
    data = yf.download(symbols, start=historical_start_date, end=start_date)['Adj Close']

    # Calculate daily returns
    returns = data.pct_change().dropna()

    # Calculate average returns and volatility
    avg_returns = returns.mean() * 252  # Annualized
    volatility = returns.std() * (252 ** 0.5)  # Annualized

    # Calculate Sharpe Ratios
    sharpe_ratios = (avg_returns - risk_free_rate) / volatility

    # Rank stocks based on Sharpe Ratio and select top 50%
    top_50_percent = len(symbols) // 2
    top_stocks = sharpe_ratios.nlargest(top_50_percent).index.tolist()

    # Create a DataFrame for Sharpe Ratios
    # Create and sort the DataFrame by Sharpe Ratio in descending order
    sharpe_ratio_df = pd.DataFrame(sharpe_ratios, columns=['Sharpe Ratio'])
    sharpe_ratio_df = sharpe_ratio_df.sort_values('Sharpe Ratio', ascending=False)
    print(sharpe_ratio_df)

    return top_stocks


def plot_all_predictions(data, buy_signals, sell_signals, arima_predictions, symbol):
    # Plot the actual closing prices
    plt.figure(figsize=(14, 7))
    if isinstance(data.index, pd.PeriodIndex):
        data.index = data.index.to_timestamp()
    plt.plot(data.index, data['close'], label='Actual Close', color='blue', alpha=0.6)

    # # Plot each ARIMA forecast and confidence interval
    for prediction in arima_predictions:
        buy_signal_date = prediction[0]
        forecast = prediction[1]
        conf_int = prediction[2]
        forecast_dates = [buy_signal_date + timedelta(days=x) for x in range(1, len(forecast) + 1)]

        plt.plot(forecast_dates, forecast, color='red')
        plt.fill_between(forecast_dates, conf_int[:, 0], conf_int[:, 1], color='pink', alpha=0.3)

    # Create a labeled plot entry for buy signals for legend purposes
    plt.scatter([], [], label='Buy Signal', marker='^', color='green', alpha=1)

    # Create a labeled plot entry for sell signals for legend purposes
    plt.scatter([], [], label='Sell Signal', marker='v', color='red', alpha=1)

    for buy_date, buy_price in buy_signals:
        plt.scatter(buy_date, buy_price, marker='^', color='green', alpha=1)

    for sell_date, sell_price in sell_signals:
        plt.scatter(sell_date, sell_price, marker='v', color='red', alpha=1)

    plt.title(f'{symbol} Stock Price, Buy Signals and ARIMA Predictions')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.show()


# Mock Trading Environment
def mock_trading(portfolio_id, portfolio_name, start_date, end_date):
    cursor.execute("SELECT DISTINCT symbol FROM portfolio_stocks WHERE portfolio_id = %s", (portfolio_id,))
    symbols = [row[0] for row in cursor.fetchall()]

    # Calculate two years before the start_date
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    historical_start_date = start_date - timedelta(days=2 * 365)

    # pick the best stocks best on sharp-ratio
    top_stocks = sharp_ratio(symbols, start_date)

    # Initialize portfolio
    portfolio = {symbol: 0 for symbol in symbols}
    cash_balance = initial_budget  # Initial investment fund

    # Fetch and process stock data
    for symbol in top_stocks:
        # Reset buy_points and sell_points for each symbol
        buy_points = {'dates': [], 'prices': []}
        sell_points = {'dates': [], 'prices': []}

        # Fetch stock data directly from yfinance
        stock_data = yf.download(symbol, start=historical_start_date.strftime('%Y-%m-%d'), end=end_date)
        # Prepare data for analysis and trading
        data = stock_data[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']].copy()
        data['date'] = data.index
        data.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Adj Close': 'adj close',
                             'Volume': 'volume'}, inplace=True)

        # Switch between different algorithms
        signals, arima_predictions, buy_signals, sell_signals = strategies(data, start_date, end_date)

        data_for_signals = data[start_date:end_date].copy()

        # main calculation loop
        for i in range(len(data_for_signals)):
            if signals[i] == 1:  # Buy signal
                if cash_balance > data_for_signals['close'].iloc[i]:
                    shares_to_buy = (cash_balance * 0.2) // data_for_signals['close'].iloc[i]  # Only use 20 percent of current balance
                    portfolio[symbol] += shares_to_buy
                    cash_balance -= shares_to_buy * data_for_signals['close'].iloc[i]
                    buy_points['dates'].append(data_for_signals.index[i])
                    buy_points['prices'].append(data_for_signals.index[i])

                    # print the buy result
                    print(f"\n------------------------------------------------")
                    print("Company:", symbol)
                    print("Date of the buy transaction:", data_for_signals.index[i])
                    print("Number of shares:", shares_to_buy)
                    print("Balance:", cash_balance)
                    print(f"------------------------------------------------\n")
            elif signals[i] == -1:  # Sell signal
                if portfolio[symbol] > 0:
                    cash_balance += portfolio[symbol] * data_for_signals['close'].iloc[i]
                    portfolio[symbol] = 0
                    sell_points['dates'].append(data_for_signals.index[i])
                    sell_points['prices'].append(data_for_signals['close'].iloc[i])

                    # print the sell result
                    print(f"\n------------------------------------------------")
                    print("Company:", symbol)
                    print("Date of the sell transaction:", data_for_signals.index[i])
                    print("Balance:", cash_balance)
                    print(f"------------------------------------------------\n")

        # At the end, plot all the signals and predictions for the symbol
        plot_all_predictions(data_for_signals, buy_signals, sell_signals, arima_predictions, symbol)

    # Calculate portfolio value and performance metrics
    portfolio_value = cash_balance + sum([portfolio[symbol] * data_for_signals['close'].iloc[-1] for symbol in symbols])
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    days_between_start_and_end = (end_date - start_date).days
    annualized_return = ((portfolio_value / initial_budget) ** (365.0 / days_between_start_and_end) - 1) * 100

    # Display results
    print(f"Portfolio Name: {portfolio_name}")
    print(f"Total Portfolio Value: ${portfolio_value:.2f}")
    print(f"Annualized Return: {annualized_return:.2f}%")


# Main function (Part 2)
def main_part2():
    portfolio_name = input("Enter the portfolio name: ")
    start_date = input("Enter start date (YYYY-MM-DD): ")
    end_date = input("Enter end date (YYYY-MM-DD): ")

    # Ensure portfolio exists
    cursor.execute("SELECT id FROM portfolios WHERE name = %s LIMIT 1", (portfolio_name,))
    portfolio_id = cursor.fetchone()

    if not portfolio_id:
        print(f"Portfolio not found: {portfolio_name}")
        return

    # Run mock trading environment
    mock_trading(portfolio_id[0], portfolio_name, start_date, end_date)


if __name__ == "__main__":
    main_part2()
    conn.close()
