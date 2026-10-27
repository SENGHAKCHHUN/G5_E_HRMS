"""Reusable CustomTkinter components implementing the Slate Desktop System.

The views use them through one name: `from ui import widgets as W`, then `W.label(...)`,
`W.Modal(...)` ... Each topic lives in its own file:

    basics.py    text, cards, buttons, badges, tags, avatars, icon tiles
    inputs.py    text entry, search box, option menu, segmented button, progress bar, switch
    layout.py    page header, KPI cards, section titles, clickable rows, grid columns
    table.py     data table, its cell helpers, paginator
    charts.py    donut chart (matplotlib)
    dialogs.py   modal dialog, two-column form, confirm, info dialog, toast
"""
from logic import formatting

from ..icons import icon  # noqa: F401 - views use W.icon
from .basics import (avatar, badge, button, card, divider, icon_button, icon_tile, label,  # noqa: F401
                     micro, tag, transparent)
from .charts import donut_chart  # noqa: F401
from .dialogs import Form, Modal, _set_window_icon, confirm, info_dialog, toast  # noqa: F401
from .inputs import SearchEntry, entry, option_menu, progress, segmented, switch  # noqa: F401
from .layout import KpiCard, PageHeader, grid_columns, make_clickable, section_title  # noqa: F401
from .table import DataTable, Paginator, cell_stack, dot_text, person_cell  # noqa: F401

money = formatting.money  # shared money formatter, available to the views as W.money
