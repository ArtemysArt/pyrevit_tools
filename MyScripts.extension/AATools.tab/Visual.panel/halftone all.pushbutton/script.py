# -*- coding: utf-8 -*-
"""
Isolates selected elements using a saved transparency setting.
"""

__title__ = 'Isolate'
__author__ = 'AA'

import os
from pyrevit import revit, DB, forms

# --- Manually find the extension's root directory ---
script_path = os.path.dirname(__file__)
current_path = script_path
while not current_path.lower().endswith('.extension'):
    parent_path = os.path.dirname(current_path)
    if parent_path == current_path:
        raise Exception("Could not find the .extension directory.")
    current_path = parent_path
ext_path = current_path

# Define the full path for our settings file
settings_file_path = os.path.join(ext_path, 'isolate_tool_settings.txt')

# --- Read the saved transparency value ---
transparency_value = 85  # Default value
try:
    if os.path.exists(settings_file_path):
        with open(settings_file_path, 'r') as f:
            file_content = f.read().strip()
            if file_content.isdigit():
                transparency_value = int(file_content)
except Exception as e:
    print('Could not read settings file, using default (85).\nError: {}'.format(e))

# --- Main Script Logic ---
doc = revit.doc
view = revit.active_view
selection_ids = revit.get_selection().element_ids

with revit.Transaction('Isolate with Halftone/Transparency'):
    if selection_ids:
        all_elements_in_view = DB.FilteredElementCollector(doc, view.Id).ToElements()
        override_settings = DB.OverrideGraphicSettings()
        override_settings.SetHalftone(True)
        override_settings.SetSurfaceTransparency(transparency_value)

        selected_ids = set(selection_ids)
        for el in all_elements_in_view:
            if el.Id not in selected_ids:
                try:
                    view.SetElementOverrides(el.Id, override_settings)
                except Exception:
                    pass
    else:
        # Clear logic
        all_elements_in_view = DB.FilteredElementCollector(doc, view.Id).ToElements()
        clear_settings = DB.OverrideGraphicSettings()
        cleared_count = 0
        for el in all_elements_in_view:
            current_overrides = view.GetElementOverrides(el.Id)
            if current_overrides.Halftone or current_overrides.Transparency > 0:
                try:
                    view.SetElementOverrides(el.Id, clear_settings)
                    cleared_count += 1
                except Exception:
                    pass
