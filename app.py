"""
CryptoChain - Advanced Options Analytics Platform
Consolidated Main Application with All UI Components
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import os
import logging
from typing import Dict, List, Optional, Tuple

# Import simplified Delta client with integrated analytics
from integrated import DeltaExchangeClient

# Import visualization (keeping existing charts)
from visualization import OptionsVisualization

# Setup logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="CryptoChain - Crypto",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS AND STYLING
# ============================================================================

def load_css():
    """Load external CSS file."""
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    if os.path.exists(css_path):
        with open(css_path, 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.warning("CSS file not found. Using default styles.")

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session_state():
    """Initialize session state for Delta-only application."""
    defaults = {
        # Data storage - simplified like legacy
        'analytics_report': {},  # Current analytics report
        
        # Delta client only
        'delta_client': None,
        'visualization_engine': None,
        
        # Simplified crypto asset settings
        'selected_asset': 'Select...',
        'available_expiries': [],
        'selected_expiry': 'Select...',
        
        # Strike range setting
        'strike_range': 10,
        
        # View selection
        'selected_view_mode': 'Select...',
        
        # Auto-refresh settings
        'auto_refresh_interval': 'Off',
        'refresh_interval_seconds': None,
        'last_refresh_time': 0,
        'refresh_in_progress': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Initialize visualization engine only
    if st.session_state.visualization_engine is None:
        st.session_state.visualization_engine = OptionsVisualization()
    
    # Initialize Delta client
    if st.session_state.delta_client is None:
        st.session_state.delta_client = DeltaExchangeClient()
        logger.info("Delta client initialized")

# ============================================================================
# UNIFIED DATA MANAGEMENT
# ============================================================================

class UnifiedDataManager:
    """Centralized data management."""

    @staticmethod
    def get_analytics_report():
        """Get analytics report - simplified like legacy."""
        return st.session_state.get('analytics_report', {})
    
    @staticmethod
    def update_unified_data(report):
        """Store analytics report - simplified like legacy."""
        if report and 'error' not in report:
            # Direct storage like legacy - no caching complexity
            st.session_state.analytics_report = report
            return True
        return False
    
    @staticmethod
    def is_data_available():
        """Check if valid data is available - simplified like legacy."""
        report = UnifiedDataManager.get_analytics_report()
        return bool(report and 'option_chain_data' in report and not report['option_chain_data'].empty)

# ============================================================================
# CONSOLIDATED UI COMPONENTS (formerly components.py)
# ============================================================================

def show_no_data_warning(source_name: str, instructions: str) -> None:
    """Show warning when no data is available."""
    st.warning(f"📊 No {source_name} Data Available")
    st.info(instructions)

# ============================================================================
# CONSOLIDATED OPTION CHAIN TABLE BUILDER (formerly option_chain.py)
# ============================================================================


def calculate_strike_level_metrics(analytics_report: Dict) -> Dict[float, Dict[str, float]]:
    """Calculate strike-level metrics from analytics report - SINGLE SOURCE OF TRUTH."""
    df = analytics_report.get('option_chain_data', pd.DataFrame())
    if df.empty:
        return {}
    
    strike_metrics = {}
    strikes = df['strike'].unique()

    for strike in strikes:
        call_data = df[(df['strike'] == strike) & (df['option_type'] == 'CE')]
        put_data = df[(df['strike'] == strike) & (df['option_type'] == 'PE')]
        
        # Safe value extraction with defaults
        call_oi = call_data['oi'].iloc[0] if not call_data.empty else 0
        put_oi = put_data['oi'].iloc[0] if not put_data.empty else 0
        call_volume = call_data['volume'].iloc[0] if not call_data.empty else 0
        put_volume = put_data['volume'].iloc[0] if not put_data.empty else 0

        # Calculate metrics
        strike_metrics[strike] = {
            'pcr_oi': put_oi / call_oi if call_oi > 0 else 0,
            'pcr_volume': put_volume / call_volume if call_volume > 0 else 0
        }
    
    return strike_metrics

def format_oi_change_value(value: float) -> str:
    """Format OI change values with K/M scaling only."""
    if pd.isna(value) or value == 0:
        return '0'
    
    # Format with K/M scaling
    if abs(value) >= 1_000_000:
        value_scaled = value / 1_000_000
        value_formatted = f"{value_scaled:.1f}M"
    elif abs(value) >= 1_000:
        value_scaled = value / 1_000
        value_formatted = f"{value_scaled:.0f}K"
    else:
        value_formatted = f"{value:.0f}"
    
    # Add proper sign and color
    if value > 0:
        return f'<span style="color:#059669">+{value_formatted}</span>'
    else:
        return f'<span style="color:#dc2626">{value_formatted}</span>'

def format_pcr_combined(pcr_oi: float, pcr_vol: float) -> str:
    """Format combined PCR with OI on top and Vol in brackets underneath."""
    if pd.isna(pcr_oi) or pcr_oi == 0:
        oi_formatted = '-'
    else:
        oi_formatted = f'{pcr_oi:.3f}'
    
    if pd.isna(pcr_vol) or pcr_vol == 0:
        vol_formatted = '(-)'
    else:
        vol_formatted = f'({pcr_vol:.3f})'
    
    return f'{oi_formatted}<br><small style="color:#000">{vol_formatted}</small>'

def format_volume_with_value(volume: float, volume_value: float) -> str:
    """Format Volume with USD value on top and volume in coins (BTC or ETH) in brackets underneath."""
    # If we have volume but no value, still show the volume
    if pd.isna(volume) or volume == 0:
        return '-'
    
    if pd.isna(volume_value) or volume_value == 0:
        # Show volume even if value calculation failed
        return f'${0:.0f}<br><small style="color:#000">({volume:.2f})</small>'
    
    # Format USD value with appropriate scaling (K/M)
    if volume_value >= 1_000_000:
        value_formatted = f"${volume_value/1_000_000:.1f}M"
    elif volume_value >= 1_000:
        value_formatted = f"${volume_value/1_000:.1f}K"
    else:
        value_formatted = f"${volume_value:.0f}"
    
    # Format volume in coins in brackets underneath (no scaling for coins)
    if pd.isna(volume) or volume == 0:
        volume_formatted = '(-)'
    else:
        volume_formatted = f'({volume:.2f})'
    
    return f'{value_formatted}<br><small style="color:#000">{volume_formatted}</small>'


def format_oi_with_value(oi: float, oi_value_usd: float) -> str:
    """Format OI with USD value on top and OI in coins (BTC or ETH) in brackets underneath."""
    # If we have OI but no USD value, still show the OI in proper format
    if pd.isna(oi) or oi == 0:
        return '-'
    
    if pd.isna(oi_value_usd) or oi_value_usd == 0:
        # Show OI even if USD value calculation failed
        return f'${0:.0f}<br><small style="color:#000">({oi:.2f})</small>'
    
    # Format USD value with appropriate scaling (K/M), as in the volume column
    if oi_value_usd >= 1_000_000:
        usd_formatted = f"${oi_value_usd/1_000_000:.1f}M"
    elif oi_value_usd >= 1_000:
        usd_formatted = f"${oi_value_usd/1_000:.1f}K"
    else:
        usd_formatted = f"${oi_value_usd:.0f}"
    
    # Format OI in coins in brackets underneath (no M scaling for coins)
    if pd.isna(oi) or oi == 0:
        oi_formatted = '(-)'
    else:
        oi_formatted = f'({oi:.2f})'
    
    return f'{usd_formatted}<br><small style="color:#000">{oi_formatted}</small>'

def format_numeric_value(value: float, column_id: str, strike: float = 0) -> str:
    """Format numeric values with standardized Indian formatting."""
    if pd.isna(value):
        return '-'
    
    # Handle numpy types and regular Python types
    if isinstance(value, (int, float, np.integer, np.floating)):
        if column_id == 'oi':
            # Calculate OI value (oi * strike price)
            calculated_oi_value = value * strike if strike > 0 else 0
            return format_oi_with_value(value, calculated_oi_value)
        elif column_id == 'volume':
            # Calculate volume value (volume * strike price)
            volume_value = value * strike if strike > 0 else 0
            return format_volume_with_value(value, volume_value)
        elif column_id == 'oi_change':
            return format_oi_change_value(value)
        elif column_id == 'last_price':
            return f'{value:.2f}' if value > 0 else '-'
        elif column_id == 'iv':
            return f'{value * 100:.2f}' if value > 0 else '-'
        else:
            return f'{value:.2f}'
    
    return str(value)

def load_css_styles() -> str:
    """Load CSS from external file."""
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    try:
        with open(css_path, 'r') as f:
            return f"<style>\n{f.read()}\n</style>"
    except FileNotFoundError:
        st.warning("CSS file not found. Using minimal inline styles.")
        return "<style>.option-table { border-collapse: collapse; width: 100%; }</style>"

def calculate_scoring_data(df: pd.DataFrame) -> Dict:
    """Calculate scoring data for highlighting top values SEPARATELY for calls and puts."""
    scoring_data = {
        'oi_scores': {},
        'volume_scores': {},
        'oi_change_scores': {}
    }
    
    # Separate calls and puts
    calls_df = df[df['option_type'] == 'CE']
    puts_df = df[df['option_type'] == 'PE']
    
    # Calculate OI scores SEPARATELY for calls and puts (top 3 each)
    for option_df, option_type in [(calls_df, 'CE'), (puts_df, 'PE')]:
        oi_values = []
        for _, row in option_df.iterrows():
            oi_value = row.get('oi', 0) * row.get('strike', 0) if row.get('oi', 0) > 0 and row.get('strike', 0) > 0 else 0
            if oi_value > 0:
                oi_values.append((oi_value, row.get('strike', 0)))
        
        oi_values.sort(key=lambda x: x[0], reverse=True)
        for i, (value, strike) in enumerate(oi_values[:3]):
            key = f"{strike}_{option_type}"
            if i == 0:
                scoring_data['oi_scores'][key] = 'first'  # Dark Green
            elif i == 1:
                scoring_data['oi_scores'][key] = 'second'  # Dark Yellow
            elif i == 2:
                scoring_data['oi_scores'][key] = 'third'   # Blue border
    
    # Calculate Volume scores SEPARATELY for calls and puts (top 3 each)
    for option_df, option_type in [(calls_df, 'CE'), (puts_df, 'PE')]:
        volume_values = []
        for _, row in option_df.iterrows():
            volume_value = row.get('volume', 0) * row.get('strike', 0) if row.get('volume', 0) > 0 and row.get('strike', 0) > 0 else 0
            if volume_value > 0:
                volume_values.append((volume_value, row.get('strike', 0)))
        
        volume_values.sort(key=lambda x: x[0], reverse=True)
        for i, (value, strike) in enumerate(volume_values[:3]):
            key = f"{strike}_{option_type}"
            if i == 0:
                scoring_data['volume_scores'][key] = 'first'  # Dark Green
            elif i == 1:
                scoring_data['volume_scores'][key] = 'second'  # Dark Yellow
            elif i == 2:
                scoring_data['volume_scores'][key] = 'third'   # Blue border
    
    # Calculate OI Change scores SEPARATELY for calls and puts (highest positive and most negative each)
    for option_df, option_type in [(calls_df, 'CE'), (puts_df, 'PE')]:
        oi_changes = []
        for _, row in option_df.iterrows():
            oi_change = row.get('oi_change', 0)
            if oi_change != 0:
                oi_changes.append((oi_change, row.get('strike', 0)))
        
        if oi_changes:
            oi_changes.sort(key=lambda x: x[0], reverse=True)
            # Highest positive (green border)
            if oi_changes[0][0] > 0:
                key = f"{oi_changes[0][1]}_{option_type}"
                scoring_data['oi_change_scores'][key] = 'positive'
            
            # Most negative (red border)
            if oi_changes[-1][0] < 0:
                key = f"{oi_changes[-1][1]}_{option_type}"
                scoring_data['oi_change_scores'][key] = 'negative'
    
    return scoring_data

def get_cell_styling(col_id: str, strike: float, option_type: str, scoring_data: Dict) -> str:
    """Get CSS class for cell styling based on scoring data."""
    key = f"{strike}_{option_type}"
    
    if col_id == 'oi':
        if key in scoring_data['oi_scores']:
            score = scoring_data['oi_scores'][key]
            if score == 'first':
                return ' style="background-color: #166534; color: #000000; font-weight: bold; font-size: 1.1em;"'  # DARK green with black bold text
            elif score == 'second':
                return ' style="background-color: #ca8a04; color: #000000; font-weight: bold; font-size: 1.1em;"'  # DARK yellow with black bold text
            elif score == 'third':
                return ' style="border: 2px solid #3b82f6; color: #000000; font-weight: bold; font-size: 1.1em;"'  # Blue border with black bold text
    
    elif col_id == 'volume':
        if key in scoring_data['volume_scores']:
            score = scoring_data['volume_scores'][key]
            if score == 'first':
                return ' style="background-color: #166534; color: #000000; font-weight: bold; font-size: 1.1em;"'  # DARK green with black bold text
            elif score == 'second':
                return ' style="background-color: #ca8a04; color: #000000; font-weight: bold; font-size: 1.1em;"'  # DARK yellow with black bold text
            elif score == 'third':
                return ' style="border: 2px solid #3b82f6; color: #000000; font-weight: bold; font-size: 1.1em;"'  # Blue border with black bold text
    
    elif col_id == 'oi_change':
        if key in scoring_data['oi_change_scores']:
            score = scoring_data['oi_change_scores'][key]
            if score == 'positive':
                return ' style="border: 2px solid #22c55e; color: #000000; font-weight: bold; font-size: 1.1em;"'  # Green border with black bold text
            elif score == 'negative':
                return ' style="border: 2px solid #ef4444; color: #000000; font-weight: bold; font-size: 1.1em;"'  # Red border with black bold text
    
    return ''

def build_unified_markets_table(df: pd.DataFrame, analytics_report: Dict) -> str:
    """Build unified HTML table with hardcoded column layout."""
    if df.empty:
        return "<p>No data available for option chain table</p>"
    
    # Calculate scoring data for highlighting
    scoring_data = calculate_scoring_data(df)
    
    # Extract metrics from analytics report
    underlying_price = analytics_report.get('basic_metrics', {}).get('underlying_price', 0)
    
    # Prepare data
    calls_df = df[df['option_type'] == 'CE'].sort_values('strike')
    puts_df = df[df['option_type'] == 'PE'].sort_values('strike')
    strikes = sorted(df['strike'].unique())
    
    # Calculate strike-level metrics
    strike_metrics = calculate_strike_level_metrics(analytics_report)
    
    # HARDCODED COLUMN LAYOUT
    # Symmetric: LTP, Volume, OI, OI Change, IV
    symmetric_display_columns = ['last_price', 'volume', 'oi', 'oi_change', 'iv']

    # Left-Only: Combined PCR column only
    left_only_columns = ['pcr_combined']

    # Filter columns that exist in dataframe
    symmetric_display_columns = [col for col in symmetric_display_columns if col in df.columns]
    
    # Extract ALL totals from pre-calculated basic metrics - ZERO REDUNDANT CALCULATION
    basic_metrics = analytics_report.get('basic_metrics', {})
    
    # Calculate OI change totals once from DataFrame
    total_call_oi_change = int(calls_df['oi_change'].sum()) if 'oi_change' in calls_df.columns and not calls_df.empty else 0
    total_put_oi_change = int(puts_df['oi_change'].sum()) if 'oi_change' in puts_df.columns and not puts_df.empty else 0
    
    # Calculate volume values for totals using new logic (volume * strike)
    try:
        total_call_volume_value = (calls_df['volume'] * calls_df['strike']).sum() if 'volume' in calls_df.columns and 'strike' in calls_df.columns and not calls_df.empty else 0
    except (KeyError, TypeError):
        total_call_volume_value = 0
        
    try:
        total_put_volume_value = (puts_df['volume'] * puts_df['strike']).sum() if 'volume' in puts_df.columns and 'strike' in puts_df.columns and not puts_df.empty else 0
    except (KeyError, TypeError):
        total_put_volume_value = 0
    
    # Calculate OI values for totals using new logic (oi * strike)
    try:
        total_call_oi_value = (calls_df['oi'] * calls_df['strike']).sum() if 'oi' in calls_df.columns and 'strike' in calls_df.columns and not calls_df.empty else 0
    except (KeyError, TypeError):
        total_call_oi_value = 0
        
    try:
        total_put_oi_value = (puts_df['oi'] * puts_df['strike']).sum() if 'oi' in puts_df.columns and 'strike' in puts_df.columns and not puts_df.empty else 0
    except (KeyError, TypeError):
        total_put_oi_value = 0
    
    calls_totals = {
        'oi': basic_metrics.get('total_call_oi', 0),
        'oi_value': total_call_oi_value,
        'oi_change': total_call_oi_change,
        'volume': basic_metrics.get('total_call_volume', 0),
        'volume_value': total_call_volume_value
    }
    
    puts_totals = {
        'oi': basic_metrics.get('total_put_oi', 0),
        'oi_value': total_put_oi_value,
        'oi_change': total_put_oi_change,
        'volume': basic_metrics.get('total_put_volume', 0),
        'volume_value': total_put_volume_value
    }
    
    # Prepare strikes with underlying price insertion
    enhanced_strikes = prepare_enhanced_strikes(strikes, underlying_price)
    
    # Start building HTML
    css = load_css_styles()
    
    html = css + f'<div class="option-table-container">'
    html += '<table class="option-table"><thead><tr>'
    
    # Build header
    html += build_table_header(left_only_columns, symmetric_display_columns)
    html += '</tr></thead><tbody>'
    
    # Build data rows
    html += build_table_data_rows(enhanced_strikes, calls_df, puts_df,
                                 left_only_columns, symmetric_display_columns,
                                 strike_metrics, scoring_data)
    
    # Build totals row
    html += build_table_totals_row(left_only_columns, symmetric_display_columns,
                                  calls_totals, puts_totals)
    
    html += '</tbody></table></div>'
    
    return html

def prepare_enhanced_strikes(strikes: List[float], underlying_price: float) -> List[Tuple[str, float]]:
    """Prepare strikes list with underlying price insertion."""
    enhanced_strikes = []
    underlying_inserted = False
    
    for i, strike in enumerate(strikes):
        # Insert underlying price row if it falls between strikes
        if not underlying_inserted and underlying_price > 0:
            if i == 0 and underlying_price < strike:
                enhanced_strikes.append(('underlying', underlying_price))
                underlying_inserted = True
            elif i > 0 and strikes[i-1] < underlying_price < strike:
                enhanced_strikes.append(('underlying', underlying_price))
                underlying_inserted = True
        
        enhanced_strikes.append(('strike', strike))
    
    # Insert at end if not inserted and underlying is above all strikes
    if not underlying_inserted and underlying_price > 0 and strikes and underlying_price > strikes[-1]:
        enhanced_strikes.append(('underlying', underlying_price))
    
    return enhanced_strikes

def build_table_header(left_only_columns: List[str], symmetric_display_columns: List[str]) -> str:
    """Build header row with hardcoded column labels."""
    # Hardcoded column labels
    column_labels = {
        'last_price': 'LTP',
        'volume': 'Volume',
        'oi': 'OI',
        'oi_change': 'OI Change (6h)',
        'iv': 'IV',
        'pcr_combined': 'PCR (OI/Vol)'
    }
    
    html = ""
    
    # Left-only headers
    for col_id in left_only_columns:
        label = column_labels.get(col_id, col_id.upper())
        html += f'<th class="left-only-header">{label}</th>'
    
    # Call headers (symmetric, reversed for symmetry)
    for col_id in reversed(symmetric_display_columns):
        label = column_labels.get(col_id, col_id.upper())
        html += f'<th class="call-column">{label} (CE)</th>'
    
    # Strike header
    html += '<th class="strike-column">STRIKE</th>'
    
    # Put headers (symmetric)
    for col_id in symmetric_display_columns:
        label = column_labels.get(col_id, col_id.upper())
        html += f'<th class="put-column">{label} (PE)</th>'

    return html

def build_table_data_rows(enhanced_strikes: List[Tuple[str, float]], 
                         calls_df: pd.DataFrame, puts_df: pd.DataFrame,
                         left_only_columns: List[str], symmetric_display_columns: List[str],
                         strike_metrics: Dict, scoring_data: Dict) -> str:
    """Build data rows for option chain table."""
    html = ""
    
    for row_type, strike_value in enhanced_strikes:
        if row_type == 'underlying':
            # Underlying price row with special styling
            html += '<tr class="underlying-row">'
            
            # Left-only columns (empty, no borders internally)
            for _ in left_only_columns:
                html += '<td class="left-only-column" style="border-right: none; border-left: 1px solid #ccc;"></td>'
            
            # Call columns - merged with gradient (no internal borders)
            call_count = len(symmetric_display_columns)
            if call_count > 0:
                html += f'<td class="call-column" colspan="{call_count}" style="border-right: none; border-left: none; background: linear-gradient(to left, #e0f2fe, transparent); text-align: center;"></td>'
            
            # Strike column with underlying price (match CSS blue border color)
            html += f'<td class="strike-column" style="border-top: 2px solid #3b82f6; border-bottom: 2px solid #3b82f6; border-left: none; border-right: none; font-weight: bold; background-color: #f0f9ff;">{strike_value:,.2f}</td>'
            
            # Put columns - merged with gradient (no internal borders)
            put_count = len(symmetric_display_columns)
            if put_count > 0:
                html += f'<td class="put-column" colspan="{put_count}" style="border-left: none; border-right: none; background: linear-gradient(to right, #e0f2fe, transparent); text-align: center;"></td>'

            html += '</tr>'
            
        else:
            # Regular strike row
            strike = strike_value
            html += f'<tr>'
            
            # Left-only columns
            for col_id in left_only_columns:
                html += '<td class="left-only-column">'
                if col_id == 'pcr_combined' and strike in strike_metrics:
                    pcr_oi = strike_metrics[strike].get('pcr_oi', 0)
                    pcr_vol = strike_metrics[strike].get('pcr_volume', 0)
                    html += format_pcr_combined(pcr_oi, pcr_vol)
                else:
                    html += '-'
                html += '</td>'
            
            # Call data (reversed)
            call_data = calls_df[calls_df['strike'] == strike]
            for col_id in reversed(symmetric_display_columns):
                # Get styling for this cell
                cell_style = get_cell_styling(col_id, strike, 'CE', scoring_data)
                html += f'<td class="call-column"{cell_style}>'
                
                if not call_data.empty and col_id in call_data.columns:
                    value = call_data[col_id].iloc[0]
                    html += format_numeric_value(value, col_id, strike)
                else:
                    html += '-'
                html += '</td>'
            
            # Strike column
            html += f'<td class="strike-column">{strike:.0f}</td>'
            
            # Put data
            put_data = puts_df[puts_df['strike'] == strike]
            for col_id in symmetric_display_columns:
                # Get styling for this cell
                cell_style = get_cell_styling(col_id, strike, 'PE', scoring_data)
                html += f'<td class="put-column"{cell_style}>'
                
                if not put_data.empty and col_id in put_data.columns:
                    value = put_data[col_id].iloc[0]
                    html += format_numeric_value(value, col_id, strike)
                else:
                    html += '-'
                html += '</td>'

            html += '</tr>'
    
    return html

def build_table_totals_row(left_only_columns: List[str], symmetric_display_columns: List[str],
                          calls_totals: Dict, puts_totals: Dict) -> str:
    """Build totals row for option chain table."""
    html = '<tr class="totals-row">'
    
    # Left-only totals (empty)
    for _ in left_only_columns:
        html += '<td class="left-only-column">-</td>'
    
    # Call totals (reversed)
    for col_id in reversed(symmetric_display_columns):
        html += '<td class="call-column">'
        if col_id == 'oi':
            html += format_oi_with_value(calls_totals["oi"], calls_totals["oi_value"])
        elif col_id == 'oi_change':
            html += format_oi_change_value(calls_totals['oi_change'])
        elif col_id == 'volume':
            html += format_volume_with_value(calls_totals["volume"], calls_totals["volume_value"])
        else:
            html += '-'
        html += '</td>'
    
    # Strike column
    html += '<td class="strike-column">TOTALS</td>'
    
    # Put totals
    for col_id in symmetric_display_columns:
        html += '<td class="put-column">'
        if col_id == 'oi':
            html += format_oi_with_value(puts_totals["oi"], puts_totals["oi_value"])
        elif col_id == 'oi_change':
            html += format_oi_change_value(puts_totals['oi_change'])
        elif col_id == 'volume':
            html += format_volume_with_value(puts_totals["volume"], puts_totals["volume_value"])
        else:
            html += '-'
        html += '</td>'

    html += '</tr>'
    return html


# ============================================================================
# DATA PROVIDER FUNCTIONS
# ============================================================================

def initialize_delta_client() -> Optional[DeltaExchangeClient]:
    """Initialize Delta Exchange client."""
    try:
        client = DeltaExchangeClient()
        st.session_state.delta_client = client
        logger.info("Delta client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Error initializing Delta client: {e}")
        st.error(f"Failed to initialize Delta client: {e}")
        return None

def fetch_crypto_data() -> bool:
    """Fetch data from Delta Exchange using integrated analytics."""
    try:
        if not st.session_state.delta_client:
            if not initialize_delta_client():
                return False
        
        # Validate required selections for crypto
        if (st.session_state.selected_expiry == 'Select...' or 
            st.session_state.selected_asset == 'Select...'):
            st.error("Please select crypto asset and expiry before fetching data.")
            return False
        
        # Extract asset symbol from selection
        asset_symbol = st.session_state.selected_asset
        
        with st.spinner(f"Fetching {asset_symbol} options data..."):
            # Use Delta's integrated analytics - returns complete report with DataFrame
            report = st.session_state.delta_client.generate_comprehensive_report(
                asset=asset_symbol,
                expiry=st.session_state.selected_expiry
            )
            
            if 'error' not in report:
                # Apply strike range filter if needed
                if st.session_state.strike_range and st.session_state.strike_range != 'All':
                    df = report.get('option_chain_data', pd.DataFrame())
                    if not df.empty:
                        underlying_price = df['underlying_price'].iloc[0] if 'underlying_price' in df.columns else 0
                        if underlying_price > 0:
                            strikes = sorted(df['strike'].unique())
                            # Find ATM strike
                            atm_strike = min(strikes, key=lambda x: abs(x - underlying_price))
                            atm_index = strikes.index(atm_strike)
                            
                            # Calculate range
                            range_value = st.session_state.strike_range
                            start_idx = max(0, atm_index - range_value)
                            end_idx = min(len(strikes), atm_index + range_value + 1)
                            
                            selected_strikes = strikes[start_idx:end_idx]
                            filtered_df = df[df['strike'].isin(selected_strikes)]
                            
                            # Update report with filtered data and recalculate analytics
                            filtered_report = st.session_state.delta_client._recalculate_analytics_for_filtered_data(
                                filtered_df, asset_symbol, st.session_state.selected_expiry
                            )
                            report = filtered_report
                
                # Store complete analytics report
                success = UnifiedDataManager.update_unified_data(report)
                if success:
                    return True
                else:
                    st.error("Failed to process fetched crypto data")
                    return False
            else:
                st.warning(f"No data received for {asset_symbol}: {report.get('error', 'Unknown error')}")
                return False
                
    except Exception as e:
        logger.error(f"Error fetching crypto data: {e}")
        st.error(f"Failed to fetch crypto data: {e}")
        return False

# ============================================================================
# SIDEBAR CONTROLS
# ============================================================================

def render_sidebar():
    """Render simplified crypto-only sidebar."""
    # Crypto Markets Panel
    with st.sidebar.expander("⚙️ Settings", expanded=True):
        render_crypto_controls()

def render_crypto_controls():
    """Render simplified crypto asset controls."""
    # Crypto asset selection
    render_crypto_asset_dropdown()
    
    # Expiry dropdown (only after asset selection)
    if st.session_state.selected_asset != 'Select...':
        render_expiry_dropdown()
    
    # Final controls (only after expiry selection)
    if st.session_state.selected_expiry != 'Select...':
        render_strike_range_selector()
        render_view_selector()
        render_fetch_button()

# Removed all provider, segment, and traditional asset selection functions
# Only crypto asset dropdown remains above

def render_crypto_asset_dropdown():
    """Render hardcoded crypto asset selection."""
    # Hardcoded crypto assets
    crypto_assets = {
        'Select...': 'Select...',
        'Bitcoin (BTC)': 'BTC',
        'Ethereum (ETH)': 'ETH', 
    }
    
    asset_options = list(crypto_assets.keys())
    
    current_index = 0
    if st.session_state.selected_asset in asset_options:
        current_index = asset_options.index(st.session_state.selected_asset)
    
    def _on_asset_change():
        """Callback for asset dropdown change - only runs when dropdown is actually changed."""
        selected_asset_display = st.session_state.crypto_asset_dropdown
        logger.info(f"Crypto asset changed to {selected_asset_display}")
        st.session_state.selected_asset = crypto_assets[selected_asset_display]
        
        # Clear downstream selections
        st.session_state.selected_expiry = 'Select...'
        st.session_state.available_expiries = []
        st.session_state.analytics_report = {}
        # Reset the expiry dropdown itself, so it shows 'Select...' and not the previous asset's date
        if 'expiry_dropdown' in st.session_state:
            del st.session_state['expiry_dropdown']

    selected_asset = st.selectbox(
        "Crypto Asset:",
        options=asset_options,
        index=current_index,
        key="crypto_asset_dropdown",
        on_change=_on_asset_change
    )

def render_expiry_dropdown():
    """Render expiry selection dropdown for crypto assets."""
    # Load expiries for crypto asset only if needed and asset is selected
    current_asset = st.session_state.get('selected_asset', 'Select...')
    if (not st.session_state.available_expiries and 
        current_asset and current_asset != 'Select...'):
        load_crypto_expiries()
    
    if not st.session_state.available_expiries:
        return
    
    expiry_options = ['Select...'] + st.session_state.available_expiries
    
    current_index = 0
    if st.session_state.selected_expiry in expiry_options:
        current_index = expiry_options.index(st.session_state.selected_expiry)
    
    def _on_expiry_change():
        """Callback for expiry dropdown change - only runs when dropdown is actually changed."""
        selected_expiry = st.session_state.expiry_dropdown
        logger.info(f"Expiry changed to {selected_expiry}")
        st.session_state.selected_expiry = selected_expiry
        # Clear data on expiry change
        st.session_state.analytics_report = {}

    selected_expiry = st.selectbox(
        "Expiry:",
        options=expiry_options,
        index=current_index,
        key="expiry_dropdown",
        on_change=_on_expiry_change
    )

def render_strike_range_selector():
    """Render strike range selection."""
    strike_range_options = {
        "±8 Strikes": 8,
        "±10 Strikes": 10,
        "±12 Strikes": 12,
        "±16 Strikes": 16,
        "±32 Strikes": 32,
        "All Strikes": None
    }
    
    # Get current selection
    current_range = st.session_state.get('strike_range', 16)
    current_key = "±16 Strikes"  # Default
    for key, value in strike_range_options.items():
        if value == current_range:
            current_key = key
            break
    
    def _on_strike_range_change():
        """Callback for strike range change - only runs when dropdown is actually changed."""
        selected_range = st.session_state.strike_range_dropdown
        st.session_state.strike_range = strike_range_options[selected_range]

    selected_range = st.selectbox(
        "Strike Range:",
        options=list(strike_range_options.keys()),
        index=list(strike_range_options.keys()).index(current_key),
        key="strike_range_dropdown",
        on_change=_on_strike_range_change
    )

def render_view_selector():
    """Render view selection dropdown."""
    view_options = ['Select...', 'Chain', 'Charts']
    
    current_index = 0
    if st.session_state.get('selected_view_mode', 'Select...') in view_options:
        current_index = view_options.index(st.session_state.get('selected_view_mode', 'Select...'))
    
    def _on_view_change():
        """Callback for view dropdown change - only runs when dropdown is actually changed."""
        selected_view = st.session_state.view_dropdown
        st.session_state.selected_view_mode = selected_view

    selected_view = st.selectbox(
        "View:",
        options=view_options,
        index=current_index,
        key="view_dropdown",
        on_change=_on_view_change
    )

    # Auto-refresh dropdown - only show when Chain view is selected
    if st.session_state.get('selected_view_mode') == 'Chain':
        auto_refresh_options = ['Off', '1s', '5s', '30s', '1m', '5m', '30m']
        
        current_index = 0
        if st.session_state.get('auto_refresh_interval', 'Off') in auto_refresh_options:
            current_index = auto_refresh_options.index(st.session_state.get('auto_refresh_interval', 'Off'))
        
        def _on_auto_refresh_change():
            """Callback for auto-refresh dropdown change - only runs when dropdown is actually changed."""
            selected_refresh = st.session_state.auto_refresh_dropdown
            st.session_state.auto_refresh_interval = selected_refresh
            # Set interval seconds based on selection
            interval_map = {
                'Off': None,
                '1s': 1.5,
                '5s': 5,
                '30s': 30,
                '1m': 60,
                '5m': 300,
                '30m': 1800
            }
            st.session_state.refresh_interval_seconds = interval_map.get(selected_refresh)

        selected_refresh = st.selectbox(
            "Auto Refresh:",
            options=auto_refresh_options,
            index=current_index,
            key="auto_refresh_dropdown",
            on_change=_on_auto_refresh_change
        )



def render_fetch_button():
    """Render crypto data fetch button."""
    button_text = "▶ Run"
    
    if st.button(button_text, type="primary", use_container_width=True):
        fetch_crypto_data()

# Removed complex provider selection logic - not needed for crypto-only app

def load_crypto_expiries():
    """Load expiry dates for selected crypto asset."""
    try:
        asset = st.session_state.selected_asset
        
        if not asset or asset == 'Select...':
            logger.debug("No crypto asset selected for expiry loading")
            return
        
        if not st.session_state.delta_client:
            logger.warning("Delta client not available for expiry loading")
            st.sidebar.warning("⚠️ Delta client not connected")
            return
        
        with st.spinner(f"Loading expiry dates for {asset}..."):
            expiries = st.session_state.delta_client.get_expiry_list(asset)
            
            if expiries and isinstance(expiries, list) and len(expiries) > 0:
                # Filter out invalid dates
                valid_expiries = []
                for expiry in expiries:
                    try:
                        # Validate date format
                        datetime.strptime(expiry, '%Y-%m-%d')
                        valid_expiries.append(expiry)
                    except ValueError:
                        logger.warning(f"Invalid expiry date format: {expiry}")
                
                if valid_expiries:
                    st.session_state.available_expiries = valid_expiries
                    logger.info(f"Loaded {len(valid_expiries)} valid expiry dates for {asset}")
                else:
                    logger.warning(f"No valid expiries found for {asset}")
                    st.sidebar.warning("⚠️ No valid expiry dates found")
            else:
                logger.warning(f"No expiries returned for {asset}")
                st.sidebar.warning("⚠️ No expiry dates available")
                
    except Exception as e:
        logger.error(f"Error loading crypto expiries: {e}")
        st.sidebar.error(f"❌ Failed to load expiry dates")

# Removed complex provider functions - crypto-only app doesn't need them



# ============================================================================
# AUTO-REFRESH LOGIC
# ============================================================================

# ============================================================================
# MAIN UI TABS
# ============================================================================

def render_option_chain_tab():
    """Render Chain tab for crypto options - match legacy pattern exactly."""
    try:
        # Check if data is available
        if not UnifiedDataManager.is_data_available():
            show_no_data_warning(
                "Crypto Options",
                "Please select asset and fetch data from the sidebar."
            )
            return
        
        # Get analytics report (single source of truth)
        analytics_report = UnifiedDataManager.get_analytics_report()
        df = analytics_report['option_chain_data']  # Direct access
        
        
        # Build and display HTML table
        html = build_unified_markets_table(
            df=df,
            analytics_report=analytics_report
        )
        
        if html:
            st.markdown(html, unsafe_allow_html=True)
        else:
            show_no_data_warning(
                "Option Chain",
                "Data is currently being processed. Please wait a moment."
            )
            
    except Exception as e:
        logger.error(f"Error in option chain display: {e}")
        st.error(f"Option chain display error: {str(e)}")

def render_charts_tab():
    """Render Charts tab for crypto options with caching."""
    # Check if data is available (current or cached)
    if not UnifiedDataManager.is_data_available():
        return
    
    # Get analytics report (with caching fallback)
    analytics_report = UnifiedDataManager.get_analytics_report()
    if analytics_report and 'option_chain_data' in analytics_report:
        # Chart rendering using visualization engine
        with st.container():
            st.session_state.visualization_engine.create_comprehensive_dashboard(analytics_report)

# ============================================================================
# AUTO-REFRESH LOGIC
# ============================================================================

def handle_auto_refresh():
    """Handle auto-refresh logic for Chain view only using proper Streamlit pattern."""
    try:
        # Only auto-refresh for Chain view
        view_mode = st.session_state.get('selected_view_mode', 'Select...')
        if view_mode != 'Chain':
            return
        
        # Check if refresh interval is set
        refresh_seconds = st.session_state.get('refresh_interval_seconds')
        if not refresh_seconds:
            return
        
        # Check if data is available and all selections are made
        if not should_auto_refresh():
            return
        
        # Use time-based refresh without continuous loops
        current_time = time.time()
        last_refresh = st.session_state.get('last_refresh_time', 0)
        
        # Initialize timing on first run
        if last_refresh == 0:
            st.session_state.last_refresh_time = current_time
            return
        
        time_since_last = current_time - last_refresh
        remaining_time = max(0, refresh_seconds - time_since_last)
        
        # Show status in sidebar
        if remaining_time > 0:
            st.sidebar.caption(f"🔄 Next refresh in {int(remaining_time)}s")
        
        # Only refresh when time is up and not already in progress
        if time_since_last >= refresh_seconds and not st.session_state.get('refresh_in_progress', False):
            st.session_state.refresh_in_progress = True
            st.sidebar.caption("🔄 Refreshing data...")
            
            # Trigger data fetch  
            success = fetch_crypto_data()
            
            # Reset timing and progress flag BEFORE rerun
            st.session_state.last_refresh_time = current_time
            st.session_state.refresh_in_progress = False
            
            if success:
                # Use st.rerun() only once after successful refresh - matches legacy.py
                st.rerun()
            
    except Exception as e:
        logger.error(f"Error in auto-refresh: {e}")
        st.session_state.refresh_in_progress = False

def should_auto_refresh() -> bool:
    """Check if conditions are met for auto-refresh."""
    return (
        st.session_state.get('selected_expiry', 'Select...') != 'Select...' and
        st.session_state.get('selected_asset', 'Select...') != 'Select...'
    )

def setup_auto_refresh_timer():
    """Keep auto-refresh timer active for Chain view - match legacy.py pattern."""
    view_mode = st.session_state.get('selected_view_mode', 'Select...')
    refresh_seconds = st.session_state.get('refresh_interval_seconds')
    
    # Only setup timer if conditions are met - match legacy.py pattern
    if view_mode == 'Chain' and refresh_seconds and should_auto_refresh():
        time.sleep(1)  # Wait 1 second
        st.rerun()  # Trigger next check

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point for crypto options analytics."""

    # Initialize
    initialize_session_state()
    load_css()
    
    # Render sidebar
    render_sidebar()
    
    
    # Header
    st.title("🔗 CryptoChain - Crypto")
    st.markdown("---")
    
    # Single display area with conditional rendering - RENDER CONTENT FIRST like legacy
    if st.session_state.get('selected_view_mode') == 'Chain':
        try:
            render_option_chain_tab()
        except Exception as e:
            logger.error(f"Error in Chain view: {e}")
    elif st.session_state.get('selected_view_mode') == 'Charts':
        try:
            render_charts_tab()
        except Exception as e:
            logger.error(f"Error in Charts view: {e}")
    elif st.session_state.get('selected_view_mode') == 'Select...':
        # Clean welcome screen
        st.write("Select an asset and view from the sidebar to begin.")
    
    # Auto-refresh logic for Chain view only (after main content) - MATCHES LEGACY ORDER
    handle_auto_refresh()
    
    # Timer to keep auto-refresh active
    setup_auto_refresh_timer()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Critical application error: {e}")
        st.error("🚨 Critical application error. Please refresh the page.")
        st.exception(e)
        