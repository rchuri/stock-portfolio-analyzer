import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from fuzzywuzzy import process

# Add "Project by: Rohit Churi" with LinkedIn profile link
st.markdown(
    """
    <div style="text-align: right;">
        <small>Project by: <a href="https://www.linkedin.com/in/rohit-churi/" target="_blank">Rohit Churi</a></small>
    </div>
    """,
    unsafe_allow_html=True,
)

# Load tickers from the CSV file
st.session_state.sym = pd.read_csv("stocks.csv")
st.session_state.sym.columns = [
    column.replace(" ", "_") for column in st.session_state.sym.columns
]
tickers = [
    symbol + ".NS" for symbol in st.session_state.sym["SYMBOL"].tolist()
]  # Append '.NS' to each ticker


# Function to suggest tickers based on input
def get_ticker_suggestions(input_ticker, symbols, limit=5):
    suggestions = process.extract(input_ticker, symbols, limit=limit)
    return [s[0] for s in suggestions]


# Layout: Stock Portfolio Input at the top
st.title("Stock Portfolio Input")

# Initialize session state for portfolio data
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []
    st.session_state.total_investment = 0

# Input for Ticker, Purchase Date, Avg Price, and Invested Amount
if len(st.session_state.portfolio) < 10:
    input_ticker = st.text_input("Start typing a ticker:")

    # Provide suggestions based on input
    suggested_tickers = get_ticker_suggestions(input_ticker, tickers)
    ticker = st.selectbox(
        "Select the ticker:", suggested_tickers, index=0 if suggested_tickers else None
    )

    purchase_date = st.date_input("Purchase Date")
    avg_price = st.number_input("Average Purchase Price", min_value=0.0, step=0.01)
    invested_amount = st.number_input("Invested Amount", min_value=0.0, step=0.01)

    # Add stock to the portfolio
    if st.button("Add Stock"):
        if ticker and purchase_date and avg_price > 0 and invested_amount > 0:
            try:
                stock_data = yf.download(
                    ticker, start=purchase_date.strftime("%Y-%m-%d")
                )
                if not stock_data.empty:
                    stock_info = yf.Ticker(ticker).info
                    sector = stock_info.get("sector", "Unknown")

                    # Add stock to portfolio
                    st.session_state.portfolio.append(
                        {
                            "ticker": ticker,
                            "purchase_date": purchase_date,
                            "avg_price": avg_price,
                            "invested_amount": invested_amount,
                            "sector": sector,
                        }
                    )

                    # Update total investment
                    st.session_state.total_investment += invested_amount
                    st.success(f"{ticker} added to portfolio!")
                else:
                    st.error(
                        f"No data available for {ticker}. Please verify the ticker symbol."
                    )
            except Exception as e:
                st.error(f"Error fetching data for {ticker}: {e}")
        else:
            st.warning("Please fill all fields correctly.")

# Portfolio Performance Section
st.title("Portfolio Performance Analysis")

# Display the current portfolio in a table
if st.session_state.portfolio:
    st.write("Your Portfolio Overview")

    portfolio_df = pd.DataFrame(st.session_state.portfolio)

    # Calculate the portfolio weight for each stock as a percentage
    portfolio_df["weight"] = (
        portfolio_df["invested_amount"] / st.session_state.total_investment
    ) * 100

    # Calculate individual stock return percentage
    portfolio_df["individual_return"] = [
        (
            (
                yf.download(
                    stock["ticker"], start=stock["purchase_date"].strftime("%Y-%m-%d")
                )["Close"].iloc[-1]
                / stock["avg_price"]
            )
            - 1
        )
        * 100
        for stock in st.session_state.portfolio
    ]

    # Display table with enhanced formatting
    st.dataframe(
        portfolio_df[
            [
                "ticker",
                "purchase_date",
                "avg_price",
                "invested_amount",
                "individual_return",
                "weight",
                "sector",
            ]
        ].rename(
            columns={
                "ticker": "Stock Name",
                "purchase_date": "Purchase Date",
                "avg_price": "Average Price",
                "invested_amount": "Invested Amount",
                "individual_return": "Individual Stock Return (%)",
                "weight": "Portfolio Weight (%)",
                "sector": "Sector",
            }
        ),
        width=800,
    )

    # Initialize performance data for portfolio comparison
    fig_portfolio = go.Figure()

    # Track the earliest purchase date
    earliest_date = min(stock["purchase_date"] for stock in st.session_state.portfolio)

    # Fetch Nifty 50 data
    nifty_data = yf.download("^NSEI", start=earliest_date.strftime("%Y-%m-%d"))

    # Calculate the cumulative return for Nifty 50
    nifty_data["Cumulative Return"] = (
        nifty_data["Close"] / nifty_data["Close"].iloc[0] - 1
    ) * 100

    fig_portfolio.add_trace(
        go.Scatter(
            x=nifty_data.index,
            y=nifty_data["Cumulative Return"],  # Cumulative return for Nifty 50
            mode="lines",
            name="Nifty 50",
            line=dict(color="orange"),
        )
    )

    # Initialize total portfolio performance data
    portfolio_performance = pd.DataFrame(index=nifty_data.index)

    for stock in st.session_state.portfolio:
        ticker = stock["ticker"]
        purchase_date = stock["purchase_date"]

        try:
            stock_data = yf.download(
                ticker, start=purchase_date.strftime("%Y-%m-%d"), period="1y"
            )
            if not stock_data.empty:
                # Calculate cumulative return for each stock
                cumulative_return = (stock_data["Close"] / stock["avg_price"] - 1) * 100
                portfolio_performance[ticker] = (
                    cumulative_return  # Store cumulative return for stock
                )
            else:
                st.warning(f"No data available for {ticker}.")
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")

    # Calculate total portfolio performance
    portfolio_performance["Total"] = portfolio_performance.sum(axis=1)

    # Add total portfolio return to the figure
    fig_portfolio.add_trace(
        go.Scatter(
            x=portfolio_performance.index,
            y=portfolio_performance["Total"],  # Cumulative return for total portfolio
            mode="lines",
            name="Total Portfolio Return",
            line=dict(color="blue"),
        )
    )

    # Show the portfolio return chart
    fig_portfolio.update_layout(
        title="Portfolio Return vs Nifty 50", yaxis_title="Return (%)"
    )
    st.plotly_chart(fig_portfolio, use_container_width=True)

    # Individual Stock Returns Chart
    fig_individual = go.Figure()

    for stock in st.session_state.portfolio:
        ticker = stock["ticker"]
        purchase_date = stock["purchase_date"]

        try:
            stock_data = yf.download(
                ticker, start=purchase_date.strftime("%Y-%m-%d"), period="1y"
            )
            if not stock_data.empty:
                # Calculate cumulative return for each stock
                cumulative_return = (stock_data["Close"] / stock["avg_price"] - 1) * 100
                fig_individual.add_trace(
                    go.Scatter(
                        x=stock_data.index,
                        y=cumulative_return,
                        mode="lines",
                        name=ticker,
                    )
                )
            else:
                st.warning(f"No data available for {ticker}.")
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")

    # Show the individual stock returns chart
    fig_individual.update_layout(
        title="Individual Stock Return", yaxis_title="Return (%)"
    )
    st.plotly_chart(fig_individual, use_container_width=True)

else:
    st.write("No stocks added to the portfolio yet.")

# Limiting to 10 stocks
if len(st.session_state.portfolio) >= 10:
    st.write("You've reached the limit of 10 stocks.")

# Adding a separate feedback link
st.markdown(
    """
    <div style="text-align: right;">
        <a href="https://forms.gle/5qTsS6uYQeyUmrCeA" target="_blank">Feedback</a>
    </div>
    """,
    unsafe_allow_html=True,
)


# Add "Project by: Rohit Churi" with LinkedIn profile link
st.markdown(
    """
    <div style="text-align: right;">
        <small>Project by: <a href="https://www.linkedin.com/in/rohit-churi/" target="_blank">Rohit Churi</a></small>
    </div>
    """,
    unsafe_allow_html=True,
)
