import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timedelta

class YahooFinanceFetcher:
    """Fetches financial data from Yahoo Finance for intrinsic value calculations"""

    def __init__(self, symbol):
        """Initialize with stock symbol"""
        self.symbol = symbol.upper()
        self.ticker = yf.Ticker(self.symbol)  # yfinance manages its own curl_cffi/Chrome session
        self.info = None
        self.financials = None
        self.cash_flow = None
        self.quarterly_cashflow = None
        self.balance_sheet = None
        self.quarterly_balance_sheet = None

    def fetch_all_data(self):
        """Fetch all required data for intrinsic value calculation"""
        print(f"Fetching data for {self.symbol}...")

        for attempt in range(1, 4):
            try:
                # Basic company info
                self.info = self.ticker.info

                # Financial statements
                self.financials = self.ticker.financials
                self.cash_flow = self.ticker.cashflow
                self.quarterly_cashflow = self.ticker.quarterly_cashflow
                self.balance_sheet = self.ticker.balance_sheet
                self.quarterly_balance_sheet = self.ticker.quarterly_balance_sheet

                return True
            except Exception as e:
                print(f"Error fetching data (attempt {attempt}/3): {e}")
                if attempt < 3:
                    time.sleep(2 ** attempt)  # 2s, 4s
        return False
    
    def get_current_price(self):
        """Get current stock price"""
        if not self.info:
            self.fetch_all_data()
        
        return self.info.get('currentPrice', self.info.get('previousClose', 'N/A'))
    
    def get_shares_outstanding(self):
        """Get shares outstanding"""
        if not self.info:
            self.fetch_all_data()
            
        return self.info.get('sharesOutstanding', self.info.get('impliedSharesOutstanding', 'N/A'))
    
    def get_current_eps(self):
        """Get current earnings per share (TTM)"""
        if not self.info:
            self.fetch_all_data()
            
        return self.info.get('trailingEps', self.info.get('forwardEps', 'N/A'))
    
    def get_operating_cash_flow_ttm(self):
        """Get TTM (Trailing Twelve Months) operating cash flow using quarterly data"""
        if self.quarterly_cashflow is None:
            self.fetch_all_data()
            
        if self.quarterly_cashflow is not None and not self.quarterly_cashflow.empty:
            # Look for operating cash flow in quarterly data
            ocf_rows = ['Operating Cash Flow', 'Total Cash From Operating Activities', 
                       'Cash From Operating Activities']
            
            for row_name in ocf_rows:
                if row_name in self.quarterly_cashflow.index:
                    # Get last 4 quarters (TTM)
                    quarterly_values = self.quarterly_cashflow.loc[row_name].dropna()
                    if len(quarterly_values) >= 4:
                        ttm_ocf = quarterly_values.iloc[:4].sum()  # Sum last 4 quarters
                        return ttm_ocf
                    elif len(quarterly_values) > 0:
                        # If less than 4 quarters available, annualize what we have
                        quarters_available = len(quarterly_values)
                        avg_quarterly = quarterly_values.mean()
                        return avg_quarterly * 4  # Annualize
            
            # If not found in quarterly, try net income as proxy
            if 'Net Income' in self.quarterly_cashflow.index:
                quarterly_values = self.quarterly_cashflow.loc['Net Income'].dropna()
                if len(quarterly_values) >= 4:
                    return quarterly_values.iloc[:4].sum()
                elif len(quarterly_values) > 0:
                    return quarterly_values.mean() * 4
        
        # Fallback to annual data if quarterly not available
        return self.get_operating_cash_flow_annual()
    
    def get_operating_cash_flow_annual(self):
        """Get operating cash flow from annual data (fallback method)"""
        if self.cash_flow is None:
            self.fetch_all_data()
            
        if self.cash_flow is not None and not self.cash_flow.empty:
            # Look for operating cash flow
            ocf_rows = ['Operating Cash Flow', 'Total Cash From Operating Activities', 
                       'Cash From Operating Activities']
            
            for row_name in ocf_rows:
                if row_name in self.cash_flow.index:
                    # Get most recent year (first column)
                    return self.cash_flow.loc[row_name].iloc[0]
            
            # If not found, try net income as proxy
            if 'Net Income' in self.cash_flow.index:
                return self.cash_flow.loc['Net Income'].iloc[0]
                
        return 'N/A'
    
    def get_operating_cash_flow(self):
        """Get current operating cash flow - prioritizes TTM over annual data"""
        return self.get_operating_cash_flow_ttm()

    def get_net_income_continuing_ops_ttm(self):
        """Get TTM Net Income from Continuing Operations using quarterly cash flow data"""
        if self.quarterly_cashflow is None:
            self.fetch_all_data()

        if self.quarterly_cashflow is not None and not self.quarterly_cashflow.empty:
            ni_rows = [
                'Net Income From Continuing Operations',
                'Net Income Continuing Operations',
                'Net Income From Continuing And Discontinued Operation',
                'Net Income',
            ]
            for row_name in ni_rows:
                if row_name in self.quarterly_cashflow.index:
                    values = self.quarterly_cashflow.loc[row_name].dropna()
                    if len(values) >= 4:
                        return values.iloc[:4].sum()
                    elif len(values) > 0:
                        return values.mean() * 4

        # Fallback: annual income statement
        if self.financials is None:
            self.fetch_all_data()
        if self.financials is not None and not self.financials.empty:
            ni_rows = [
                'Net Income From Continuing Operations',
                'Net Income Continuing Operations',
                'Net Income',
            ]
            for row_name in ni_rows:
                if row_name in self.financials.index:
                    return self.financials.loc[row_name].iloc[0]

        return 'N/A'

    def get_total_debt_quarterly(self):
        """Get total debt as Current Debt + Long Term Debt from most recent quarterly balance sheet"""
        if self.quarterly_balance_sheet is None:
            self.fetch_all_data()

        if self.quarterly_balance_sheet is not None and not self.quarterly_balance_sheet.empty:
            current_debt = 0
            long_term_debt = 0

            # Current Debt (short-term portion)
            for row_name in ['Current Debt', 'Current Debt And Capital Lease Obligation',
                             'Short Long Term Debt', 'Current Portion Of Long Term Debt']:
                if row_name in self.quarterly_balance_sheet.index:
                    val = self.quarterly_balance_sheet.loc[row_name].iloc[0]
                    if isinstance(val, (int, float)) and not pd.isna(val):
                        current_debt = val
                    break

            # Long Term Debt
            for row_name in ['Long Term Debt', 'Long Term Debt And Capital Lease Obligation',
                             'Long Term Debt Excl Capital Leases']:
                if row_name in self.quarterly_balance_sheet.index:
                    val = self.quarterly_balance_sheet.loc[row_name].iloc[0]
                    if isinstance(val, (int, float)) and not pd.isna(val):
                        long_term_debt = val
                    break

            if current_debt > 0 or long_term_debt > 0:
                return current_debt + long_term_debt
        
        # Fallback to annual data
        return self.get_total_debt_annual()
    
    def get_total_debt_annual(self):
        """Get total debt from annual balance sheet (fallback method)"""
        if self.balance_sheet is None:
            self.fetch_all_data()
            
        if self.balance_sheet is not None and not self.balance_sheet.empty:
            # Look for total debt variations
            debt_rows = ['Total Debt', 'Total Liabilities', 'Long Term Debt', 'Short Long Term Debt']
            
            for debt_row in debt_rows:
                if debt_row in self.balance_sheet.index:
                    return self.balance_sheet.loc[debt_row].iloc[0]
            
            # Try to calculate total debt from components
            long_term_debt = 0
            short_term_debt = 0
            
            if 'Long Term Debt' in self.balance_sheet.index:
                ltd = self.balance_sheet.loc['Long Term Debt'].iloc[0]
                if isinstance(ltd, (int, float)) and not pd.isna(ltd):
                    long_term_debt = ltd
                    
            current_debt_rows = ['Current Debt', 'Short Long Term Debt']
            for row_name in current_debt_rows:
                if row_name in self.balance_sheet.index:
                    std = self.balance_sheet.loc[row_name].iloc[0]
                    if isinstance(std, (int, float)) and not pd.isna(std):
                        short_term_debt = std
                    break
            
            if long_term_debt or short_term_debt:
                return long_term_debt + short_term_debt
        
        # Final fallback from info
        return self.info.get('totalDebt', 'N/A')
    
    def get_total_debt(self):
        """Get total debt - prioritizes quarterly over annual data"""
        return self.get_total_debt_quarterly()
    
    def get_cash_and_short_term_investments_quarterly(self):
        """Get cash and short-term investments from most recent quarterly balance sheet"""
        if self.quarterly_balance_sheet is None:
            self.fetch_all_data()
            
        if self.quarterly_balance_sheet is not None and not self.quarterly_balance_sheet.empty:
            # Prioritize the consolidated field first (exact field name from Yahoo Finance)
            priority_cash_rows = ['Cash Cash Equivalents And Short Term Investments', 
                                 'Cash, Cash Equivalents & Short Term Investments']
            
            for cash_row in priority_cash_rows:
                if cash_row in self.quarterly_balance_sheet.index:
                    cash_value = self.quarterly_balance_sheet.loc[cash_row].iloc[0]
                    if isinstance(cash_value, (int, float)) and not pd.isna(cash_value):
                        return cash_value
            
            # Fallback to other cash variations
            fallback_cash_rows = ['Cash And Cash Equivalents', 'Cash And Short Term Investments', 
                                'Total Cash', 'Cash And Equivalents', 'Cash']
            
            for cash_row in fallback_cash_rows:
                if cash_row in self.quarterly_balance_sheet.index:
                    cash_value = self.quarterly_balance_sheet.loc[cash_row].iloc[0]
                    if isinstance(cash_value, (int, float)) and not pd.isna(cash_value):
                        return cash_value
        
        # Fallback to annual data
        return self.get_cash_and_short_term_investments_annual()
    
    def get_cash_and_short_term_investments_annual(self):
        """Get cash and short-term investments from annual balance sheet (fallback method)"""
        if self.balance_sheet is None:
            self.fetch_all_data()
            
        if self.balance_sheet is not None and not self.balance_sheet.empty:
            # Prioritize the consolidated field first (exact field name from Yahoo Finance)
            priority_cash_rows = ['Cash Cash Equivalents And Short Term Investments',
                                 'Cash, Cash Equivalents & Short Term Investments']
            
            for cash_row in priority_cash_rows:
                if cash_row in self.balance_sheet.index:
                    cash_value = self.balance_sheet.loc[cash_row].iloc[0]
                    if isinstance(cash_value, (int, float)) and not pd.isna(cash_value):
                        return cash_value
            
            # Fallback to other cash variations
            fallback_cash_rows = ['Cash And Cash Equivalents', 'Cash And Short Term Investments',
                                'Total Cash', 'Cash And Equivalents', 'Cash']
            
            for cash_row in fallback_cash_rows:
                if cash_row in self.balance_sheet.index:
                    cash_value = self.balance_sheet.loc[cash_row].iloc[0]
                    if isinstance(cash_value, (int, float)) and not pd.isna(cash_value):
                        return cash_value
        
        # Final fallback from info
        return self.info.get('totalCash', 'N/A')
    
    def get_cash_and_short_term_investments(self):
        """Get cash and short-term investments - prioritizes quarterly over annual data"""
        return self.get_cash_and_short_term_investments_quarterly()
    
    def get_free_cash_flow(self):
        """Get current free cash flow"""
        if self.cash_flow is None:
            self.fetch_all_data()
            
        if self.cash_flow is not None and not self.cash_flow.empty:
            # Look for free cash flow
            fcf_rows = ['Free Cash Flow', 'Total Cash From Operating Activities']
            
            for row_name in fcf_rows:
                if row_name in self.cash_flow.index:
                    return self.cash_flow.loc[row_name].iloc[0]
                    
            # Calculate FCF = Operating Cash Flow - Capital Expenditures
            try:
                ocf = self.get_operating_cash_flow()
                capex_rows = ['Capital Expenditures', 'Capital Expenditure', 'Capex']
                
                for capex_row in capex_rows:
                    if capex_row in self.cash_flow.index:
                        capex = self.cash_flow.loc[capex_row].iloc[0]
                        if isinstance(ocf, (int, float)) and isinstance(capex, (int, float)):
                            return ocf - abs(capex)  # Capex is usually negative
                        break
            except:
                pass
                
        return 'N/A'
    
    def get_financial_ratios(self):
        """Get key financial ratios"""
        if not self.info:
            self.fetch_all_data()
            
        return {
            'pe_ratio': self.info.get('trailingPE', 'N/A'),
            'forward_pe': self.info.get('forwardPE', 'N/A'),
            'peg_ratio': self.info.get('pegRatio', 'N/A'),
            'price_to_book': self.info.get('priceToBook', 'N/A'),
            'price_to_sales': self.info.get('priceToSalesTrailing12Months', 'N/A'),
            'debt_to_equity': self.info.get('debtToEquity', 'N/A'),
            'roe': self.info.get('returnOnEquity', 'N/A'),
            'roa': self.info.get('returnOnAssets', 'N/A')
        }
    
    def estimate_growth_rates(self):
        """Estimate historical growth rates for EPS and cash flow"""
        try:
            if self.financials is None or self.cash_flow is None:
                self.fetch_all_data()
            
            growth_rates = {}
            
            # EPS Growth Rate (using net income as proxy)
            if self.financials is not None and not self.financials.empty:
                if 'Net Income' in self.financials.index:
                    net_incomes = self.financials.loc['Net Income'].dropna()
                    if len(net_incomes) >= 2:
                        # Calculate compound annual growth rate
                        years = len(net_incomes) - 1
                        start_value = net_incomes.iloc[-1]
                        end_value = net_incomes.iloc[0]
                        
                        if start_value > 0 and end_value > 0:
                            eps_growth = ((end_value / start_value) ** (1/years)) - 1
                            growth_rates['eps_growth'] = eps_growth
            
            # Cash Flow Growth Rate
            if self.cash_flow is not None and not self.cash_flow.empty:
                ocf_rows = ['Operating Cash Flow', 'Total Cash From Operating Activities']
                for row_name in ocf_rows:
                    if row_name in self.cash_flow.index:
                        cash_flows = self.cash_flow.loc[row_name].dropna()
                        if len(cash_flows) >= 2:
                            years = len(cash_flows) - 1
                            start_value = cash_flows.iloc[-1]
                            end_value = cash_flows.iloc[0]
                            
                            if start_value > 0 and end_value > 0:
                                cf_growth = ((end_value / start_value) ** (1/years)) - 1
                                growth_rates['cash_flow_growth'] = cf_growth
                        break
            
            # Use analyst estimates as fallback
            if not growth_rates and self.info:
                growth_rates['eps_growth'] = self.info.get('earningsGrowth', 0.05)  # Default 5%
                growth_rates['cash_flow_growth'] = self.info.get('revenueGrowth', 0.05)  # Default 5%
            
            return growth_rates
            
        except Exception as e:
            print(f"Error calculating growth rates: {e}")
            return {'eps_growth': 0.05, 'cash_flow_growth': 0.05}  # Default 5%
    
    def get_risk_free_rate(self):
        """Get current risk-free rate (10-year Treasury)"""
        try:
            treasury = yf.Ticker("^TNX")  # 10-year Treasury
            hist = treasury.history(period="1d")
            if not hist.empty:
                return hist['Close'].iloc[-1] / 100  # Convert percentage to decimal
        except:
            pass
        
        return 0.045  # Default 4.5%
    
    def estimate_discount_rate(self):
        """Estimate appropriate discount rate using CAPM"""
        try:
            if not self.info:
                self.fetch_all_data()
            
            risk_free_rate = self.get_risk_free_rate()
            beta = self.info.get('beta', 1.0)
            market_risk_premium = 0.06  # Typical market risk premium
            
            discount_rate = risk_free_rate + (beta * market_risk_premium)
            
            # Ensure reasonable bounds (4% - 15%)
            return max(0.04, min(0.15, discount_rate))
            
        except:
            return 0.08  # Default 8%
    
    def print_summary(self):
        """Print summary of all fetched data"""
        if not self.info:
            if not self.fetch_all_data():
                print("Failed to fetch data")
                return
        
        print(f"\n=== {self.symbol} - Financial Data Summary ===")
        print(f"Company: {self.info.get('longName', 'N/A')}")
        print(f"Sector: {self.info.get('sector', 'N/A')}")
        print(f"Industry: {self.info.get('industry', 'N/A')}")
        print(f"Current Price: ${self.get_current_price()}")
        print(f"Market Cap: ${self.info.get('marketCap', 'N/A'):,}" if isinstance(self.info.get('marketCap'), (int, float)) else f"Market Cap: {self.info.get('marketCap', 'N/A')}")
        
        print(f"\n--- Key Inputs for IV Calculation ---")
        print(f"Shares Outstanding: {self.get_shares_outstanding():,}" if isinstance(self.get_shares_outstanding(), (int, float)) else f"Shares Outstanding: {self.get_shares_outstanding()}")
        print(f"Current EPS: ${self.get_current_eps()}")
        
        ocf = self.get_operating_cash_flow()
        print(f"Operating Cash Flow: ${ocf/1e6:.1f}M" if isinstance(ocf, (int, float)) else f"Operating Cash Flow: {ocf}")
        
        fcf = self.get_free_cash_flow()
        print(f"Free Cash Flow: ${fcf/1e6:.1f}M" if isinstance(fcf, (int, float)) else f"Free Cash Flow: {fcf}")
        
        growth_rates = self.estimate_growth_rates()
        print(f"Estimated EPS Growth: {growth_rates.get('eps_growth', 0)*100:.1f}%")
        print(f"Estimated CF Growth: {growth_rates.get('cash_flow_growth', 0)*100:.1f}%")
        print(f"Estimated Discount Rate: {self.estimate_discount_rate()*100:.1f}%")
        
        ratios = self.get_financial_ratios()
        print(f"\n--- Key Ratios ---")
        print(f"P/E Ratio: {ratios['pe_ratio']}")
        print(f"P/B Ratio: {ratios['price_to_book']}")
        print(f"ROE: {ratios['roe']}")

def main():
    """Test the fetcher with a sample stock"""
    symbol = input("Enter stock symbol (e.g., AAPL): ").strip()
    
    fetcher = YahooFinanceFetcher(symbol)
    fetcher.print_summary()

if __name__ == "__main__":
    main()