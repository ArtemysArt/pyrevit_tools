# -*- coding: utf-8 -*-
import os
from pyrevit import forms, script

# Revit API imports
from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent

# .NET / WPF imports
import wpf
from System.Windows.Controls import (StackPanel, ComboBox, TextBox, CheckBox,
                                     Orientation, DockPanel, Dock)
from System.Windows import (Thickness, VerticalAlignment, Window)

class RevitApiHandler(IExternalEventHandler):
    def __init__(self, window_instance):
        self.window = window_instance
        self.action = None
        self.data_to_apply = None

    def Execute(self, app):
        try:
            uidoc = app.ActiveUIDocument
            doc = uidoc.Document
        except Exception:
            return

        try:
            if self.action == "get_parameters":
                self._get_parameters(doc, uidoc)
            elif self.action == "set_parameters":
                self._set_parameters(doc, uidoc)
        except Exception as e:
            print("Error in Revit API Handler: {}".format(e))

    def GetName(self):
        return "pyRevit Parameter Editor Revit API Handler"

    def _get_parameters(self, doc, uidoc):
        selection_ids = uidoc.Selection.GetElementIds()
        if not selection_ids:
            self.window.Dispatcher.Invoke(
                lambda: self.window.show_messagebox("No elements selected.", "Information")
            )
            return

        selection = [doc.GetElement(el_id) for el_id in selection_ids]
        param_names = set()
        for el in selection:
            for param in el.Parameters:
                param_names.add(param.Definition.Name)
        
        sorted_params = sorted(list(param_names))

        self.window.Dispatcher.Invoke(
            lambda: self.window.update_all_dropdowns(sorted_params)
        )

    def _set_parameters(self, doc, uidoc):
        from Autodesk.Revit.DB import Transaction

        selection_ids = uidoc.Selection.GetElementIds()
        if not selection_ids or not self.data_to_apply:
            return

        selection = [doc.GetElement(el_id) for el_id in selection_ids]

        t = Transaction(doc, "pyRevit: Apply Parameters")
        try:
            t.Start()
            for element in selection:
                for param_name, new_value in self.data_to_apply:
                    param = element.LookupParameter(param_name)
                    if param and not param.IsReadOnly:
                        try:
                            param.Set(new_value)
                        except Exception as e:
                            print('Failed to set "{}" on Element ID {}. Error: {}'.format(param_name, element.Id, e))
            t.Commit()
        except Exception as e:
            if t.HasStarted():
                t.RollBack()
            print("Transaction failed: {}".format(e))
        


# The WPF Window Class
class ParameterEditorWindow(Window):
    def __init__(self, handler, external_event, initial_rows=5):
        self.handler = handler
        self.external_event = external_event

        xaml_path = os.path.join(os.path.dirname(__file__), 'ui.xaml')
        wpf.LoadComponent(self, xaml_path)

        self.parameter_rows = []
        for _ in range(initial_rows):
            self.add_new_row()

        self.Show()

    def show_messagebox(self, message, title):
        from System.Windows import MessageBox, MessageBoxButton, MessageBoxImage
        MessageBox.Show(self, message, title, MessageBoxButton.OK, MessageBoxImage.Information)

    def add_new_row(self):
        param_combobox = ComboBox(Margin=Thickness(0, 0, 5, 5), VerticalContentAlignment=VerticalAlignment.Center, MinWidth=180)
        new_value_textbox = TextBox(Margin=Thickness(0, 0, 5, 5), VerticalContentAlignment=VerticalAlignment.Center, MinWidth=120)
        lock_checkbox = CheckBox(ToolTip="Lock this row to prevent clearing the value.", VerticalAlignment=VerticalAlignment.Center)
        
        row_panel = DockPanel(Margin=Thickness(0, 0, 0, 5))
        DockPanel.SetDock(lock_checkbox, Dock.Right)
        
        row_panel.Children.Add(lock_checkbox)
        row_panel.Children.Add(param_combobox)
        row_panel.Children.Add(new_value_textbox)
        
        self.parameter_rows.append({'combo': param_combobox, 'text': new_value_textbox, 'lock': lock_checkbox})
        self.parameter_rows_panel.Children.Add(row_panel)

    def update_all_dropdowns(self, param_names):
        for row in self.parameter_rows:
            selected_item = row['combo'].SelectedItem
            row['combo'].ItemsSource = param_names
            if selected_item in param_names:
                row['combo'].SelectedItem = selected_item

    def refresh_all_dropdowns_click(self, sender, args):
        self.handler.action = "get_parameters"
        self.external_event.Raise()

    def apply_parameters_click(self, sender, args):
        data_to_apply = []
        for row in self.parameter_rows:
            param_name = row['combo'].SelectedItem
            new_value = row['text'].Text
            if param_name and new_value:
                data_to_apply.append((param_name, new_value))
        
        if not data_to_apply:
            self.show_messagebox("Nothing to apply. Select parameters and enter values.", "Warning")
            return

        self.handler.data_to_apply = data_to_apply
        self.handler.action = "set_parameters"
        self.external_event.Raise()

    def clear_textboxes_click(self, sender, args):
        for row in self.parameter_rows:
            if not row['lock'].IsChecked:
                row['text'].Clear()


if __name__ == "__main__":
    revit_handler = RevitApiHandler(None)
    ext_event = ExternalEvent.Create(revit_handler)
    ui_window = ParameterEditorWindow(revit_handler, ext_event)
    revit_handler.window = ui_window