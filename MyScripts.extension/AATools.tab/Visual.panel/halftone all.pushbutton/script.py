# -*- coding: utf-8 -*-
"""
Halftones and makes transparent all elements not in the current selection.
If nothing is selected, removes all halftone and transparency overrides
from the active view.
"""

__title__ = 'Isolate'
__author__ = 'AA'

from pyrevit import revit, DB

# Get the current Revit document and the active view
doc = revit.doc
view = revit.active_view

# Get the current selection
selection_ids = revit.get_selection().element_ids

with revit.Transaction('Isolate with Halftone/Transparency'):
    if selection_ids:

        all_elements_in_view = DB.FilteredElementCollector(doc, view.Id).ToElements()

        override_settings = DB.OverrideGraphicSettings()
        override_settings.SetHalftone(True)
        override_settings.SetSurfaceTransparency(85) # Set transparency

        selected_ids = set(selection_ids)

        for el in all_elements_in_view:
            if el.Id not in selected_ids:
                try:
                    view.SetElementOverrides(el.Id, override_settings)
                except Exception:
                    pass

    else:
        all_elements_in_view = DB.FilteredElementCollector(doc, view.Id).ToElements()
        clear_settings = DB.OverrideGraphicSettings()

        for el in all_elements_in_view:
            current_overrides = view.GetElementOverrides(el.Id)

            if current_overrides.Halftone or current_overrides.Transparency > 0:
                try:
                    view.SetElementOverrides(el.Id, clear_settings)
                except Exception:
                    pass