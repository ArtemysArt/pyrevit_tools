# -*- coding: utf-8 -*-
"""
Sets and saves the default transparency value for the 'Isolate' tool.
"""

__title__ = 'Isolate Settings'
__author__ = 'AA'

import os
from pyrevit import forms

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

# --- Read the current setting from the file ---
current_transparency = '85'
try:
    if os.path.exists(settings_file_path):
        with open(settings_file_path, 'r') as f:
            file_content = f.read().strip()
            if file_content.isdigit():
                current_transparency = file_content
except Exception as e:
    print('Error reading settings file: {}'.format(e))

# --- Ask the user for a new value ---
input_string = forms.ask_for_string(
    default=current_transparency,
    prompt='Enter default transparency for the Isolate tool (0-100):',
    title='Isolate Tool Settings'
)

# --- Save the new value ---
if input_string and input_string.isdigit():
    new_value = int(input_string)
    new_value = max(0, min(100, new_value))

    try:
        with open(settings_file_path, 'w') as f:
            f.write(str(new_value))
    except Exception as e:
        forms.alert('Could not save settings.\nError: {}'.format(e), title='Error')
elif input_string:
    forms.alert('Invalid input. Please enter a whole number.', title='Input Error')