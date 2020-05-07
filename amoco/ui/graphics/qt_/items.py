# -*- coding: utf-8 -*-
try:
    from PyQt5.QtCore import pyqtSignal, Qt
    from PyQt5.QtWidgets import *
    from PyQt5.QtGui import QPainter
except ImportError:
    from PySide2.QtCore import Signal, QPointF, Qt
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *

from math import sin, cos, pi, radians

# ------------------------------------------------------------------------------


class Node_basic(QGraphicsItem):
    """Node_basic is a QGraphicsItem that represents a function node, used as
       a view for a cfg.node of code.func or code.xfunc object.

       The object is movable, focusable and accepts mouse-over events.
       It is composed of a shadowed circle of radius *r* colored in white,
       and a blue label set as the function's name.

       Arguments:

           name (string): string used as label for the Node_basic.label.
           r (int): radius of the Node_basic.el circle.

       Attributes:
       
           el (QGraphicsEllipseItem): the cicle object
           label (QGraphicsTextItem): the label object
           cx (list[Edge_basic]): list of edges views associated with the node 
    """

    def __init__(self, name="?", r=10):
        super(Node_basic, self).__init__()
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsFocusable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        # define circle shape:
        w = 2 * r + 2
        self.el = QGraphicsEllipseItem(0, 0, w, w)
        self.el.setBrush(QBrush(QColor("white")))
        shadow = QGraphicsDropShadowEffect()
        shadow.setOffset(4)
        self.el.setGraphicsEffect(shadow)
        self.el.setParentItem(self)
        # define node label shape:
        self.label = QGraphicsTextItem(name)
        self.label.setDefaultTextColor(QColor("blue"))
        self.label.setFlag(QGraphicsItem.ItemIsSelectable)
        self.label.setParentItem(self)
        self.el.setZValue(1.0)
        self.label.setZValue(2.0)
        center = self.center() - self.label.boundingRect().center()
        self.label.setPos(self.mapFromScene(center))
        self.setZValue(1.0)
        self.cx = []

    def boundingRect(self):
        e = self.el.boundingRect()
        l = self.label.boundingRect()
        l = self.mapRectToItem(self, l)
        return e.united(l)

    def shape(self):
        e = self.el.shape()
        l = self.label.shape()
        l = self.mapToItem(self, l)
        return e.united(l)

    def paint(self, painter, option, widget=None):
        pass

    def center(self):
        return self.el.sceneBoundingRect().center()

    def focusOutEvent(self, event):
        self.label.setTextInteractionFlags(Qt.NoTextInteraction)
        super(Node_basic, self).focusOutEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.label.textInteractionFlags() == Qt.NoTextInteraction:
            self.label.setTextInteractionFlags(Qt.TextEditorInteraction)
        super(Node_basic, self).mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for e in self.cx:
                e.update_points()
        return super(Node_basic, self).itemChange(change, value)

    def contextMenuEvent(self, event):
        menu = QMenu()
        testAction = QAction("Test", None)
        testAction.triggered.connect(self.print_out)
        menu.addAction(testAction)
        menu.exec_(event.screenPos())

    def print_out(self):
        print("Triggered")


# ------------------------------------------------------------------------------


class Node_codeblock(QGraphicsItem):
    """Node_codeblock is a QGraphicsItem that represents a block node, used as a
       view for a cfg.node of code.block object.

       The object is movable, focusable and accepts mouse-over events.
       It is composed of a shadowed rectangle (QGraphicsRectItem) that contains
       a text block (QGraphicsTextItem) with the assembly instructions formatted
       as an Html source for pretty printing.

       Arguments:

           block (code.block): the block object

       Attributes:
       
           codebox (QGraphicsRectItem): the shadowed rectangular background
           code (QGraphicsTextItem): the assembly text of the input block
           cx (list[Edge_basic]): list of edges views associated with the node 
    """

    def __init__(self, block):
        super(Node_codeblock, self).__init__()
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsFocusable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        # define code text shape:
        self.code = QGraphicsTextItem()
        self.code.setHtml(block)
        f = QFont("Monospace")
        f.setPointSize(8)
        self.code.setFont(f)
        self.code.setParentItem(self)
        # define circle shape:
        self.codebox = QGraphicsRectItem(
            self.code.boundingRect().adjusted(-2, -2, 2, 2)
        )
        self.codebox.setBrush(QBrush(QColor("#fdf6e3")))
        shadow = QGraphicsDropShadowEffect()
        shadow.setOffset(4)
        self.codebox.setGraphicsEffect(shadow)
        self.codebox.setParentItem(self)
        self.codebox.setZValue(1.0)
        self.code.setZValue(2.0)
        center = (
            self.codebox.boundingRect().center() - self.code.boundingRect().center()
        )
        self.code.setPos(center)
        self.setZValue(1.0)
        self.cx = []

    def boundingRect(self):
        b = self.codebox.boundingRect()
        return b

    def center(self):
        return self.codebox.sceneBoundingRect().center()

    def shape(self):
        return self.codebox.shape()

    def paint(self, painter, option, widget=None):
        pass

    def hoverEnterEvent(self, event):
        self.codebox.setBrush(QBrush(QColor("white")))
        super(Node_codeblock, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.codebox.setBrush(QBrush(QColor("#fdf6e3")))
        self.code.setTextInteractionFlags(Qt.NoTextInteraction)
        super(Node_codeblock, self).hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.code.textInteractionFlags() == Qt.NoTextInteraction:
            self.code.setTextInteractionFlags(Qt.TextEditorInteraction)
        super(Node_codeblock, self).mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for e in self.cx:
                e.update_points()
        return super(Node_codeblock, self).itemChange(change, value)


# ------------------------------------------------------------------------------


class Edge_basic(QGraphicsItem):
    """Edge_basic is a QGraphicsItem that represents an edge, used as a
       view for a cfg.Edge object.

       The object is not movable or focusable but should accept mouse
       events to highlight or tag the nodes of this edge.
       It is composed of a QGraphicsPathItem build from self.points
       and a triangular arrow head positioned at the border of the node's
       view. It should react to nodes n0/n1 displacements.

       Arguments:

           n0 (Node_codeblock|Node_basic): first node (from).
           n1 (Node_codeblock|Node_basic): second node (to).

        Attributes:

            n (list): the list of node views.
            points (list[QPointF]): list of points for routing the edge.
            head (QPolygonF): the arrow head polygon.
    """

    def __init__(self, n0, n1):
        super(Edge_basic, self).__init__()
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.n = [n0, n1]
        n0.cx.append(self)
        n1.cx.append(self)
        self.points = [None, None]
        self.head = None
        self.update_points()

    def setpath(self, l):
        self.points = [QPointF(*p) for p in l]
        self.update_points()

    def update_points(self):
        self.prepareGeometryChange()
        self.points[0] = self.n[0].center()
        self.points[-1] = self.n[1].center()
        self.adjust()

    def adjust(self):
        nend = self.n[1]
        nendshape = nend.shape()
        s = nend.mapToScene(nendshape)
        x = s.intersected(self.shape())
        self.points[-1] = x.pointAtPercent(1.0)

    def boundingRect(self):
        br = self.getqgp().boundingRect()
        if self.head:
            br = br.united(self.head.boundingRect())
        return br

    def getqgp(self):
        """Compute the QGraphicsPathItem that represents the open
           polygonal line going through all self.points.
        """
        qpp = QPainterPath(self.points[0])
        for p in self.points[1:]:
            qpp.lineTo(p)
        return QGraphicsPathItem(qpp)

    def shape(self):
        s = self.getqgp().shape()
        if self.head:
            s.addPolygon(self.head)
        return s

    def paint(self, painter, option, widget=None):
        qgp = self.getqgp()
        pen = QPen()
        pen.setWidth(2)
        qgp.setPen(pen)
        qgp.setBrush(QBrush(Qt.NoBrush))
        painter.setClipRect(option.exposedRect)
        qgp.paint(painter, option, widget)
        lastp = self.points[-1]
        angle = radians(qgp.path().angleAtPercent(1.0))
        angle = angle + pi
        p = lastp + QPointF(cos(angle - pi / 6.0) * 10, -sin(angle - pi / 6.0) * 10)
        q = lastp + QPointF(cos(angle + pi / 6.0) * 10, -sin(angle + pi / 6.0) * 10)
        painter.setBrush(QBrush(QColor("black")))
        self.head = QPolygonF([lastp, p, q])
        painter.drawPolygon(self.head)
