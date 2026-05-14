"""Tab renderers for the Streamlit UI."""

from .backtesting import render_backtesting_tab
from .comparison import render_comparison_tab
from .detail import render_detail_tab

__all__ = ["render_backtesting_tab", "render_comparison_tab", "render_detail_tab"]
