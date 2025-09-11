#
# Copyright 2016 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

from .qt import QtGui, QtWidgets, QtCore
from pxr import Sdf
from .usdviewContextMenuItem import UsdviewContextMenuItem
from .common import (PropertyViewIndex, PropertyViewDataRoles,
                     PrimNotFoundException, PropertyNotFoundException)

#
# Specialized context menu for running commands in the agent message viewer.
#
class AgentMessageContextMenu(QtWidgets.QMenu):

    def __init__(self, parent, item, dataModel):
        QtWidgets.QMenu.__init__(self, parent)
        self._menuItems = _GetContextMenuItems(item, dataModel)

        for menuItem in self._menuItems:
            # create menu actions
            if menuItem.isValid() and menuItem.ShouldDisplay():
                action = self.addAction(menuItem.GetText(), menuItem.RunCommand)

                # set enabled
                if not menuItem.IsEnabled():
                    action.setEnabled(False)


def _GetContextMenuItems(item, dataModel):
    menuItems = []

    # if we don't have an item, we can't produce a context menu.
    if not item:
        return menuItems

    try:
        # If the item represents an object, we'll get these items.
        obj = item.data(PropertyViewDataRoles.OBJECT)
        path = obj.GetPath()
        prim = dataModel.stage.GetPrimAtPath(path)

        # Get the target paths depending on the kind of object we have.
        if hasattr(obj, 'GetTargets'):
            targetPaths = obj.GetTargets()
        else:
            targetPaths = []

        menuItems.append(
            UsdviewContextMenuItem(
                'Copy Property Path', _CopyPropertyPathToClipboard,
                (obj,)))

        # We can only select prims
        if prim.IsValid():
            menuItems.append(
                UsdviewContextMenuItem(
                    'Select Prim', _SelectPrim,
                    (dataModel, prim.GetPath())))

        for target in targetPaths:
            targetPrim = dataModel.stage.GetPrimAtPath(target)
            if targetPrim.IsValid():
                menuItems.append(
                    UsdviewContextMenuItem(
                        'Select Target: %s' % str(target),
                        _SelectPrim,
                        (dataModel, target)))

    except:
        # If the above didn't work, try to get the computed property path.
        try:
            path, propName = item.data(PropertyViewDataRoles.COMPUTED_PROPERTY_PATH)
            menuItems.append(
                UsdviewContextMenuItem(
                    'Copy Computed Property Path', _CopyComputedPropertyPathToClipboard,
                    (path, propName)))

            prim = dataModel.stage.GetPrimAtPath(path)
            if prim.IsValid():
                menuItems.append(
                    UsdviewContextMenuItem(
                        'Select Prim', _SelectPrim,
                        (dataModel, path)))
        except:
            # We can't determine an object or computed property associated
            # with this item. Give up.
            pass

    return menuItems


def _CopyPropertyPathToClipboard(obj):
    import sys

    cb = QtWidgets.QApplication.clipboard()
    cb.setText(str(obj.GetPath()), QtGui.QClipboard.Selection)
    cb.setText(str(obj.GetPath()), QtGui.QClipboard.Clipboard)


def _CopyComputedPropertyPathToClipboard(path, propName):
    import sys

    cb = QtWidgets.QApplication.clipboard()
    pathStr = path.AppendProperty(propName).pathString
    cb.setText(pathStr, QtGui.QClipboard.Selection)
    cb.setText(pathStr, QtGui.QClipboard.Clipboard)


def _SelectPrim(dataModel, primPath):
    try:
        prim = dataModel.stage.GetPrimAtPath(primPath)
        if prim:
            dataModel.selection.setPrimPath(primPath, "context menu")
        else:
            raise PrimNotFoundException(primPath)
    except Exception as e:
        # If prim selection fails, report the error and give up.
        err = ("ERROR: Could not select prim <%s>\n%s" % (primPath, e))
        print(err)


def _GetPropertySpecInSessionLayer(prop):
    stage = prop.GetStage()
    return stage.GetSessionLayer().GetPropertyAtPath(prop.GetPath())


class _CreateOpinionDialog(QtWidgets.QDialog):
    def __init__(self, parent, prop):
        QtWidgets.QDialog.__init__(self, parent)
        self._prop = prop

        # set title
        self.setWindowTitle('Set %s' % prop.GetName())

        # create layout
        layout = QtWidgets.QVBoxLayout()

        # add user message.
        self._label = QtWidgets.QLabel(self)
        self._label.setText('Setting %s on prim %s:' %
                           (prop.GetName(), prop.GetPrim().GetPath()))
        layout.addWidget(self._label)

        # find typed value
        self._widget = None
        from .scalarTypes import GetScalarTypeFromTypeName
        scalarType = GetScalarTypeFromTypeName(prop.GetTypeName())
        if scalarType is not None:
            self._widget = scalarType.GetEditWidget(prop.Get(), self)
        else:
            # we don't have a widget for this type.  Display a text field
            # instead.
            self._widget = QtWidgets.QLineEdit(self)
            self._widget.setText(str(prop.Get()))

        layout.addWidget(self._widget)

        # add buttons
        buttonLayout = QtWidgets.QHBoxLayout()
        self._okButton = QtWidgets.QPushButton('Ok')
        self._cancelButton = QtWidgets.QPushButton('Cancel')
        buttonLayout.addWidget(self._okButton)
        buttonLayout.addWidget(self._cancelButton)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

        # connect buttons to handlers
        self._okButton.clicked.connect(self.accept)
        self._cancelButton.clicked.connect(self.reject)

    def GetValue(self):
        from .scalarTypes import GetScalarTypeFromTypeName
        scalarType = GetScalarTypeFromTypeName(self._prop.GetTypeName())

        if scalarType is not None:
            return scalarType.GetValueFromWidget(self._widget)
        else:
            return str(self._widget.text())


def _CreateOpinion(prop, layer=None):
    from .scalarTypes import GetScalarTypeFromTypeName

    if layer is None:
        stage = prop.GetStage()
        layer = stage.GetSessionLayer()

    dialog = _CreateOpinionDialog(None, prop)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:

        # add opinion
        with Sdf.ChangeBlock():
            primSpec = Sdf.CreatePrimInLayer(layer, prop.GetPrim().GetPath())
            propSpec = Sdf.PropertySpec(primSpec, prop.GetName(),
                                       prop.GetPropertyType())
            propSpec.default = dialog.GetValue()


def _RemoveOpinion(prop, layer=None):
    if layer is None:
        stage = prop.GetStage()
        layer = stage.GetSessionLayer()

    Sdf.RemovePropertyKeyPath(layer, prop.GetPath())


class _JumpToEnclosingObject(UsdviewContextMenuItem):

    def __init__(self, obj, dataModel):
        if hasattr(obj, 'GetPrim'):
            prim = obj.GetPrim()
        else:
            prim = obj

        path = prim.GetPath()

        from .common import GetEnclosingModelPrim
        modelPrim = GetEnclosingModelPrim(prim)

        if modelPrim:
            self._modelPath = modelPrim.GetPath()
            displayName = 'Jump to Enclosing Model'
        else:
            displayName = 'Jump to Stage Root'
            self._modelPath = Sdf.Path.absoluteRootPath

        super(_JumpToEnclosingObject, self).__init__(
            displayName, self._JumpToEnclosingModel, (dataModel,))

    def _JumpToEnclosingModel(self, dataModel):
        dataModel.selection.setPrimPath(self._modelPath, "context menu")

    def IsEnabled(self):
        return True

    def ShouldDisplay(self):
        return True


class _HasSessionOpinion(UsdviewContextMenuItem):
    def __init__(self, prop):
        self._prop = prop
        super(_HasSessionOpinion, self).__init__('Remove Session Override',
                                                 self._RemoveSessionOpinion,
                                                 ())

    def _RemoveSessionOpinion(self):
        _RemoveOpinion(self._prop)

    def IsEnabled(self):
        return True

    def ShouldDisplay(self):
        stage = self._prop.GetStage()
        propSpec = _GetPropertySpecInSessionLayer(self._prop)
        return propSpec is not None


class _NoSessionOpinion(UsdviewContextMenuItem):
    def __init__(self, prop):
        self._prop = prop
        super(_NoSessionOpinion, self).__init__('Add Session Override',
                                                self._AddSessionOpinion,
                                                ())

    def _AddSessionOpinion(self):
        _CreateOpinion(self._prop)

    def IsEnabled(self):
        return True

    def ShouldDisplay(self):
        stage = self._prop.GetStage()
        propSpec = _GetPropertySpecInSessionLayer(self._prop)
        return propSpec is None


class _CreateReference(UsdviewContextMenuItem):
    def __init__(self, prim):
        self._prim = prim
        super(_CreateReference, self).__init__('Add Reference...',
                                              self._AddReference,
                                              ())

    def _AddReference(self):
        pass

    def IsEnabled(self):
        return True

    def ShouldDisplay(self):
        return True


class _VisualizeAttribute(UsdviewContextMenuItem):
    def __init__(self, prop, dataModel):
        self._prop = prop
        self._dataModel = dataModel
        super(_VisualizeAttribute, self).__init__('Visualize Attribute',
                                                 self._visualizeAttribute,
                                                 ())

    def _visualizeAttribute(self):
        # Find the associated array attribute window and update it.
        try:
            from .arrayAttributeView import ArrayAttributeView
            import weakref

            appController = self._dataModel._appController()
            if appController:
                arrayAttrViewer = ArrayAttributeView(appController, self._prop)
                arrayAttrViewer.show()
            else:
                print('Error: Failed to get the AppController. '\
                      'Unable to show the array attribute.')
        except Exception as e:
            print('Failed to launch array attribute viewer. %s' % str(e))

    def IsEnabled(self):
        return True

    def ShouldDisplay(self):
        if hasattr(self._prop, 'Get'):
            val = self._prop.Get()
            if val is not None:
                return True
        return False
