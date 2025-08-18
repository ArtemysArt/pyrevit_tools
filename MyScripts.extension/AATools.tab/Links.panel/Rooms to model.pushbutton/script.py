# -*- coding: utf-8 -*-
"""
pyRevit script to generate 'Room Separator' lines based on the boundaries of existing rooms AND existing separators visible in the view.
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

# --- Helper Functions ---

def get_visible_rooms(view):
    """Returns a list of all placed Room elements visible in the given view."""
    collector = FilteredElementCollector(doc, view.Id)
    elements = collector.OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
    return [room for room in elements if isinstance(room, Room) and room.Area > 0 and room.Location]

def get_visible_separators(view):
    """Returns a list of all Room Separation Line elements in the given view."""
    collector = FilteredElementCollector(doc, view.Id)
    return collector.OfCategory(BuiltInCategory.OST_RoomSeparationLines).WhereElementIsNotElementType().ToElements()

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

def create_line_fingerprint(line, precision=4):
    """Creates a unique, order-independent string for a line's 2D geometry."""
    p1 = line.GetEndPoint(0)
    p2 = line.GetEndPoint(1)
    pt1_tuple = (round(p1.X, precision), round(p1.Y, precision))
    pt2_tuple = (round(p2.X, precision), round(p2.Y, precision))
    sorted_points = sorted([pt1_tuple, pt2_tuple])
    return "{};{}".format(sorted_points[0], sorted_points[1])

def merge_collinear_lines(curve_list):
    """Takes a list of contiguous curves and merges any adjacent, collinear lines."""
    if not curve_list: return []
    merged_curves = []
    while curve_list:
        current_curve = curve_list.pop(0)
        if not isinstance(current_curve, Line):
            merged_curves.append(current_curve)
            continue
        while True:
            if not curve_list: break 
            next_curve = curve_list[0] 
            can_merge = False
            if isinstance(next_curve, Line) and \
               current_curve.Direction.IsAlmostEqualTo(next_curve.Direction) and \
               current_curve.GetEndPoint(1).IsAlmostEqualTo(next_curve.GetEndPoint(0)):
                can_merge = True
            if can_merge:
                new_start = current_curve.GetEndPoint(0)
                new_end = next_curve.GetEndPoint(1)
                current_curve = Line.CreateBound(new_start, new_end)
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
    visible_separators = get_visible_separators(active_view)

    if not visible_rooms and not visible_separators:
        forms.alert("No visible rooms or room separators found.", title="Nothing to Copy")
        return

    offset_y = get_offset_from_user()
    if offset_y is None: return

    # 2. Main Logic
    newly_created_element_ids = []
    created_line_fingerprints = set()

    with Transaction(doc, "Copy Rooms and Separators with Offset") as t:
        t.Start()

        level = doc.GetElement(active_view.GenLevel.Id)
        if not level:
            t.RollBack()
            forms.alert("Could not determine the level from the active view.", "Error")
            return

        sketch_plane = SketchPlane.Create(doc, level.Id)
        translation = XYZ(0, offset_y, 0)
        transform = Transform.CreateTranslation(translation)

        # --- Part A: Process Room Boundaries ---
        for room in visible_rooms:
            if not isinstance(room.Location, LocationPoint): continue

            # Create and place the new room
            original_loc = room.Location.Point
            new_loc = transform.OfPoint(original_loc)
            new_room = doc.Create.NewRoom(level, UV(new_loc.X, new_loc.Y))
            if new_room:
                newly_created_element_ids.append(new_room.Id)
                # Copy parameters
                for param in room.Parameters:
                    if not param.IsReadOnly and param.HasValue:
                        new_param = new_room.get_Parameter(param.Definition)
                        if new_param and not new_param.IsReadOnly:
                            try:
                                if param.StorageType == StorageType.String: new_param.Set(param.AsString())
                                elif param.StorageType == StorageType.Double: new_param.Set(param.AsDouble())
                                elif param.StorageType == StorageType.Integer: new_param.Set(param.AsInteger())
                                elif param.StorageType == StorageType.ElementId: new_param.Set(param.AsElementId())
                            except: pass
            
            # Create boundaries for the placed room
            boundary_segments = room.GetBoundarySegments(SpatialElementBoundaryOptions())
            if not boundary_segments: continue
            for segment_list in boundary_segments:
                loop_curves = [seg.GetCurve().CreateTransformed(transform) for seg in segment_list]
                merged_loop_curves = merge_collinear_lines(loop_curves)
                
                for curve in merged_loop_curves:
                    # Create a temporary CurveArray for the creation method
                    temp_curve_array = CurveArray()
                    temp_curve_array.Append(curve)
                    
                    if isinstance(curve, Line):
                        fingerprint = create_line_fingerprint(curve)
                        if fingerprint not in created_line_fingerprints:
                            new_sep = doc.Create.NewRoomBoundaryLines(sketch_plane, temp_curve_array, active_view)
                            newly_created_element_ids.extend([el.Id for el in new_sep])
                            created_line_fingerprints.add(fingerprint)
                    else: # For arcs, etc., create without fingerprinting
                        new_sep = doc.Create.NewRoomBoundaryLines(sketch_plane, temp_curve_array, active_view)
                        newly_created_element_ids.extend([el.Id for el in new_sep])

        # --- Part B: Process Standalone Room Separators ---
        for separator in visible_separators:
            original_curve = separator.Location.Curve
            if isinstance(original_curve, Line):
                new_curve = original_curve.CreateTransformed(transform)
                fingerprint = create_line_fingerprint(new_curve)
                if fingerprint not in created_line_fingerprints:
                    # Create a temporary CurveArray for the creation method
                    temp_curve_array = CurveArray()
                    temp_curve_array.Append(new_curve)
                    new_sep = doc.Create.NewRoomBoundaryLines(sketch_plane, temp_curve_array, active_view)
                    newly_created_element_ids.extend([el.Id for el in new_sep])
                    created_line_fingerprints.add(fingerprint)
        t.Commit()

    # 3. Post-processing and User Feedback
    if newly_created_element_ids:
        uidoc.Selection.SetElementIds(DotNetList[ElementId](newly_created_element_ids))
        total_rooms = len([eid for eid in newly_created_element_ids if doc.GetElement(eid).Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms)])
        total_separators = len(newly_created_element_ids) - total_rooms
        message = "Successfully created {} new rooms and {} new separator lines.".format(total_rooms, total_separators)
        forms.alert(message, title="Script Completed")

# --- Script Execution ---
if __name__ == '__main__':
    main()