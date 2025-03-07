Stock Portfolio Management and Trading Algorithm
This project implements a stock portfolio management system with a trading algorithm that utilizes various technical indicators such as Moving Averages, RSI, MACD, and ARIMA-based predictions to guide buy and sell decisions. The application integrates with both Yahoo Finance and a MySQL database for storing and managing stock data, simulating a mock trading environment based on historical stock data.

Features
1. Portfolio Management
Create, display, and manage stock portfolios.
Add or remove stocks to/from portfolios.
Store real-time stock data and historical data for analysis.
View portfolio details including stock symbols and their respective data.
2. Technical Analysis & Trading Strategy
The trading strategy is based on several well-known technical indicators:

SMA (Simple Moving Average): Compares short-term and long-term price trends.
RSI (Relative Strength Index): Signals overbought or oversold conditions in the market.
OBV (On-Balance Volume): Measures buying and selling pressure based on volume.
MACD (Moving Average Convergence Divergence): Helps identify trends and potential reversals.
ARIMA: Forecasting future prices and trends based on time-series analysis.
The strategy combines these indicators using a weighted voting system, which triggers buy and sell signals based on the overall market sentiment.

3. ARIMA Forecasting
ARIMA (AutoRegressive Integrated Moving Average) is used to predict stock prices for the next 15 days. The slope of the ARIMA forecast is used as a signal:

Positive slope → Buy Signal
Negative slope → Sell Signal
4. Sharpe Ratio Calculation
The program ranks stocks based on their Sharpe Ratio, which is used to measure risk-adjusted returns. Stocks with a higher Sharpe ratio are preferred in the portfolio.

Project Setup
Requirements
Python 3.x
MySQL Server
Libraries: yfinance, mysql.connector, pandas, finta, matplotlib, pmdarima, numpy
