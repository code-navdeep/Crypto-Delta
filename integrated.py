"""
Delta Exchange Client for Crypto Options Data
Fetches option chains from Delta Exchange India's public market data and works out the
totals the dashboard shows.
"""

import requests
import pandas as pd
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)

class DeltaExchangeClient:
    """Delta Exchange API client for crypto options data."""

    def __init__(self):
        """Initialize Delta client (no authentication required for market data)."""
        self.base_url = "https://api.india.delta.exchange"
        self.session = requests.Session()
        self.rate_limit_delay = 1.0  # 1 second between requests
        self.last_request_time = 0
        self.max_retries = 3
        # Hardcoded supported assets
        self.supported_assets = ['BTC', 'ETH']

        logger.info("Delta Exchange client initialized")

    def _rate_limit(self):
        """Simple rate limiting for API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.1f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict = None, retries: int = None) -> Optional[Dict]:
        """
        Make HTTP request to Delta API with error handling and retries.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            retries: Number of retries (uses max_retries if None)

        Returns:
            API response dict or None on failure
        """
        if retries is None:
            retries = self.max_retries

        headers = {
            "Accept": "application/json",
            "User-Agent": "OptionChainViewer/1.0"
        }

        url = f"{self.base_url}{endpoint}"

        for attempt in range(retries + 1):
            try:
                self._rate_limit()

                logger.debug(f"Delta API request attempt {attempt + 1}: {endpoint}")
                response = self.session.get(url, params=params, headers=headers, timeout=15)

                # Check for rate limiting
                if response.status_code == 429:
                    logger.warning("Rate limit hit, increasing delay")
                    self.rate_limit_delay = min(5.0, self.rate_limit_delay * 2)

                    if attempt < retries:
                        time.sleep(self.rate_limit_delay)
                        continue
                    else:
                        raise requests.exceptions.RequestException("Rate limit exceeded")

                response.raise_for_status()
                result = response.json()

                logger.debug(f"Delta API request successful: {endpoint}")

                return result

            except requests.exceptions.RequestException as e:
                logger.error(f"Delta API request failed (attempt {attempt + 1}): {e}")

                if attempt < retries:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Delta API request failed after {retries + 1} attempts: {endpoint}")
                    return None

        return None

    def validate_input(self, asset: str, expiry: str = None) -> Tuple[bool, str]:
        """Validate input parameters for Delta Exchange."""
        # Validate asset
        if asset not in self.supported_assets:
            return False, f"Invalid asset: {asset}. Must be one of {self.supported_assets}"

        # Validate expiry if provided
        if expiry:
            try:
                expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
                if expiry_date.date() < datetime.now().date():
                    return False, f"Expiry date {expiry} is in the past"
            except ValueError:
                return False, f"Invalid expiry date format: {expiry}. Use YYYY-MM-DD"

        return True, "Valid"

    def get_expiry_list(self, asset: str = "BTC") -> List[str]:
        """
        Get available expiry dates for an asset from Delta Exchange API.

        Args:
            asset: Underlying asset symbol (BTC, ETH)

        Returns:
            List of expiry dates in YYYY-MM-DD format, sorted chronologically
        """
        try:
            logger.info(f"Fetching expiry list for {asset} from Delta Exchange API")

            # Validate asset
            is_valid, error_msg = self.validate_input(asset)
            if not is_valid:
                logger.error(f"Input validation failed: {error_msg}")
                return []

            # Fetch all live option products for the asset
            params = {
                "contract_types": "call_options,put_options",
                "underlying_asset_symbols": asset
            }

            response = self._make_request("/v2/products", params)

            if not response or not response.get("success"):
                logger.error(f"Failed to fetch products for {asset}: {response}")
                return []

            products = response.get("result", [])
            if not products:
                logger.warning(f"No option products found for {asset}")
                return []

            # Extract unique expiry dates from option symbols
            expiry_dates = set()

            for product in products:
                symbol = product.get("symbol", "")
                if not symbol:
                    continue

                # Parse Delta option symbol format: C-BTC-90000-310125
                try:
                    parts = symbol.split("-")
                    if len(parts) >= 4:
                        expiry_code = parts[3]  # DDMMYY format

                        # Convert DDMMYY to YYYY-MM-DD
                        if len(expiry_code) == 6:
                            day = expiry_code[:2]
                            month = expiry_code[2:4]
                            year = "20" + expiry_code[4:6]  # Assume 20xx

                            # Validate date components
                            if (day.isdigit() and month.isdigit() and year.isdigit() and
                                1 <= int(day) <= 31 and 1 <= int(month) <= 12):
                                expiry_date = f"{year}-{month}-{day}"
                                expiry_dates.add(expiry_date)

                except (IndexError, ValueError) as e:
                    logger.debug(f"Could not parse expiry from symbol {symbol}: {e}")
                    continue

            # Convert to sorted list
            expiry_list = sorted(list(expiry_dates), key=lambda x: datetime.strptime(x, "%Y-%m-%d"))

            logger.info(f"Successfully extracted {len(expiry_list)} unique expiry dates for {asset}")

            return expiry_list

        except Exception as e:
            logger.error(f"Error fetching expiry list for {asset}: {e}")
            return []

    def fetch_option_chain(self, asset: str, expiry: str) -> Optional[List[Dict]]:
        """
        Fetch option chain data from Delta Exchange.

        Args:
            asset: Underlying asset (BTC, ETH)
            expiry: Expiry date in YYYY-MM-DD format

        Returns:
            List of option contracts or None on failure
        """
        # Validate inputs
        is_valid, error_msg = self.validate_input(asset, expiry)
        if not is_valid:
            logger.error(f"Input validation failed: {error_msg}")
            return None

        try:
            # Convert YYYY-MM-DD to DD-MM-YYYY for Delta API
            expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
            delta_expiry = expiry_date.strftime('%d-%m-%Y')

            params = {
                "contract_types": "call_options,put_options",
                "underlying_asset_symbols": asset,
                "expiry_date": delta_expiry
            }

            logger.info(f"Fetching option chain: Asset={asset}, Expiry={expiry}")
            response = self._make_request("/v2/tickers", params)

            if response and response.get("success"):
                result = response.get("result", [])
                logger.info(f"Successfully fetched {len(result)} option contracts for {asset}")
                return result
            else:
                logger.error(f"Failed to fetch option chain: {response}")
                return None

        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
            return None

    def parse_option_symbol(self, symbol: str) -> Tuple[Optional[str], Optional[float], Optional[str]]:
        """
        Parse Delta option symbol with enhanced validation.
        Format: C-BTC-90000-310125 or P-BTC-90000-310125

        Args:
            symbol: Option symbol string

        Returns:
            Tuple of (option_type, strike_price, expiry_code)
        """
        if not symbol or not isinstance(symbol, str):
            return None, None, None

        try:
            parts = symbol.split("-")

            # Validate symbol format
            if len(parts) < 4:
                logger.warning(f"Invalid symbol format: {symbol}")
                return None, None, None

            # Parse option type
            option_type_code = parts[0].upper()
            if option_type_code == "C":
                option_type = "CALL"
            elif option_type_code == "P":
                option_type = "PUT"
            else:
                logger.warning(f"Invalid option type in symbol: {symbol}")
                return None, None, None

            # Parse and validate strike price
            try:
                strike_str = parts[2]
                strike_price = float(strike_str)

                # Validate reasonable strike price range for crypto
                if strike_price <= 0 or strike_price > 1000000:
                    logger.warning(f"Unreasonable strike price in symbol: {symbol}")
                    return None, None, None

            except (ValueError, IndexError):
                logger.warning(f"Invalid strike price in symbol: {symbol}")
                return None, None, None

            # Parse expiry date
            expiry_code = parts[3] if len(parts) > 3 else None

            return option_type, strike_price, expiry_code

        except Exception as e:
            logger.error(f"Error parsing option symbol {symbol}: {e}")
            return None, None, None

    def get_option_chain(self, asset: str = "BTC", expiry: str = None) -> pd.DataFrame:
        """
        Fetch option chain data and return as standardized DataFrame.

        Args:
            asset: Underlying asset symbol (default: "BTC")
            expiry: Expiry date in YYYY-MM-DD format

        Returns:
            Standardized DataFrame with option chain data
        """
        try:
            # Get expiry if not provided
            if not expiry:
                expiry_list = self.get_expiry_list(asset)
                if not expiry_list:
                    logger.error(f"No expiry dates available for {asset}")
                    return pd.DataFrame()
                expiry = expiry_list[0]  # Use nearest expiry

            # Fetch raw data
            raw_data = self.fetch_option_chain(asset, expiry)

            if not raw_data:
                return pd.DataFrame()

            # Convert to DataFrame with Delta-specific processing
            processed_data = []

            for item in raw_data:
                # Parse symbol
                option_type, strike, expiry_code = self.parse_option_symbol(item.get("symbol", ""))
                if not option_type or strike is None:
                    continue

                # Extract data with safe defaults
                greeks = item.get("greeks", {}) or {}
                quotes = item.get("quotes", {}) or {}

                # Safe conversion helper
                def safe_float(value, default=0.0):
                    try:
                        if value is None:
                            return default
                        return float(str(value))
                    except (ValueError, TypeError):
                        return default

                processed_data.append({
                    'strike': safe_float(strike),
                    'option_type': 'CE' if option_type == 'CALL' else 'PE',
                    'last_price': safe_float(item.get("close", 0)),
                    'volume': safe_float(item.get("volume", 0)),  # in coins (BTC or ETH), with decimals
                    'oi': safe_float(item.get("oi", 0)),  # Changed to float as API returns decimals
                    'oi_change': safe_float(item.get("oi_change_usd_6h", 0)),  # Delta's change in open interest over 6 hours, in US dollars
                    'iv': safe_float(quotes.get("mark_iv", 0)),
                    'delta': safe_float(greeks.get("delta", 0)),
                    'gamma': safe_float(greeks.get("gamma", 0)),
                    'theta': safe_float(greeks.get("theta", 0)),
                    'vega': safe_float(greeks.get("vega", 0)),
                    'underlying_price': safe_float(item.get("spot_price", 0))
                })

            if processed_data:
                df = pd.DataFrame(processed_data)
                logger.info(f"Successfully processed {len(df)} Delta options for {asset}")
                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in get_option_chain: {e}")
            return pd.DataFrame()

    def _recalculate_analytics_for_filtered_data(self, filtered_df: pd.DataFrame, asset: str, expiry: str) -> Dict:
        """
        Work out the report for an option chain DataFrame (the whole chain, or the strikes
        kept by the strike-range filter) without fetching data again.

        Args:
            filtered_df: Option chain DataFrame
            asset: Asset symbol
            expiry: Expiry date

        Returns:
            Analytics report: basic metrics, support/resistance levels and the option chain
        """
        try:
            if filtered_df.empty:
                return {'error': 'Filtered data is empty'}

            return {
                'basic_metrics': self.calculate_basic_metrics(filtered_df),
                'support_resistance': self.calculate_support_resistance(filtered_df),
                'option_chain_data': filtered_df
            }

        except Exception as e:
            logger.error(f"Error recalculating analytics for {asset} {expiry}: {e}")
            return {'error': str(e)}

    def calculate_basic_metrics(self, df):
        """Calculate basic options metrics."""
        if df.empty:
            return {}

        try:
            calls = df[df['option_type'] == 'CE']
            puts = df[df['option_type'] == 'PE']

            return {
                'underlying_price': df['underlying_price'].iloc[0],
                'total_call_oi': float(calls['oi'].sum()),
                'total_put_oi': float(puts['oi'].sum()),
                'total_call_volume': float(calls['volume'].sum()),
                'total_put_volume': float(puts['volume'].sum())
            }

        except Exception as e:
            logger.error(f"Error calculating basic metrics: {e}")
            return {}

    def calculate_support_resistance(self, df, top_n=3):
        """Calculate support/resistance levels based on OI."""
        if df.empty:
            return {}

        try:
            calls = df[df['option_type'] == 'CE']
            puts = df[df['option_type'] == 'PE']

            result = {}

            if not calls.empty:
                calls_oi = calls.nlargest(top_n, 'oi')
                result.update({
                    'resistance_levels': calls_oi['strike'].tolist(),
                    'resistance_oi': calls_oi['oi'].tolist()
                })

            if not puts.empty:
                puts_oi = puts.nlargest(top_n, 'oi')
                result.update({
                    'support_levels': puts_oi['strike'].tolist(),
                    'support_oi': puts_oi['oi'].tolist()
                })

            return result

        except Exception as e:
            logger.error(f"Error calculating support/resistance: {e}")
            return {}

    def generate_comprehensive_report(self, asset: str = "BTC", expiry: str = None) -> Dict:
        """
        Fetch one expiry's option chain and work out its report.

        Args:
            asset: Crypto asset symbol (BTC, ETH)
            expiry: Expiry date in YYYY-MM-DD format

        Returns:
            Analytics report dict
        """
        try:
            df = self.get_option_chain(asset, expiry)

            if df.empty:
                return {'error': f'No options data available for {asset}'}

            return self._recalculate_analytics_for_filtered_data(df, asset, expiry)

        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            return {'error': str(e)}
