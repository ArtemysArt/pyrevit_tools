# -*- coding: utf-8 -*-
"""
Changes the radius of pre-selected bend fittings to 50 inches.
"""

__title__ = "Bend 50\""
__author__ = "Your Name"

from Autodesk.Revit.DB import Transaction, BuiltInParameter
from pyrevit import revit, forms

doc = revit.doc

def find_and_set_radius(element, radius_value):
    radius_param = None

    param_builtin = element.get_Parameter(BuiltInParameter.RBS_CONDUIT_BENDRADIUS)
    if param_builtin and not param_builtin.IsReadOnly:
        radius_param = param_builtin
    else:
        for param_name in ["Radius", "Nominal Radius", "Bend Radius"]:
            p = element.LookupParameter(param_name)
            if p and not p.IsReadOnly:
                radius_param = p
                break

    if radius_param:
        try:
            radius_param.Set(radius_value)
            return True
        except Exception:
            pass

    try:
        elem_type = doc.GetElement(element.GetTypeId())
        if elem_type:
            type_param = None
            type_param_builtin = elem_type.get_Parameter(BuiltInParameter.RBS_CONDUIT_BENDRADIUS)
            if type_param_builtin and not type_param_builtin.IsReadOnly:
                type_param = type_param_builtin
            else:
                for param_name in ["Radius", "Nominal Radius", "Bend Radius"]:
                    p = elem_type.LookupParameter(param_name)
                    if p and not p.IsReadOnly:
                        type_param = p
                        break
            
            if type_param:
                type_param.Set(radius_value)
                return True
    except Exception:
        return False
        
    return False

def change_bend_radius_silently():

    selection = revit.get_selection()

    if not selection:
        forms.alert("Please select one or more bend fittings first.", exitscript=True)

    new_radius_feet = 50.0 / 12.0
    changed_count = 0

    t = Transaction(doc, 'Change Bend Radius to 50" (Silent)')
    t.Start()

    try:
        for el in selection:
            if find_and_set_radius(el, new_radius_feet):
                changed_count += 1

        if changed_count > 0:
            doc.Regenerate()

        t.Commit()

    except Exception as e:
        if t.HasStarted():
            t.RollBack()
        forms.alert("An error occurred: {}\nNo changes were made.".format(e), exitscript=True)

if __name__ == "__main__":
    change_bend_radius_silently()