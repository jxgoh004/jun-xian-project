import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, Optional, Any

class FinVizFetcher:
    """Fetches financial data from FinViz for intrinsic value calculations"""

    def __init__(self, symbol: str):
        """Initialize with stock symbol"""
        self.symbol = symbol.upper()
        self.base_url = "https://finviz.com/quote.ashx?t="
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.data = {}
        self.soup = None

    def fetch_data(self):
        """Fetch and parse FinViz page for the stock"""
        try:
            url = f"{self.base_url}{self.symbol}"
            print(f"Fetching FinViz data for {self.symbol}...")

            response = requests.get(url, headers=self.headers, timeout=15)

            if response.status_code == 200:
                self.soup = BeautifulSoup(response.content, 'html.parser')
                self._parse_financial_data()
                return True
            else:
                print(f"Failed to fetch FinViz data. Status: {response.status_code}")
                return False

        except Exception as e:
            print(f"Error fetching FinViz data: {e}")
            return False

    def _parse_financial_data(self):
        """Parse financial data from FinViz page"""
        if not self.soup:
            return

        # Find the main financial data table
        # FinViz typically has financial metrics in a specific table format
        tables = self.soup.find_all('table', class_='snapshot-table2')

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                # Process pairs of cells (label, value)
                for i in range(0, len(cells), 2):
                    if i + 1 < len(cells):
                        label = cells[i].get_text(strip=True)
                        value = cells[i + 1].get_text(strip=True)
                        self.data[label] = value

        # Also look for other table formats
        if not self.data:
            # Try alternative table structure
            tables = self.soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        for i in range(0, len(cells), 2):
                            if i + 1 < len(cells):
                                label = cells[i].get_text(strip=True)
                                value = cells[i + 1].get_text(strip=True)
                                if label and value and len(label) > 1:
                                    self.data[label] = value

    def _parse_financial_value(self, value_str: str) -> Optional[float]:
        """Parse financial value string (handles B, M, K suffixes and percentages)"""
        if not value_str or value_str == '-' or value_str == 'N/A':
            return None

        # Remove common prefixes/suffixes
        value_str = value_str.replace('$', '').replace('%', '').replace(',', '').strip()

        # Handle negative values
        is_negative = value_str.startswith('-')
        if is_negative:
            value_str = value_str[1:]

        try:
            # Handle suffix multipliers
            multiplier = 1
            if value_str.endswith('B'):
                multiplier = 1_000_000_000
                value_str = value_str[:-1]
            elif value_str.endswith('M'):
                multiplier = 1_000_000
                value_str = value_str[:-1]
            elif value_str.endswith('K'):
                multiplier = 1_000
                value_str = value_str[:-1]

            # Convert to float and apply multiplier
            value = float(value_str) * multiplier
            return -value if is_negative else value

        except (ValueError, TypeError):
            return None

    def get_cash_flow_data(self) -> Dict[str, Any]:
        """Extract cash flow related data"""
        cash_flow_data = {}

        # Look for cash flow related metrics
        cash_flow_fields = {
            'Operating Cash Flow': ['Operating Cash Flow', 'Op Cash Flow', 'Cash Flow'],
            'Free Cash Flow': ['Free Cash Flow', 'FCF'],
            'Cash Flow Growth': ['Cash Flow Growth', 'CF Growth'],
            'Cash Flow per Share': ['Cash/sh', 'Cash per Share']
        }

        for key, possible_labels in cash_flow_fields.items():
            for label in possible_labels:
                if label in self.data:
                    parsed_value = self._parse_financial_value(self.data[label])
                    if parsed_value is not None:
                        cash_flow_data[key] = parsed_value
                        break

        return cash_flow_data

    def get_balance_sheet_data(self) -> Dict[str, Any]:
        """Extract balance sheet related data"""
        balance_sheet_data = {}

        # Look for balance sheet related metrics
        balance_sheet_fields = {
            'Total Debt': ['Total Debt', 'Debt', 'LT Debt'],
            'Total Cash': ['Cash', 'Total Cash', 'Cash & ST Investments'],
            'Book Value': ['Book/sh', 'Book Value'],
            'Total Assets': ['Total Assets', 'Assets']
        }

        for key, possible_labels in balance_sheet_fields.items():
            for label in possible_labels:
                if label in self.data:
                    parsed_value = self._parse_financial_value(self.data[label])
                    if parsed_value is not None:
                        balance_sheet_data[key] = parsed_value
                        break

        return balance_sheet_data

    def get_growth_estimates(self) -> Dict[str, Any]:
        """Extract growth estimates"""
        growth_data = {}

        # Look for growth related metrics
        growth_fields = {
            'EPS Growth Next Year': ['EPS next Y', 'EPS Growth Next Y'],
            'EPS Growth Next 5 Years': ['EPS next 5Y', 'EPS Growth 5Y', 'PEG'],
            'Sales Growth': ['Sales Growth', 'Revenue Growth'],
            'EPS Growth Past 5 Years': ['EPS past 5Y', 'EPS Growth Past 5Y']
        }

        for key, possible_labels in growth_fields.items():
            for label in possible_labels:
                if label in self.data:
                    # Growth rates are typically in percentage
                    value_str = self.data[label]
                    if '%' in value_str:
                        parsed_value = self._parse_financial_value(value_str.replace('%', ''))
                        if parsed_value is not None:
                            growth_data[key] = parsed_value / 100  # Convert to decimal
                            break

        return growth_data

    def get_valuation_metrics(self) -> Dict[str, Any]:
        """Extract valuation metrics"""
        valuation_data = {}

        # Look for valuation metrics
        valuation_fields = {
            'P/E Ratio': ['P/E', 'PE'],
            'Forward P/E': ['Forward P/E', 'Fwd P/E'],
            'PEG Ratio': ['PEG'],
            'Price to Sales': ['P/S', 'PS'],
            'Price to Book': ['P/B', 'PB'],
            'Price to Cash Flow': ['P/FCF', 'Price/FCF'],
            'Beta': ['Beta']
        }

        for key, possible_labels in valuation_fields.items():
            for label in possible_labels:
                if label in self.data:
                    parsed_value = self._parse_financial_value(self.data[label])
                    if parsed_value is not None:
                        valuation_data[key] = parsed_value
                        break

        return valuation_data

    def get_company_info(self) -> Dict[str, Any]:
        """Extract basic company information"""
        company_info = {}

        # Look for company info
        info_fields = {
            'Market Cap': ['Market Cap', 'Mkt Cap'],
            'Shares Outstanding': ['Shs Outstand', 'Shares Outstanding'],
            'Sector': ['Sector'],
            'Industry': ['Industry'],
            'Current Price': ['Price']
        }

        for key, possible_labels in info_fields.items():
            for label in possible_labels:
                if label in self.data:
                    if key in ['Market Cap', 'Shares Outstanding']:
                        parsed_value = self._parse_financial_value(self.data[label])
                        if parsed_value is not None:
                            company_info[key] = parsed_value
                            break
                    else:
                        company_info[key] = self.data[label]
                        break

        return company_info

    def get_all_data(self) -> Dict[str, Any]:
        """Get all extracted financial data"""
        if not self.data:
            self.fetch_data()

        return {
            'symbol': self.symbol,
            'cash_flow': self.get_cash_flow_data(),
            'balance_sheet': self.get_balance_sheet_data(),
            'growth_estimates': self.get_growth_estimates(),
            'valuation_metrics': self.get_valuation_metrics(),
            'company_info': self.get_company_info(),
            'raw_data': self.data
        }

    def print_summary(self):
        """Print summary of extracted data"""
        all_data = self.get_all_data()

        print(f"\n=== FinViz Data Summary for {self.symbol} ===")

        print("\n--- Company Info ---")
        for key, value in all_data['company_info'].items():
            print(f"{key}: {value}")

        print("\n--- Cash Flow Data ---")
        for key, value in all_data['cash_flow'].items():
            if isinstance(value, float):
                if abs(value) >= 1_000_000:
                    print(f"{key}: ${value/1_000_000:.1f}M")
                else:
                    print(f"{key}: ${value:,.0f}")
            else:
                print(f"{key}: {value}")

        print("\n--- Balance Sheet Data ---")
        for key, value in all_data['balance_sheet'].items():
            if isinstance(value, float):
                if abs(value) >= 1_000_000:
                    print(f"{key}: ${value/1_000_000:.1f}M")
                else:
                    print(f"{key}: ${value:,.0f}")
            else:
                print(f"{key}: {value}")

        print("\n--- Growth Estimates ---")
        for key, value in all_data['growth_estimates'].items():
            if isinstance(value, float):
                print(f"{key}: {value:.1%}")
            else:
                print(f"{key}: {value}")

        print("\n--- Valuation Metrics ---")
        for key, value in all_data['valuation_metrics'].items():
            print(f"{key}: {value}")

def main():
    """Test the FinViz fetcher"""
    symbol = input("Enter stock symbol (e.g., AAPL): ").strip()

    fetcher = FinVizFetcher(symbol)
    fetcher.print_summary()

if __name__ == "__main__":
    main()