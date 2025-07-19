import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import plotly.express as px

st.set_page_config(page_title="Mijn Portfolio Tracker", layout="wide")
st.title("\ud83d\udcc8 Mijn Portfolio Tracker")

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

    # Dividendoverzicht
    dividend_df = df[df['Total'] < 0]
    dividend_df = dividend_df[dividend_df['Quantity'] == 0]  # Alleen geld ontvangen, geen aandelen gekocht
    dividend_total = dividend_df['Total'].sum() * -1  # Positieve waarde tonen

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
        "VANGUARD S&P500": "VUSA.AS",
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

    # Visualisaties naast elkaar
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Portfolioverdeling")
        plot_data = portfolio.dropna(subset=['Current_Value'])
        plot_data = plot_data[plot_data['Current_Value'] > 0]

        if not plot_data.empty:
            fig1 = px.pie(plot_data, values='Current_Value', names='Product', title='Portfolioverdeling')
            fig1.update_traces(textinfo='percent+label')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.warning("Geen geldige posities om weer te geven in de grafiek.")

    with col2:
        st.subheader("Waardeontwikkeling over tijd")
        df_filtered = df[df['Quantity'] > 0].copy()
        df_filtered['Total_Value'] = df_filtered['Price'] * df_filtered['Quantity']
        daily_value = df_filtered.groupby('Date')['Total_Value'].sum().cumsum().reset_index()

        fig2 = px.line(daily_value, x='Date', y='Total_Value', title="Totale waarde van aankopen over tijd")
        fig2.update_layout(xaxis_title="Datum", yaxis_title="Waarde in €")
        st.plotly_chart(fig2, use_container_width=True)

    # Totale waarde en dividend
    totaal = portfolio['Current_Value'].sum()
    winst = portfolio['Unrealized_Gain_€'].sum()
    st.metric("Totale Waarde", f"€ {totaal:,.2f}")
    st.metric("Totaal Ongerealiseerde Winst", f"€ {winst:,.2f}")
    st.metric("Ontvangen Dividend", f"€ {dividend_total:,.2f}")

    # Geschat ontvangen dividend op basis van historische dividenden
    st.subheader("\ud83d\udcec Geschat Ontvangen Dividend")
    estimated_total_dividend = 0.0

    df_sorted = df.sort_values("Date")

    for _, row in portfolio.iterrows():
        ticker = row['Ticker']
        try:
            ticker_obj = yf.Ticker(ticker)
            dividends = ticker_obj.dividends
            if dividends.empty:
                continue

            transactions = df_sorted[df_sorted['Product'] == row['Product']][['Date', 'Quantity']].copy()
            transactions['Quantity'] = pd.to_numeric(transactions['Quantity'], errors='coerce')
            transactions['Cumulative_Shares'] = transactions['Quantity'].cumsum()

            div_earned = 0.0
            for div_date, dividend_per_share in dividends.items():
                div_date = pd.to_datetime(div_date)
                relevant_tx = transactions[transactions['Date'] <= div_date]
                if not relevant_tx.empty:
                    shares_on_date = relevant_tx.iloc[-1]['Cumulative_Shares']
                    div_earned += shares_on_date * dividend_per_share

            estimated_total_dividend += div_earned

        except:
            continue

    st.metric("Geschat Ontvangen Dividend", f"€ {estimated_total_dividend:,.2f}")

else:
    st.info("\ud83d\udcc1 Upload een CSV-bestand om te beginnen.")
