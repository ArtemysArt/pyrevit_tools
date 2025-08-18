# -*- coding: utf-8 -*-
"""
pyRevit script to generate 'Room Separator' lines based on the boundaries of existing rooms visible in the current Revit view.
And then place in it copy of the room (with all corresponding to it parameters).
"""

__title__ = "Copy Rooms"
__author__ = "AA"

# --- .NET Imports ---
from System.Collections.Generic import List as DotNetList

# --- Revit API Imports ---
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    BuiltInCategory,
    Transaction,
    SpatialElementBoundaryOptions,
    CurveArray,
    Curve,
    SketchPlane,
    XYZ,
    Transform,
    ElementId,
    UV,
    StorageType,
    LocationPoint,
    Line
)
from Autodesk.Revit.DB.Architecture import Room

# --- pyRevit Imports ---
from pyrevit import forms
from pyrevit import revit

# --- Globals ---
doc = revit.doc
uidoc = revit.uidoc
active_view = doc.ActiveView

# --- Core Functions ---

def get_visible_rooms(view):
    """Returns a list of all Room elements visible in the given view."""
    collector = FilteredElementCollector(doc, view.Id)
    visible_rooms = collector.OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
    return [room for room in visible_rooms if isinstance(room, Room) and room.Area > 0 and room.Location is not None]

def get_offset_from_user():
    """Prompts the user for a Y-axis offset and returns it as a float."""
    offset_str = forms.ask_for_string(
        default="10.0",
        prompt="Enter the offset value for the Y-axis (in project units):",
        title="Y-Axis Offset"
    )
    if offset_str is None: return None
    try:
        return float(offset_str)
    except ValueError:
        forms.alert("Invalid input. Please enter a numerical value.", title="Input Error")
        return None

def merge_collinear_lines(curve_list):
    """Takes a list of contiguous curves and merges any adjacent, collinear lines."""
    if not curve_list:
        return []

    merged_curves = []
    while curve_list:
        current_curve = curve_list.pop(0)

        if not isinstance(current_curve, Line):
            merged_curves.append(current_curve)
            continue

        while True:
            if not curve_list:
                break 

            next_curve = curve_list[0] 
            can_merge = False
            if isinstance(next_curve, Line):
                if current_curve.Direction.IsAlmostEqualTo(next_curve.Direction) and \
                   current_curve.GetEndPoint(1).IsAlmostEqualTo(next_curve.GetEndPoint(0)):
                    can_merge = True

            if can_merge:
                new_start_point = current_curve.GetEndPoint(0)
                new_end_point = next_curve.GetEndPoint(1)
                current_curve = Line.CreateBound(new_start_point, new_end_point)
                curve_list.pop(0)
            else:
                break
        
        merged_curves.append(current_curve)
    
    return merged_curves

def main():
    """Main execution function of the script."""
    # 1. Pre-checks
    if not (active_view.ViewType.ToString() in ['FloorPlan', 'CeilingPlan']):
        forms.alert("Please run this script in a Floor Plan or Ceiling Plan view.", title="Wrong View Type")
        return
        
    visible_rooms = get_visible_rooms(active_view)
    if not visible_rooms:
        forms.alert("No visible rooms with valid locations found.", title="No Rooms Found")
        return

    offset_y = get_offset_from_user()
    if offset_y is None: return

    # 2. Main Logic
    newly_created_element_ids = []
    with Transaction(doc, "Create Offset Rooms and Separators") as t:
        t.Start()

        level = doc.GetElement(active_view.GenLevel.Id)
        if not level:
            t.RollBack()
            forms.alert("Could not determine the level from the active view.", "Error")
            return

        sketch_plane = SketchPlane.Create(doc, level.Id)

        for room in visible_rooms:
            if not isinstance(room.Location, LocationPoint):
                continue

            boundary_segments = room.GetBoundarySegments(SpatialElementBoundaryOptions())
            if not boundary_segments: continue

            translation = XYZ(0, offset_y, 0)
            transform = Transform.CreateTranslation(translation)
            
            final_curves_for_room = CurveArray()

            for segment_list in boundary_segments:
                loop_curves = [seg.GetCurve().CreateTransformed(transform) for seg in segment_list]
                merged_loop_curves = merge_collinear_lines(loop_curves)
                for curve in merged_loop_curves:
                    final_curves_for_room.Append(curve)

            if not final_curves_for_room.IsEmpty:
                separators = doc.Create.NewRoomBoundaryLines(sketch_plane, final_curves_for_room, active_view)
                for sep in separators:
                    newly_created_element_ids.append(sep.Id)
            
            original_loc_point = room.Location.Point
            new_loc_point = transform.OfPoint(original_loc_point)
            uv_point = UV(new_loc_point.X, new_loc_point.Y)
            
            new_room = doc.Create.NewRoom(level, uv_point)

            if new_room:
                newly_created_element_ids.append(new_room.Id)
                for param in room.Parameters:
                    if not param.IsReadOnly and param.HasValue:
                        new_param = new_room.get_Parameter(param.Definition)
                        if new_param and not new_param.IsReadOnly:
                            try:
                                if param.StorageType == StorageType.String:
                                    new_param.Set(param.AsString())
                                elif param.StorageType == StorageType.Double:
                                    new_param.Set(param.AsDouble())
                                elif param.StorageType == StorageType.Integer:
                                    new_param.Set(param.AsInteger())
                                elif param.StorageType == StorageType.ElementId:
                                    new_param.Set(param.AsElementId())
                            except Exception as e:
                                print("Could not set param '{}'. Error: {}".format(param.Definition.Name, e))
        
        t.Commit()

    # 3. Post-processing and User Feedback
    if newly_created_element_ids:
        # Convert Python list to a .NET collection for the API method
        selection_collection = DotNetList[ElementId](newly_created_element_ids)
        uidoc.Selection.SetElementIds(selection_collection)
        
        # --- Refactored this section for clarity ---
        # Get the IDs of the newly created separator lines
        separator_ids = [
            eid for eid in newly_created_element_ids 
            if doc.GetElement(eid).Category.Id.IntegerValue != int(BuiltInCategory.OST_Rooms)
        ]
        
        # Get the IDs of the newly created rooms
        room_ids = [
            eid for eid in newly_created_element_ids 
            if doc.GetElement(eid).Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms)
        ]

        total_separators = len(separator_ids)
        total_rooms = len(room_ids)
        
        # Create the message string first
        message = "Successfully created {} Room Separator lines and {} new rooms.".format(
            total_separators, 
            total_rooms
        )
        
        # Call the alert with the clean message
        forms.alert(message, title="Script Completed")

# --- Script Execution ---
if __name__ == '__main__':
    main()