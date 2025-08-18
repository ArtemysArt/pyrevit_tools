# -*- coding: utf-8 -*-
#pylint: disable=E0401,W0703,C0103
"""
BUTTON 2: APPLY REMEMBERED TYPES
This script retrieves the stored Conduit and Fitting type IDs,
and applies them to the user's current selection.
"""

from Autodesk.Revit.DB import ElementId, Transaction
from pyrevit import forms
from pyrevit import script
from pyrevit import revit

# --- Unique Keys for Retrieving Data ---
CONDUIT_ID_KEY = 'MyConduitChanger_ConduitTypeID'
FITTING_ID_KEY = 'MyConduitChanger_FittingTypeID'

doc = revit.doc

# --- Step 1: Load the stored ElementIDs ---
conduit_type_id_int = script.load_data(CONDUIT_ID_KEY)
fitting_type_id_int = script.load_data(FITTING_ID_KEY)

# --- Step 2: Check if the types have been set ---
if not conduit_type_id_int or not fitting_type_id_int:
    forms.alert(
        "Target types have not been set yet.\n\n"
        "Please run the 'Set Conduit Types' script first.",
        title="Error: Types Not Set",
        exitscript=True
    )

# Convert the stored integers back into ElementId objects
target_conduit_type_id = ElementId(conduit_type_id_int)
target_fitting_type_id = ElementId(fitting_type_id_int)

# --- Step 3: Get selection and apply the types ---
selection = revit.get_selection()

if selection.is_empty:
    forms.alert("No elements are selected. Please select conduits and fittings to change.", exitscript=True)

with revit.Transaction('Apply Stored Conduit and Fitting Types'):
    for element in selection:
        if not hasattr(element, 'Category') or not element.Category:
            continue
        
        # Check if it's a Conduit
        if element.Category.Id == doc.Settings.Categories.get_Item("Conduits").Id:
            if element.GetTypeId() != target_conduit_type_id:
                element.ChangeTypeId(target_conduit_type_id)
        
        # Check if it's a Conduit Fitting
        elif element.Category.Id == doc.Settings.Categories.get_Item("Conduit Fittings").Id:
            if element.GetTypeId() != target_fitting_type_id:
                element.ChangeTypeId(target_fitting_type_id)
