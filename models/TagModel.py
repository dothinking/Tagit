# model, delegate for Tags table view
# 

from PyQt5.QtCore import QModelIndex, Qt, QRect, QEvent, QSize
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle, QColorDialog

from .TableModel import TableModel

class TagModel(TableModel):

    KEY, NAME, COLOR = range(3)

    NOTAG = 0

    def __init__(self, headers, parent=None):        
        super(TagModel, self).__init__(headers, parent)

        self.defaultTags = [[TagModel.NOTAG, 'Untagged', '#000000']]

        self.initData()

    def initData(self):
        # key for each item
        # key=0 is the default item: untagged
        # so common item starts from key=1
        self._currentKey = 0

        # item count for each group
        self.itemsList = []


    def getIndexByKey(self, key):
        '''get ModelIndex with specified key in the associated object'''
        for i, (tag_key, *_) in enumerate(self.dataList):
            if tag_key == key:
                return self.index(i, TagModel.NAME)
        return QModelIndex()

 
    def setup(self, tags=[]):
        '''setup model data:
           it is convenient to reset data after the model is created
        ''' 
        if not tags:
            tags = self.defaultTags

        # reset data
        self.initData()

        # calculate current key
        for key, name, color in tags:
            if self._currentKey<key:
                self._currentKey = key

        # reset model data
        self.beginResetModel()        
        self.dataList = tags        
        self.endResetModel()

    def updateItems(self, items):
        '''items for counting'''
        self.itemsList = items

    def nextKey(self):
        '''next key for new item of this model'''
        self._currentKey += 1
        return self._currentKey 

    def isDefaultItem(self, index):
        '''first row is default item -> No Tag'''
        return index.row()==0 

    def flags(self, index):
        '''item status'''
        if not index.isValid():
            return Qt.ItemIsEnabled

        if index.row()==0 or index.column() != TagModel.NAME:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index, role=Qt.DisplayRole):
        '''Table view could get data from this model'''
        if not self.checkIndex(index):
            return None

        row, col = index.row(), index.column()
        # display
        if role == Qt.DisplayRole:
            if col == TagModel.NAME:
                key = self.dataList[row][TagModel.KEY] # KEY, NAME, COLOR
                name = self.dataList[row][TagModel.NAME]
                count = 0
                for item in self.itemsList:
                    if key in item[2]: # 2=>TAGS
                        count += 1
                return '{0} ({1})'.format(name, count) if count else name
            else:
                return self.dataList[row][col]
        #edit
        elif role == Qt.EditRole:
            return self.dataList[row][col]
        else:
            return None


class TagDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(TagDelegate, self).__init__(parent)
        self.ratio = 0.55 # button width=height=ration*cell_height

    def _getButtonRect(self, rect):
        '''determin drawing area'''
        h = self.ratio*rect.height()
        w = h
        dx = (rect.width()-w)/2
        dy = (1-self.ratio)/2*rect.height()
        return rect.adjusted(dx, dy, -dx, -dy)

    def sizeHint(self, option, index):
        '''calculate size needed by the delegate to display the item''' 
        if index.column() == TagModel.COLOR:
            rect = super(TagDelegate, self).sizeHint(option, index)
            h = self.ratio*rect.height()
            return h * QSize(3, 1)
        else:
            return super(TagDelegate, self).sizeHint(option, index)

    def paint(self, painter, option, index):
        '''paint item as user defined'''
        # dismiss focus style        
        if option.state & QStyle.State_HasFocus: 
            option.state ^= QStyle.State_HasFocus

        if index.column() == TagModel.COLOR:
            painter.save()
            painter.setBrush(QColor(index.data()))
            painter.setPen(Qt.NoPen)
            rect = self._getButtonRect(option.rect)
            painter.drawRect(rect)
            painter.restore()
        else:
            super(TagDelegate, self).paint(painter, option, index)    

    def editorEvent(self, event, model, option, index):
        '''it called when editing of an item starts.
           only single click on the drawn button is allowable
        '''
        if index.column() == TagModel.COLOR:
            if self._getButtonRect(option.rect).contains(event.pos()) and event.button() == Qt.LeftButton:
                self.setModelData(None, model, index)
            return True
        else:
            return super(TagDelegate, self).editorEvent(event, model, option, index)

    def setModelData(self, editor, model, index):
        '''set model data after editing'''        
        if index.column() == TagModel.COLOR:
            color = QColorDialog.getColor(QColor(index.data()))
            if color.isValid():
                model.setData(index, color.name())
        else:
            super(TagDelegate, self).setModelData(editor, model, index)