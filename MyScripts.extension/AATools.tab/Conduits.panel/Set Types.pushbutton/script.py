# -*- coding: utf-8 -*-
#pylint: disable=E0401,W0703,C0103
"""
SET AND REMEMBER TYPES
This script asks the user to select a target conduit type and a target
conduit fitting type, and then stores their ElementIDs for later use
by the 'Apply Types' script.
"""

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    BuiltInCategory,
    BuiltInParameter,
)
from pyrevit import forms
from pyrevit import script
from pyrevit import revit

# --- Unique Keys for Storing Data ---
CONDUIT_ID_KEY = 'MyConduitChanger_ConduitTypeID'
FITTING_ID_KEY = 'MyConduitChanger_FittingTypeID'

doc = revit.doc

# --- Create Dictionaries for Selection Lookup ---
conduit_type_dict = {}
for t in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Conduit).WhereElementIsElementType():
    param = t.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
    if param and param.HasValue:
        type_name = param.AsString()
        if type_name:
            conduit_type_dict[type_name] = t

fitting_type_dict = {}
for t in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ConduitFitting).WhereElementIsElementType():
    fam_name_param = t.get_Parameter(BuiltInParameter.ALL_MODEL_FAMILY_NAME)
    type_name_param = t.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
    if fam_name_param and fam_name_param.HasValue and type_name_param and type_name_param.HasValue:
        fam_name = fam_name_param.AsString()
        type_name = type_name_param.AsString()
        if fam_name and type_name:
            display_name = "{}: {}".format(fam_name, type_name)
            fitting_type_dict[display_name] = t

# --- Step 1: Select Conduit Type ---
if not conduit_type_dict:
    forms.alert("Error: Could not find any valid Conduit types.", exitscript=True)

conduit_names = sorted(conduit_type_dict.keys())
selected_conduit_name = forms.SelectFromList.show(
    conduit_names,
    title='Step 1 of 2: Select Target Conduit Type',
    button_name='Next: Select Fitting'
)

if not selected_conduit_name:
    script.exit()
target_conduit_type = conduit_type_dict[selected_conduit_name]

# --- Step 2: Select Conduit Fitting Type ---
if not fitting_type_dict:
    forms.alert("Error: Could not find any valid Conduit Fitting types.", exitscript=True)

fitting_names = sorted(fitting_type_dict.keys())
selected_fitting_name = forms.SelectFromList.show(
    fitting_names,
    title='Step 2 of 2: Select Target Conduit Fitting Type',
    button_name='Set and Save Types'
)

if not selected_fitting_name:
    script.exit()
target_fitting_type = fitting_type_dict[selected_fitting_name]


# --- Step 3: Store the ElementIDs of the chosen types ---
script.store_data(CONDUIT_ID_KEY, target_conduit_type.Id.IntegerValue)
script.store_data(FITTING_ID_KEY, target_fitting_type.Id.IntegerValue)
