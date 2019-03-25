# editable tree view for groups:
# append, insert child, remove, edit text
# 

from PyQt5.QtCore import (QItemSelectionModel, Qt, QRect, pyqtSignal)
from PyQt5.QtGui import QPainter, QPalette
from PyQt5.QtWidgets import (QTreeView, QMenu, QAction, QMessageBox)

from models.GroupModel import GroupModel

class GroupTreeView(QTreeView):

    groupRemoved = pyqtSignal(list)
    itemsDropped = pyqtSignal(int) # drag items to group and drop

    def __init__(self, header, parent=None):
        ''':param headers: header of tree, e.g. ('name', 'value')
        '''
        super(GroupTreeView, self).__init__(parent)

        # model
        self.sourceModel = GroupModel(header)
        self.setModel(self.sourceModel)

        # context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.customContextMenu)

        # table style
        self.initTableStyle()
        

    def initTableStyle(self):
        # tree style
        self.resizeColumnToContents(0)
        self.header().hide()
        self.expandAll()

        # drop
        self.setAcceptDrops(True)
        self.highlightRect = QRect() # show drop indicator

        self.setSelectionMode(QTreeView.SingleSelection)
        self.setSelectionBehavior(QTreeView.SelectRows)


    def setup(self, data=[], selected_key=GroupModel.ALLGROUPS):
        '''reset tree with specified model data,
           and set the item with specified key as selected
        '''
        self.sourceModel.setup(data)       

        # refresh tree view to activate the model setting
        self.reset()
        self.expandAll()

        # set selected item        
        index = self.sourceModel.getIndexByKey(selected_key)
        if index.isValid():
            self.selectionModel().setCurrentIndex(index, QItemSelectionModel.ClearAndSelect|QItemSelectionModel.Rows)
            self.selectionModel().select(index, QItemSelectionModel.ClearAndSelect|QItemSelectionModel.Rows)

    def selectedIndex(self):
        '''get currently selected index'''
        for index in self.selectedIndexes():
            return index
        else:
            QMessageBox.warning(self, 'Warning', self.tr("Please select a group first"))
            return None

    def customContextMenu(self, position):
        '''show context menu'''
        indexes = self.selectedIndexes()
        if not len(indexes):
            return

        # init context menu
        menu = QMenu()
        menu.addAction(self.tr("Create Group"), self.slot_insertRow)
        act_sb = menu.addAction(self.tr("Create Sub-Group"), self.slot_insertChild)
        menu.addSeparator()
        act_rv = menu.addAction(self.tr("Remove Group"), self.slot_removeRow)

        # set status
        s = not self.sourceModel.isDefaultItem(indexes[0])
        act_sb.setEnabled(s)
        act_rv.setEnabled(s)

        menu.exec_(self.viewport().mapToGlobal(position))

    # ---------------------------------------------------
    # drag and drop events
    # ---------------------------------------------------
    def paintEvent(self, e):
        # default paint event
        super(GroupTreeView, self).paintEvent(e)

        # draw droping indicator
        if self.highlightRect.isValid():
            painter = QPainter(self.viewport()) # painter applying on viewpoint
            color = self.viewport().palette().color(QPalette.Highlight) # highlight
            painter.setPen(color)
            painter.drawRect(self.highlightRect)

    def dragEnterEvent(self, e):
        '''accept drag event only if 
           - the mimedata is specified by user -> tagit-item
           - target group is not UNREFERENCED
        '''
        # concern itemtable view only
        if not e.mimeData().hasFormat('tagit-item'):
            e.ignore()
            return

        # tree view item right in current cursor
        index = self.indexAt(e.pos())
        if not index.isValid():
            e.ignore()
            return

        # target group should not be UNREFERENCED,
        # as well as the right group which the dragging items belong to
        itemData = e.mimeData().data('tagit-item')
        current_group = int(str(itemData, encoding='utf-8'))
        key = index.siblingAtColumn(self.sourceModel.KEY).data()
        if key not in (current_group, self.sourceModel.ALLGROUPS, self.sourceModel.UNREFERENCED):
            self.highlightRect = self.visualRect(index) # QRect of current tree item
            self.viewport().update() # trigger paint event to update view
            e.accept()
        else:
            self.highlightRect = QRect()
            self.viewport().update()
            e.ignore()

    def dragMoveEvent(self, e):
        self.dragEnterEvent(e)

    def dropEvent(self, e):
        '''accept drag event only if the mimedata is specified type defined by user'''        
        if not e.mimeData().hasFormat('tagit-item'):
            e.ignore()
            return

        # target group
        index = self.indexAt(e.pos())
        key = index.siblingAtColumn(self.sourceModel.KEY).data()
        self.itemsDropped.emit(key)

        # clear droping indicator
        self.highlightRect = QRect()
        self.viewport().update()

        e.accept()


    # ---------------------------------------------------
    # slots
    # ---------------------------------------------------
    def slot_insertChild(self):
        '''insert child item under current selected item'''
        index = self.selectedIndex()
        if not index:
            return

        # could not insert sub-items to default items
        if self.sourceModel.isDefaultItem(index):
            return

        # insert
        if self.sourceModel.insertRow(0, index):
            child_name = self.sourceModel.index(0, self.sourceModel.NAME, index)
            child_key = self.sourceModel.index(0, self.sourceModel.KEY, index)
            self.sourceModel.setData(child_name, "[Sub Group]")
            self.sourceModel.setData(child_key, self.sourceModel.nextKey())            
            self.selectionModel().setCurrentIndex(child_name, QItemSelectionModel.ClearAndSelect)

    def slot_insertRow(self):
        '''inset item at the same level with current selected item'''
        index = self.selectedIndex()
        if not index:
            return

        # could not prepend item to default items
        row = 3 if self.sourceModel.isDefaultItem(index) else index.row() + 1
        if self.sourceModel.insertRow(row, index.parent()):
            child_name = self.sourceModel.index(row, self.sourceModel.NAME, index.parent())
            child_key = self.sourceModel.index(row, self.sourceModel.KEY, index.parent())            
            self.sourceModel.setData(child_name, "[New Group]")
            self.sourceModel.setData(child_key, self.sourceModel.nextKey())            
            self.selectionModel().setCurrentIndex(child_name, QItemSelectionModel.ClearAndSelect)

    def slot_removeRow(self):
        '''delete selected item'''
        index = self.selectedIndex()
        if not index:
            return

        reply = QMessageBox.question(self, 'Confirm', self.tr(
            "Confirm to remove '{0}' and all sub-groups under this group?\n"
            "The reference items under this group will not be deleted,"
            " but moved to UNGROUPED.".format(index.data(Qt.EditRole))), 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply != QMessageBox.Yes:
            return        
        
        # ATTENTION: get the key before any actions are applied to the tree model
        keys = index.internalPointer().keys()
        if not self.sourceModel.isDefaultItem(index): 
            self.sourceModel.removeRow(index.row(), index.parent())
            # emit removing group signal
            self.groupRemoved.emit(keys)


    def slot_updateCounter(self, items):
        '''update count of items for each group
           :param items: the latest items list
        '''
        self.sourceModel.layoutAboutToBeChanged.emit()
        self.sourceModel.updateItems(items)
        self.sourceModel.layoutChanged.emit() # update display immediately