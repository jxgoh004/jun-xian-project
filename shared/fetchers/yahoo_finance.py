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
    
    def get_financial_trends(self):
        """
        Extract annual historical trends + TTM for the financial overview charts.

        Returns a dict with:
            years: list of year labels (ints for annual, 'TTM' for trailing twelve months)
            revenue, operating_income, net_income,
            operating_cash_flow, free_cash_flow, stock_based_compensation,
            cash_and_st_investments, total_debt, net_accounts_receivable:
                parallel lists of floats in millions (None if missing).

        Annual columns come from .financials / .cash_flow / .balance_sheet
        (most recent first in yfinance; reversed here to oldest-first).
        TTM is appended as the final point when quarterly data is available
        (sum of last 4 quarters for flow items; most recent quarter for stock items).
        """
        if self.financials is None:
            self.fetch_all_data()

        def _pick_row(frame, candidates):
            if frame is None or frame.empty:
                return None
            for name in candidates:
                if name in frame.index:
                    return frame.loc[name]
            return None

        def _annual_series(frame, candidates):
            row = _pick_row(frame, candidates)
            if row is None:
                return [], []
            row = row.dropna()
            if row.empty:
                return [], []
            # yfinance returns most-recent-first; reverse to oldest-first
            row = row.iloc[::-1]
            years = []
            values = []
            for col, val in row.items():
                try:
                    year = int(pd.Timestamp(col).year)
                except Exception:
                    continue
                if isinstance(val, (int, float)) and not pd.isna(val):
                    years.append(year)
                    values.append(float(val) / 1_000_000)
                else:
                    years.append(year)
                    values.append(None)
            return years, values

        def _ttm_sum(frame, candidates):
            """Sum last 4 quarters for a flow-statement row (in millions)."""
            row = _pick_row(frame, candidates)
            if row is None:
                return None
            row = row.dropna()
            if len(row) < 4:
                return None
            total = row.iloc[:4].sum()
            if pd.isna(total):
                return None
            return float(total) / 1_000_000

        def _latest_quarter(frame, candidates):
            """Most recent quarterly value for a balance-sheet row (in millions)."""
            row = _pick_row(frame, candidates)
            if row is None:
                return None
            row = row.dropna()
            if row.empty:
                return None
            val = row.iloc[0]
            if pd.isna(val):
                return None
            return float(val) / 1_000_000

        def _total_debt_from_bs(frame):
            """Sum current + long-term debt from a balance sheet frame."""
            cur = _pick_row(frame, [
                'Current Debt', 'Current Debt And Capital Lease Obligation',
                'Short Long Term Debt', 'Current Portion Of Long Term Debt',
            ])
            lt = _pick_row(frame, [
                'Long Term Debt', 'Long Term Debt And Capital Lease Obligation',
                'Long Term Debt Excl Capital Leases',
            ])
            total_alt = _pick_row(frame, ['Total Debt'])
            if total_alt is not None:
                series = total_alt.dropna()
                if not series.empty:
                    # Convert to millions column-by-column
                    series = series.iloc[::-1]
                    out_years, out_vals = [], []
                    for col, v in series.items():
                        try:
                            out_years.append(int(pd.Timestamp(col).year))
                        except Exception:
                            continue
                        out_vals.append(float(v) / 1_000_000 if isinstance(v, (int, float)) and not pd.isna(v) else None)
                    return out_years, out_vals
            # Otherwise sum current + long-term
            if cur is None and lt is None:
                return [], []
            dates = set()
            if cur is not None:
                dates.update(cur.dropna().index)
            if lt is not None:
                dates.update(lt.dropna().index)
            # Sort ascending
            dates = sorted(dates)
            years, values = [], []
            for d in dates:
                try:
                    years.append(int(pd.Timestamp(d).year))
                except Exception:
                    continue
                c_val = 0.0
                l_val = 0.0
                if cur is not None and d in cur.index and isinstance(cur.loc[d], (int, float)) and not pd.isna(cur.loc[d]):
                    c_val = float(cur.loc[d])
                if lt is not None and d in lt.index and isinstance(lt.loc[d], (int, float)) and not pd.isna(lt.loc[d]):
                    l_val = float(lt.loc[d])
                total = c_val + l_val
                values.append(total / 1_000_000 if total else None)
            return years, values

        # ── Annual series from the three primary frames ─────────────────────
        rev_years, rev_vals = _annual_series(self.financials, [
            'Total Revenue', 'Revenue', 'Operating Revenue',
        ])
        op_years, op_vals = _annual_series(self.financials, [
            'Operating Income', 'Operating Income Loss',
        ])
        ni_years, ni_vals = _annual_series(self.financials, [
            'Net Income', 'Net Income Common Stockholders',
            'Net Income From Continuing Operations',
        ])

        ocf_years, ocf_vals = _annual_series(self.cash_flow, [
            'Operating Cash Flow', 'Total Cash From Operating Activities',
            'Cash From Operating Activities',
        ])
        fcf_years, fcf_vals = _annual_series(self.cash_flow, ['Free Cash Flow'])
        # If FCF row missing, derive from OCF - CapEx
        if not fcf_years and self.cash_flow is not None and not self.cash_flow.empty:
            capex_row = _pick_row(self.cash_flow, [
                'Capital Expenditure', 'Capital Expenditures', 'Capex',
            ])
            if capex_row is not None and ocf_years:
                capex_row = capex_row.iloc[::-1]
                fcf_years = list(ocf_years)
                fcf_vals = []
                for yr, ocf_v in zip(ocf_years, ocf_vals):
                    capex_v = None
                    # Find matching year column
                    for col, v in capex_row.items():
                        try:
                            if int(pd.Timestamp(col).year) == yr:
                                if isinstance(v, (int, float)) and not pd.isna(v):
                                    capex_v = float(v) / 1_000_000
                                break
                        except Exception:
                            continue
                    if ocf_v is None or capex_v is None:
                        fcf_vals.append(None)
                    else:
                        fcf_vals.append(ocf_v - abs(capex_v))

        sbc_years, sbc_vals = _annual_series(self.cash_flow, [
            'Stock Based Compensation', 'Stock Based Compensation Expense',
        ])

        cash_years, cash_vals = _annual_series(self.balance_sheet, [
            'Cash Cash Equivalents And Short Term Investments',
            'Cash, Cash Equivalents & Short Term Investments',
            'Cash And Cash Equivalents',
            'Cash And Short Term Investments',
            'Total Cash', 'Cash And Equivalents', 'Cash',
        ])
        debt_years, debt_vals = _total_debt_from_bs(self.balance_sheet)
        ar_years, ar_vals = _annual_series(self.balance_sheet, [
            'Accounts Receivable', 'Net Accounts Receivable', 'Receivables',
            'Gross Accounts Receivable',
        ])

        # ── Union of all observed years, sorted ascending ───────────────────
        all_years = sorted(set(
            rev_years + op_years + ni_years +
            ocf_years + fcf_years + sbc_years +
            cash_years + debt_years + ar_years
        ))

        def _align(yrs, vals):
            lookup = dict(zip(yrs, vals))
            return [lookup.get(y) for y in all_years]

        revenue = _align(rev_years, rev_vals)
        operating_income = _align(op_years, op_vals)
        net_income = _align(ni_years, ni_vals)
        operating_cash_flow = _align(ocf_years, ocf_vals)
        free_cash_flow = _align(fcf_years, fcf_vals)
        stock_based_compensation = _align(sbc_years, sbc_vals)
        cash_and_st_investments = _align(cash_years, cash_vals)
        total_debt = _align(debt_years, debt_vals)
        net_accounts_receivable = _align(ar_years, ar_vals)

        years = list(all_years)

        # ── TTM column (last 4 quarters / most recent quarter) ──────────────
        ttm_rev = _ttm_sum(self.ticker.quarterly_financials if hasattr(self.ticker, 'quarterly_financials') else None, [
            'Total Revenue', 'Revenue', 'Operating Revenue',
        ])
        ttm_op = _ttm_sum(self.ticker.quarterly_financials if hasattr(self.ticker, 'quarterly_financials') else None, [
            'Operating Income', 'Operating Income Loss',
        ])
        ttm_ni = _ttm_sum(self.quarterly_cashflow, [
            'Net Income From Continuing Operations',
            'Net Income Continuing Operations', 'Net Income',
        ])
        ttm_ocf = _ttm_sum(self.quarterly_cashflow, [
            'Operating Cash Flow', 'Total Cash From Operating Activities',
            'Cash From Operating Activities',
        ])
        ttm_fcf = _ttm_sum(self.quarterly_cashflow, ['Free Cash Flow'])
        if ttm_fcf is None and ttm_ocf is not None:
            capex_ttm = _ttm_sum(self.quarterly_cashflow, [
                'Capital Expenditure', 'Capital Expenditures', 'Capex',
            ])
            if capex_ttm is not None:
                ttm_fcf = ttm_ocf - abs(capex_ttm)
        ttm_sbc = _ttm_sum(self.quarterly_cashflow, [
            'Stock Based Compensation', 'Stock Based Compensation Expense',
        ])

        ttm_cash = _latest_quarter(self.quarterly_balance_sheet, [
            'Cash Cash Equivalents And Short Term Investments',
            'Cash, Cash Equivalents & Short Term Investments',
            'Cash And Cash Equivalents',
            'Cash And Short Term Investments',
            'Total Cash', 'Cash And Equivalents', 'Cash',
        ])
        # Total debt TTM (most recent quarter, sum of components)
        q_cur = _latest_quarter(self.quarterly_balance_sheet, [
            'Current Debt', 'Current Debt And Capital Lease Obligation',
            'Short Long Term Debt', 'Current Portion Of Long Term Debt',
        ]) or 0.0
        q_lt = _latest_quarter(self.quarterly_balance_sheet, [
            'Long Term Debt', 'Long Term Debt And Capital Lease Obligation',
            'Long Term Debt Excl Capital Leases',
        ]) or 0.0
        ttm_debt_total = _latest_quarter(self.quarterly_balance_sheet, ['Total Debt'])
        if ttm_debt_total is None:
            ttm_debt = (q_cur + q_lt) if (q_cur or q_lt) else None
        else:
            ttm_debt = ttm_debt_total
        ttm_ar = _latest_quarter(self.quarterly_balance_sheet, [
            'Accounts Receivable', 'Net Accounts Receivable', 'Receivables',
            'Gross Accounts Receivable',
        ])

        have_ttm = any(v is not None for v in [
            ttm_rev, ttm_op, ttm_ni, ttm_ocf, ttm_fcf, ttm_sbc,
            ttm_cash, ttm_debt, ttm_ar,
        ])
        if have_ttm:
            years.append('TTM')
            revenue.append(ttm_rev)
            operating_income.append(ttm_op)
            net_income.append(ttm_ni)
            operating_cash_flow.append(ttm_ocf)
            free_cash_flow.append(ttm_fcf)
            stock_based_compensation.append(ttm_sbc)
            cash_and_st_investments.append(ttm_cash)
            total_debt.append(ttm_debt)
            net_accounts_receivable.append(ttm_ar)

        return {
            'years': years,
            'revenue': revenue,
            'operating_income': operating_income,
            'net_income': net_income,
            'operating_cash_flow': operating_cash_flow,
            'free_cash_flow': free_cash_flow,
            'stock_based_compensation': stock_based_compensation,
            'cash_and_st_investments': cash_and_st_investments,
            'total_debt': total_debt,
            'net_accounts_receivable': net_accounts_receivable,
        }

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