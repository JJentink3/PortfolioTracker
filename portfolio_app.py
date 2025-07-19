import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

st.set_page_config(page_title="My Portfolio Tracker", layout="wide")
st.title("📈 My Portfolio Tracker")

# Upload CSV-bestand
uploaded_file = st.file_uploader("Upload je transactiebestand (CSV)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Basis opschoning en parsing
    df = df.rename(columns={
        'Datum': 'Date',
        'Product': 'Product',
        'ISIN': 'ISIN',
        'Aantal': 'Quantity',
        'Koers': 'Price',
        'Lokale waarde': 'Local_Value',
        'Transactiekosten en/of': 'Fees',
        'Totaal': 'Total'
    })

    df = df[df['Date'].str.contains(r'\d{2}-\d{2}-\d{4}', na=False)]
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')

    numeric_cols = ['Quantity', 'Price', 'Local_Value', 'Fees', 'Total']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Portfolio posities berekenen
    portfolio = df.groupby(['Product', 'ISIN']).agg(
        Total_Shares=('Quantity', 'sum'),
        Average_Buy_Price=('Price', 'mean'),
        Total_Invested=('Total', 'sum'),
        Total_Fees=('Fees', 'sum')
    ).reset_index()

    portfolio['Total_Invested'] = portfolio['Total_Invested'].abs()
    portfolio['Total_Fees'] = portfolio['Total_Fees'].abs()

    # Yahoo Finance ticker mapping
    ticker_mapping = {
        "ASML HOLDING": "ASML.AS",
        "VANGUARD S&P500": "VUSA.L",
        "VANGUARD FTSE AW": "VWRL.AS",
        "WISDOMTREE ARTIFICIAL INTELLIGENCE UCITS ETF": "WTAI.MI",
        "WISDOMTREE ARTIFICIAL INTELLIGENCE UCITS ETF USD": "WTAI.MI",
    }
    portfolio['Ticker'] = portfolio['Product'].map(ticker_mapping)

    # Verwijder posities met 0 of negatieve aandelen
    portfolio = portfolio[portfolio['Total_Shares'] > 0]

    # Live koersen ophalen
    def get_price(ticker):
        try:
            return yf.Ticker(ticker).history(period='1d')['Close'].iloc[-1]
        except:
            return None

    portfolio['Current_Price'] = portfolio['Ticker'].apply(get_price)
    portfolio['Current_Value'] = portfolio['Current_Price'] * portfolio['Total_Shares']
    portfolio['Unrealized_Gain_€'] = portfolio['Current_Value'] - portfolio['Total_Invested']
    portfolio['Unrealized_Gain_%'] = (portfolio['Unrealized_Gain_€'] / portfolio['Total_Invested']) * 100

    # Rond waarden af
    portfolio = portfolio.round({
        'Current_Price': 2,
        'Current_Value': 2,
        'Unrealized_Gain_€': 2,
        'Unrealized_Gain_%': 2
    })

    # Weergave
    st.subheader("Overzicht")
    st.dataframe(portfolio, use_container_width=True)

    # Waardeverdeling
    st.subheader("Portfolioverdeling")
    plot_data = portfolio.dropna(subset=['Current_Value'])
    plot_data = plot_data[plot_data['Current_Value'] > 0]

    if not plot_data.empty:
        fig, ax = plt.subplots()
        ax.pie(plot_data['Current_Value'], labels=plot_data['Product'], autopct='%1.1f%%')
        st.pyplot(fig)
    else:
        st.warning("Geen geldige posities om weer te geven in de grafiek.")

    # Totale waarde
    totaal = portfolio['Current_Value'].sum()
    winst = portfolio['Unrealized_Gain_€'].sum()
    st.metric("Totale Waarde", f"€ {totaal:,.2f}")
    st.metric("Totaal Ongerealiseerde Winst", f"€ {winst:,.2f}")
else:
    st.info("📁 Upload een CSV-bestand om te beginnen.")
