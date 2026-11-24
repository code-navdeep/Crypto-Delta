"""
Options Analytics Visualization Engine
Creates interactive charts using Altair
"""

import altair as alt
import pandas as pd
import streamlit as st
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

# Colour scheme: calls red, puts green, everywhere
COLORS = {
    'call': '#FF4444',         # Call options (red)
    'put': '#00C851',          # Put options (green)
    'warning': '#FF8800'       # Current-price line (orange)
}


def _strike_gap(strikes) -> float:
    """Smallest distance between neighbouring strikes; sizes the bars on a numeric strike axis."""
    values = sorted(set(float(s) for s in strikes))
    gaps = [b - a for a, b in zip(values, values[1:]) if b > a]
    if gaps:
        return min(gaps)
    return values[0] * 0.01 if values and values[0] > 0 else 1.0


def _place_call_put_bars(chart_data_long: pd.DataFrame, call_label: str, strikes) -> pd.DataFrame:
    """Give each bar a start and end on the numeric strike axis: the call bar just left of its
    strike, the put bar just right of it, each 40% of the gap between strikes wide."""
    half = _strike_gap(strikes) * 0.4
    is_call = (chart_data_long['option_type'] == call_label).astype(float)
    chart_data_long['bar_start'] = chart_data_long['strike'] - half * is_call
    chart_data_long['bar_end'] = chart_data_long['strike'] + half * (1.0 - is_call)
    return chart_data_long


def _strike_axis(strikes) -> alt.Axis:
    """Numeric strike axis with its labels on strikes; the chart library shows as many as fit the width."""
    values = sorted(set(float(s) for s in strikes))
    return alt.Axis(values=values, format=',.0f', labelAngle=-45)


def _moneyness(strike: float, price: float, is_call: bool) -> str:
    """At, in or out of the money: within 2% of the price is ATM; a call is ITM below the price,
    a put is ITM above it."""
    if abs(strike - price) < price * 0.02:
        return 'ATM'
    if is_call:
        return 'ITM' if strike < price else 'OTM'
    return 'ITM' if strike > price else 'OTM'


def _add_bar_moneyness(chart_data_long: pd.DataFrame, call_label: str, price: float) -> pd.DataFrame:
    """Moneyness for each bar, from its own option type (the call bar and the put bar at one strike differ)."""
    chart_data_long['moneyness'] = [
        _moneyness(s, price, t == call_label)
        for s, t in zip(chart_data_long['strike'], chart_data_long['option_type'])
    ]
    return chart_data_long


class ChartDataManager:
    """Pre-processes the analytics report once for all charts."""

    def __init__(self, analytics_report: Dict[str, Any]):
        """Extract and pre-process all chart data once."""
        self.analytics_report = analytics_report
        self.df = analytics_report.get('option_chain_data', pd.DataFrame())

        if self.df.empty:
            self._init_empty()
            return

        # Extract common metrics once
        basic_metrics = analytics_report.get('basic_metrics', {})
        self.underlying_price = basic_metrics.get('underlying_price', 0)

        # Pre-process common DataFrame views
        self.calls_df = self.df[self.df['option_type'] == 'CE'].copy()
        self.puts_df = self.df[self.df['option_type'] == 'PE'].copy()
        self.strikes = sorted(self.df['strike'].unique())

    def _init_empty(self):
        """Initialize with empty data."""
        self.underlying_price = 0
        self.calls_df = pd.DataFrame()
        self.puts_df = pd.DataFrame()
        self.strikes = []

    def get_oi_distribution_data(self) -> pd.DataFrame:
        """Get pre-processed OI distribution data."""
        if self.df.empty:
            return pd.DataFrame()

        # Aggregate OI by strike and option type
        oi_data = self.df.groupby(['strike', 'option_type'])['oi'].sum().reset_index()
        oi_pivot = oi_data.pivot(index='strike', columns='option_type', values='oi').fillna(0).reset_index()

        result_data = []
        for _, row in oi_pivot.iterrows():
            strike = row['strike']
            result_data.append({
                'strike': strike,
                'call_oi': row.get('CE', 0),
                'put_oi': row.get('PE', 0)
            })

        return pd.DataFrame(result_data)

    def get_oi_change_distribution_data(self) -> pd.DataFrame:
        """Get pre-processed OI Change (6h) distribution data."""
        if self.df.empty or 'oi_change' not in self.df.columns:
            return pd.DataFrame()

        # Aggregate OI Change by strike and option type
        oi_change_data = self.df.groupby(['strike', 'option_type'])['oi_change'].sum().reset_index()
        oi_change_pivot = oi_change_data.pivot(index='strike', columns='option_type', values='oi_change').fillna(0).reset_index()

        result_data = []
        for _, row in oi_change_pivot.iterrows():
            strike = row['strike']
            result_data.append({
                'strike': strike,
                'call_oi_change': row.get('CE', 0),
                'put_oi_change': row.get('PE', 0)
            })

        return pd.DataFrame(result_data)

    def get_volume_distribution_data(self) -> pd.DataFrame:
        """Get pre-processed volume distribution data."""
        if self.df.empty:
            return pd.DataFrame()

        # Aggregate volume by strike and option type
        volume_data = self.df.groupby(['strike', 'option_type'])['volume'].sum().reset_index()
        volume_pivot = volume_data.pivot(index='strike', columns='option_type', values='volume').fillna(0).reset_index()

        result_data = []
        for _, row in volume_pivot.iterrows():
            strike = row['strike']
            result_data.append({
                'strike': strike,
                'call_volume': row.get('CE', 0),
                'put_volume': row.get('PE', 0)
            })

        return pd.DataFrame(result_data)

    def get_iv_smile_data(self) -> pd.DataFrame:
        """Get pre-processed IV smile data."""
        if self.df.empty or 'iv' not in self.df.columns:
            return pd.DataFrame()

        # Filter valid IV values
        iv_data = self.df[self.df['iv'] > 0].copy()

        if iv_data.empty:
            return pd.DataFrame()

        result_data = []
        for _, row in iv_data.iterrows():
            result_data.append({
                'strike': row['strike'],
                'option_type': row['option_type'],
                'iv': row['iv'] * 100,  # Delta sends a decimal (0.62 = 62%); shown as a percentage, as in the table
                'moneyness': _moneyness(row['strike'], self.underlying_price, row['option_type'] == 'CE')
            })

        return pd.DataFrame(result_data)

    def get_greeks_data(self, greek_name: str) -> pd.DataFrame:
        """Get pre-processed Greeks data."""
        if self.df.empty or greek_name.lower() not in self.df.columns:
            return pd.DataFrame()

        # Filter valid Greek values
        greek_data = self.df[self.df[greek_name.lower()] != 0].copy()

        if greek_data.empty:
            return pd.DataFrame()

        result_data = []
        for _, row in greek_data.iterrows():
            result_data.append({
                'strike': row['strike'],
                'option_type': row['option_type'],
                'greek_value': row[greek_name.lower()],
                'moneyness': _moneyness(row['strike'], self.underlying_price, row['option_type'] == 'CE')
            })

        return pd.DataFrame(result_data)

    def get_support_resistance_data(self) -> pd.DataFrame:
        """Get pre-processed support/resistance data: the three call strikes with the most open
        interest (resistance) and the three put strikes with the most (support)."""
        sr_data = self.analytics_report.get('support_resistance', {})

        if not sr_data:
            return pd.DataFrame()

        levels_data = []

        # Resistance levels (from calls)
        resistance_levels = sr_data.get('resistance_levels', [])
        resistance_oi = sr_data.get('resistance_oi', [])

        for i, level in enumerate(resistance_levels[:5]):  # Top 5
            oi = resistance_oi[i] if i < len(resistance_oi) else 0
            levels_data.append({
                'strike': level,
                'oi': oi,
                'level_type': 'Resistance',
                'strength': 'Strong' if i < 2 else 'Moderate',
                'distance_from_spot': abs(level - self.underlying_price) if self.underlying_price > 0 else 0
            })

        # Support levels (from puts)
        support_levels = sr_data.get('support_levels', [])
        support_oi = sr_data.get('support_oi', [])

        for i, level in enumerate(support_levels[:5]):  # Top 5
            oi = support_oi[i] if i < len(support_oi) else 0
            levels_data.append({
                'strike': level,
                'oi': oi,
                'level_type': 'Support',
                'strength': 'Strong' if i < 2 else 'Moderate',
                'distance_from_spot': abs(level - self.underlying_price) if self.underlying_price > 0 else 0
            })

        df = pd.DataFrame(levels_data)
        if df.empty:
            return df

        # Place each bar on the numeric strike axis: resistance just above its strike, support just
        # below it, so a strike that is both shows two bars side by side
        half = _strike_gap(self.strikes if len(self.strikes) > 1 else df['strike']) * 0.4
        is_resistance = (df['level_type'] == 'Resistance').astype(float)
        df['bar_start'] = df['strike'] - half * (1.0 - is_resistance)
        df['bar_end'] = df['strike'] + half * is_resistance
        df['zero'] = 0.0

        return df.sort_values('strike')

class OptionsVisualization:
    """
    Simple chart manager - no caching, fresh renders every time.
    """

    def _create_price_line(self, underlying_price: float) -> Optional[alt.Chart]:
        """Create a vertical current-price line on a numeric strike axis."""
        if underlying_price <= 0:
            return None

        price_line = alt.Chart(pd.DataFrame({'price': [underlying_price]})).mark_rule(
            color=COLORS['warning'],
            strokeWidth=2,
            strokeDash=[5, 5]
        ).encode(
            x=alt.X('price:Q', title='Strike Price'),
            tooltip=alt.Tooltip('price:Q', title='Current Price', format='.2f')
        )

        return price_line

    def create_oi_distribution_chart(self, chart_data: pd.DataFrame, underlying_price: float = 0) -> Optional[alt.Chart]:
        """Create Open Interest distribution visualization."""
        try:
            if chart_data.empty:
                return None

            # One row per bar: strike, option type, value
            chart_data_long = pd.melt(
                chart_data,
                id_vars=['strike'],
                value_vars=['call_oi', 'put_oi'],
                var_name='option_type',
                value_name='oi'
            )
            chart_data_long = _place_call_put_bars(chart_data_long, 'call_oi', chart_data['strike'])
            chart_data_long = _add_bar_moneyness(chart_data_long, 'call_oi', underlying_price)

            base = alt.Chart(chart_data_long).add_selection(
                alt.selection_interval(bind='scales', encodings=['x'])
            )

            # Calls left of each strike, puts right of it
            oi_bars = base.mark_bar(
                opacity=0.8,
                stroke='white',
                strokeWidth=0.5
            ).encode(
                x=alt.X('bar_start:Q', title='Strike Price', scale=alt.Scale(zero=False),
                        axis=_strike_axis(chart_data['strike'])),
                x2='bar_end:Q',
                y=alt.Y('oi:Q', title='Open Interest', scale=alt.Scale(type='sqrt')),
                y2=alt.datum(0),
                color=alt.Color(
                    'option_type:N',
                    title='Option Type',
                    scale=alt.Scale(
                        domain=['call_oi', 'put_oi'],
                        range=[COLORS['call'], COLORS['put']]
                    ),
                    legend=alt.Legend(title="Option Type")
                ),
                tooltip=[
                    alt.Tooltip('strike:O', title='Strike'),
                    alt.Tooltip('oi:Q', title='Open Interest', format=',.2f'),
                    alt.Tooltip('option_type:N', title='Type'),
                    alt.Tooltip('moneyness:N', title='Moneyness')
                ]
            ).properties(
                width=800,
                height=400,
                title=alt.TitleParams(
                    text="Open Interest Distribution - Calls vs Puts",
                    fontSize=16,
                    anchor='start'
                )
            )

            # Current-price line, at the price on the same numeric axis
            price_line = self._create_price_line(underlying_price)
            layered = (oi_bars + price_line) if price_line else oi_bars

            chart = layered.configure_view(
                strokeWidth=0
            )

            return chart

        except Exception as e:
            logger.error(f"Error creating OI distribution chart: {e}")
            return None

    def create_oi_change_distribution_chart(self, chart_data: pd.DataFrame, underlying_price: float = 0) -> Optional[alt.Chart]:
        """Create OI Change (6h) distribution visualization."""
        try:
            if chart_data.empty:
                return None

            # One row per bar: strike, option type, value
            chart_data_long = pd.melt(
                chart_data,
                id_vars=['strike'],
                value_vars=['call_oi_change', 'put_oi_change'],
                var_name='option_type',
                value_name='oi_change'
            )
            chart_data_long = _place_call_put_bars(chart_data_long, 'call_oi_change', chart_data['strike'])
            chart_data_long = _add_bar_moneyness(chart_data_long, 'call_oi_change', underlying_price)
            chart_data_long['change_type'] = chart_data_long['oi_change'].apply(
                lambda x: 'Increase' if x > 0 else ('Decrease' if x < 0 else 'No Change')
            )

            base = alt.Chart(chart_data_long).add_selection(
                alt.selection_interval(bind='scales', encodings=['x'])
            )

            # Calls left of each strike, puts right of it
            oi_change_bars = base.mark_bar(
                opacity=0.8,
                stroke='white',
                strokeWidth=0.5
            ).encode(
                x=alt.X('bar_start:Q', title='Strike Price', scale=alt.Scale(zero=False),
                        axis=_strike_axis(chart_data['strike'])),
                x2='bar_end:Q',
                y=alt.Y('oi_change:Q', title='OI Change (6h)', scale=alt.Scale(zero=True)),
                y2=alt.datum(0),
                color=alt.Color(
                    'option_type:N',
                    title='Option Type',
                    scale=alt.Scale(
                        domain=['call_oi_change', 'put_oi_change'],
                        range=[COLORS['call'], COLORS['put']]
                    ),
                    legend=alt.Legend(title="Option Type")
                ),
                tooltip=[
                    alt.Tooltip('strike:O', title='Strike'),
                    alt.Tooltip('oi_change:Q', title='OI Change (6h)', format='+,.0f'),
                    alt.Tooltip('option_type:N', title='Type'),
                    alt.Tooltip('change_type:N', title='Direction'),
                    alt.Tooltip('moneyness:N', title='Moneyness')
                ]
            ).properties(
                width=800,
                height=400,
                title=alt.TitleParams(
                    text="OI Change (6h) Distribution - New Positions vs Closures",
                    fontSize=16,
                    anchor='start'
                )
            )

            # Zero line for reference
            zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
                strokeWidth=1,
                strokeDash=[2, 2]
            ).encode(y='y:Q')

            # Current-price line, at the price on the same numeric axis
            price_line = self._create_price_line(underlying_price)
            layered = (oi_change_bars + zero_line + price_line) if price_line else (oi_change_bars + zero_line)

            chart = layered.configure_view(
                strokeWidth=0
            )

            return chart

        except Exception as e:
            logger.error(f"Error creating OI change distribution chart: {e}")
            return None

    def create_volume_distribution_chart(self, chart_data: pd.DataFrame, underlying_price: float = 0) -> Optional[alt.Chart]:
        """Create Volume distribution visualization."""
        try:
            if chart_data.empty:
                return None

            # One row per bar: strike, option type, value
            chart_data_long = pd.melt(
                chart_data,
                id_vars=['strike'],
                value_vars=['call_volume', 'put_volume'],
                var_name='option_type',
                value_name='volume'
            )
            chart_data_long = _place_call_put_bars(chart_data_long, 'call_volume', chart_data['strike'])
            chart_data_long = _add_bar_moneyness(chart_data_long, 'call_volume', underlying_price)

            base = alt.Chart(chart_data_long).add_selection(
                alt.selection_interval(bind='scales', encodings=['x'])
            )

            # Calls left of each strike, puts right of it
            volume_bars = base.mark_bar(
                opacity=0.8,
                stroke='white',
                strokeWidth=0.5
            ).encode(
                x=alt.X('bar_start:Q', title='Strike Price', scale=alt.Scale(zero=False),
                        axis=_strike_axis(chart_data['strike'])),
                x2='bar_end:Q',
                y=alt.Y('volume:Q', title='Trading Volume', scale=alt.Scale(type='sqrt')),
                y2=alt.datum(0),
                color=alt.Color(
                    'option_type:N',
                    title='Option Type',
                    scale=alt.Scale(
                        domain=['call_volume', 'put_volume'],
                        range=[COLORS['call'], COLORS['put']]
                    ),
                    legend=alt.Legend(title="Option Type")
                ),
                tooltip=[
                    alt.Tooltip('strike:O', title='Strike'),
                    alt.Tooltip('volume:Q', title='Volume', format=',.2f'),
                    alt.Tooltip('option_type:N', title='Type'),
                    alt.Tooltip('moneyness:N', title='Moneyness')
                ]
            ).properties(
                width=800,
                height=400,
                title=alt.TitleParams(
                    text="Volume Distribution - Calls vs Puts",
                    fontSize=16,
                    anchor='start'
                )
            )

            # Current-price line, at the price on the same numeric axis
            price_line = self._create_price_line(underlying_price)
            layered = (volume_bars + price_line) if price_line else volume_bars

            chart = layered.configure_view(
                strokeWidth=0
            )

            return chart

        except Exception as e:
            logger.error(f"Error creating volume distribution chart: {e}")
            return None

    def create_iv_smile_chart(self, chart_data: pd.DataFrame, underlying_price: float = 0) -> Optional[alt.Chart]:
        """Create IV smile curve visualization."""
        try:
            if chart_data.empty:
                return None

            base = alt.Chart(chart_data)

            # IV smile curves - separate lines for calls and puts
            iv_lines = base.mark_line(
                point=True,
                strokeWidth=3
            ).encode(
                x=alt.X('strike:Q', title='Strike Price'),
                y=alt.Y('iv:Q', title='Implied Volatility (%)', scale=alt.Scale(zero=False)),
                color=alt.Color(
                    'option_type:N',
                    title='Option Type',
                    scale=alt.Scale(
                        domain=['CE', 'PE'],
                        range=[COLORS['call'], COLORS['put']]
                    )                ),
                tooltip=[
                    alt.Tooltip('strike:Q', title='Strike'),
                    alt.Tooltip('iv:Q', title='IV', format='.2f'),
                    alt.Tooltip('option_type:N', title='Type'),
                    alt.Tooltip('moneyness:N', title='Moneyness')
                ]
            ).properties(
                width=600,
                height=300,
                title=alt.TitleParams(
                    text="IV Smile Curve",
                    fontSize=16,
                    anchor='start'
                )
            )

            # Current-price line, at the price on the same numeric axis
            price_line = self._create_price_line(underlying_price)
            layered = (iv_lines + price_line) if price_line else iv_lines

            chart = layered.configure_view(
                strokeWidth=0
            )

            return chart

        except Exception as e:
            logger.error(f"Error creating IV smile chart: {e}")
            return None

    def create_greek_distribution_chart(self, chart_data: pd.DataFrame, greek_name: str) -> Optional[alt.Chart]:
        """Create Greek distribution visualization."""
        try:
            if chart_data.empty:
                return None

            base = alt.Chart(chart_data).add_selection(
                alt.selection_interval(bind='scales', encodings=['x'])
            )

            # Tight X-axis domain from the data: 2% padding instead of Altair's 5%
            min_strike = chart_data['strike'].min()
            max_strike = chart_data['strike'].max()
            strike_padding = (max_strike - min_strike) * 0.02
            x_domain = [min_strike - strike_padding, max_strike + strike_padding]

            # Greek distribution scatter plot
            greek_scatter = base.mark_circle(
                size=100,
                opacity=0.8,
                stroke='white',
                strokeWidth=1
            ).encode(
                x=alt.X('strike:Q', title='Strike Price', scale=alt.Scale(domain=x_domain)),
                y=alt.Y('greek_value:Q', title=f'{greek_name.title()} Value', scale=alt.Scale(zero=False)),
                color=alt.Color(
                    'option_type:N',
                    title='Option Type',
                    scale=alt.Scale(
                        domain=['CE', 'PE'],
                        range=[COLORS['call'], COLORS['put']]
                    )                ),
                tooltip=[
                    alt.Tooltip('strike:Q', title='Strike'),
                    alt.Tooltip('greek_value:Q', title=f'{greek_name.title()}', format='.4f'),
                    alt.Tooltip('option_type:N', title='Type'),
                    alt.Tooltip('moneyness:N', title='Moneyness')
                ]
            ).properties(
                width=350,
                height=300,
                title=alt.TitleParams(
                    text=f"{greek_name.title()} Distribution by Strike",
                    fontSize=14,
                    anchor='start'
                )
            )

            chart = greek_scatter.configure_view(
                strokeWidth=0
            )

            return chart

        except Exception as e:
            logger.error(f"Error creating {greek_name} distribution chart: {e}")
            return None

    def create_support_resistance_chart(self, chart_data: pd.DataFrame, underlying_price: float) -> Optional[alt.Chart]:
        """Create support and resistance levels visualization."""
        try:
            if chart_data.empty:
                return None

            # Horizontal bars on a numeric strike axis (vertical)
            base = alt.Chart(chart_data)

            sr_bars = base.mark_bar(
                opacity=0.8,
                stroke='white',
                strokeWidth=1
            ).encode(
                y=alt.Y('bar_start:Q', title='Strike Price', scale=alt.Scale(zero=False),
                        axis=alt.Axis(values=sorted(chart_data['strike'].unique()), format=',.0f')),
                y2='bar_end:Q',
                x=alt.X('zero:Q', title='Open Interest', scale=alt.Scale(type='sqrt')),
                x2='oi:Q',
                color=alt.Color(
                    'level_type:N',
                    title='Level Type',
                    scale=alt.Scale(
                        domain=['Support', 'Resistance'],
                        range=[COLORS['put'], COLORS['call']]
                    )                ),
                tooltip=[
                    alt.Tooltip('strike:O', title='Strike'),
                    alt.Tooltip('oi:Q', title='Open Interest', format=',.2f'),
                    alt.Tooltip('level_type:N', title='Type'),
                    alt.Tooltip('strength:N', title='Strength'),
                    alt.Tooltip('distance_from_spot:Q', title='Distance from Spot', format='.0f')
                ]
            ).properties(
                width=600,
                height=400,
                title=alt.TitleParams(
                    text="Support & Resistance Levels",
                    fontSize=16,
                    anchor='start'
                )
            )

            # Current-price line, at the price on the same numeric strike axis
            if underlying_price > 0:
                price_line = alt.Chart(pd.DataFrame({'price': [underlying_price]})).mark_rule(
                    color=COLORS['warning'],
                    strokeWidth=3,
                    strokeDash=[8, 4]
                ).encode(
                    y=alt.Y('price:Q', title='Strike Price')
                )
                layered = sr_bars + price_line
            else:
                layered = sr_bars

            chart = layered.configure_view(
                strokeWidth=0
            )

            return chart

        except Exception as e:
            logger.error(f"Error creating support/resistance chart: {e}")
            return None

    def _display_chart_with_data(self, chart_type: str, chart_creator_func) -> None:
        """Display one chart."""
        try:
            with st.spinner(f"Creating {chart_type.replace('_', ' ').title()} chart..."):
                chart = chart_creator_func()

                if chart is not None:
                    st.altair_chart(chart, use_container_width=True)

        except Exception as e:
            logger.error(f"Error displaying {chart_type} chart: {e}")

    def create_comprehensive_dashboard(self, analytics_report: Dict[str, Any]) -> None:
        """
        Create the options analytics dashboard with all charts.

        Args:
            analytics_report: Analytics report from integrated.py
        """
        try:
            if not self._validate_analytics_report(analytics_report):
                return

            data_manager = ChartDataManager(analytics_report)

            # Get pre-processed data for all charts
            iv_data = data_manager.get_iv_smile_data()
            oi_data = data_manager.get_oi_distribution_data()
            oi_change_data = data_manager.get_oi_change_distribution_data()
            volume_data = data_manager.get_volume_distribution_data()
            sr_data = data_manager.get_support_resistance_data()

            # Greeks data
            delta_data = data_manager.get_greeks_data('Delta')
            gamma_data = data_manager.get_greeks_data('Gamma')
            vega_data = data_manager.get_greeks_data('Vega')
            theta_data = data_manager.get_greeks_data('Theta')

            underlying_price = data_manager.underlying_price

            self._display_chart_with_data('iv_smile',
                lambda: self.create_iv_smile_chart(iv_data, underlying_price))

            # Two-column layout for OI analysis
            col1, col2 = st.columns(2)

            with col1:
                self._display_chart_with_data('oi_distribution',
                    lambda: self.create_oi_distribution_chart(oi_data, underlying_price))

            with col2:
                self._display_chart_with_data('oi_change_distribution',
                    lambda: self.create_oi_change_distribution_chart(oi_change_data, underlying_price))

            # Second row: Volume and Support/Resistance
            col1, col2 = st.columns(2)

            with col1:
                self._display_chart_with_data('volume_distribution',
                    lambda: self.create_volume_distribution_chart(volume_data, underlying_price))

            with col2:
                self._display_chart_with_data('support_resistance',
                    lambda: self.create_support_resistance_chart(sr_data, underlying_price))

            # Greeks Distribution Charts (2x2 grid)
            col1, col2 = st.columns(2)

            with col1:
                # Delta and Gamma
                self._display_chart_with_data('delta_distribution',
                    lambda: self.create_greek_distribution_chart(delta_data, 'Delta'))

                self._display_chart_with_data('gamma_distribution',
                    lambda: self.create_greek_distribution_chart(gamma_data, 'Gamma'))

            with col2:
                # Vega and Theta
                self._display_chart_with_data('vega_distribution',
                    lambda: self.create_greek_distribution_chart(vega_data, 'Vega'))

                self._display_chart_with_data('theta_distribution',
                    lambda: self.create_greek_distribution_chart(theta_data, 'Theta'))

        except Exception as e:
            logger.error(f"Error creating comprehensive dashboard: {e}")

    def _validate_analytics_report(self, analytics_report: Dict[str, Any]) -> bool:
        """Validate analytics report has required structure."""
        if not analytics_report or analytics_report.get('error'):
            return False

        required_keys = ['basic_metrics', 'option_chain_data']
        for key in required_keys:
            if key not in analytics_report:
                logger.error(f"Missing required key in analytics report: {key}")
                return False

        # Check if DataFrame is valid
        df = analytics_report.get('option_chain_data', pd.DataFrame())
        if df.empty:
            logger.warning("Option chain dataframe is empty")
            return False

        # Check for required columns
        required_columns = ['strike', 'option_type', 'oi', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns in dataframe: {missing_columns}")
            return False

        return True
