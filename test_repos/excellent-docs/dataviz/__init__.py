"""
DataViz Toolkit
==============

A comprehensive data visualization library.

Basic usage:
    >>> import dataviz as dv
    >>> chart = dv.BarChart(data)
    >>> chart.show()
"""

__version__ = "2.1.0"
__author__ = "DataViz Team"

# Note: These would be imported if the modules existed
# from .charts import BarChart, LineChart, PieChart
# from .themes import set_theme

# Define what's available when importing with *
__all__ = ["__version__", "__author__"]
