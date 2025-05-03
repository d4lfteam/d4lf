from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QSpacerItem, QStackedLayout, QVBoxLayout, QWidget


class Header(QWidget):
    def __init__(self, name, content_widget):
        super(Header, self).__init__()
        self.content = content_widget
        self.name = name
        self.expand_ico = ">"  # Use text instead of image
        self.collapse_ico = "v"  # Use text instead of image
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Create a stacked layout to hold the background and widget
        stacked = QStackedLayout(self)
        stacked.setStackingMode(QStackedLayout.StackingMode.StackAll)
        # Create a background label with a specific style sheet
        background = QLabel()
        background.setStyleSheet("QLabel{ background-color: rgb(93, 93, 93); padding-top: -20px; border-radius:2px}")

        # Create a widget and a layout to hold the icon and label
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Create an icon label and set its text and style sheet
        self.icon = QLabel()
        self.icon.setText(self.expand_ico)
        self.icon.setStyleSheet("QLabel { font-weight: bold; font-size: 20px; color: #ffffff }")
        layout.addWidget(self.icon)

        # Add the icon and the label to the layout and set margins
        layout.addWidget(self.icon)
        layout.addWidget(self.icon)
        layout.setContentsMargins(11, 0, 11, 0)

        # Create a font and a label for the header name
        font = QFont()
        font.setBold(True)
        self.label = QLabel(name)
        self.label.setStyleSheet("QLabel { margin-top: 5px; }")
        self.label.setFont(font)

        # Add the label to the layout and add a spacer for expanding
        layout.addWidget(self.label)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))

        # Add the widget and the background to the stacked layout
        stacked.addWidget(widget)
        stacked.addWidget(background)
        # Set the minimum height of the background based on the layout height
        background.setMinimumHeight(int(layout.sizeHint().height() * 1.5))
        self.collapse()

    def mousePressEvent(self, *args):
        """Handle mouse events, call the function to toggle groups"""
        # Toggle between expand and collapse based on the visibility of the content widget
        self.expand() if not self.content.isVisible() else self.collapse()

    def expand(self):
        """Expand the collapsible group"""
        self.content.setVisible(True)
        self.icon.setText(self.collapse_ico)  # Set text instead of pixmap

    def collapse(self):
        """Collapse the collapsible group"""
        self.content.setVisible(False)
        self.icon.setText(self.expand_ico)

    def set_name(self, name):
        self.name = name
        self.label.setText(name)


class Container(QWidget):
    def __init__(self, name, color_background=False):
        super(Container, self).__init__()  # Call the constructor of the parent class

        layout = QVBoxLayout(self)  # Create a QVBoxLayout instance and pass the current object as the parent
        layout.setContentsMargins(0, 0, 0, 0)  # Set the margins of the layout to 0

        self._content_widget = QWidget()  # Create a QWidget instance and assign it to the instance variable _content_widget
        if color_background:
            # If color_background is True, set the stylesheet of _content_widget to have a lighter background color
            self._content_widget.setStyleSheet(
                ".QWidget{background-color: rgb(73, 73, 73); "
                "margin-left: 2px; padding-top: 20px; margin-right: 2px}"
                ".QLabel{background-color: rgb(73, 73, 73)}"
            )

        self.header = Header(name, self._content_widget)  # Create a Header instance and pass the name and _content_widget as arguments
        layout.addWidget(self.header)  # Add the header to the layout
        layout.addWidget(self._content_widget)  # Add the _content_widget to the layout

        # assign header methods to instance attributes so they can be called outside of this class
        self.collapse = self.header.collapse  # Assign the collapse method of the header to the instance attribute collapse
        self.expand = self.header.expand  # Assign the expand method of the header to the instance attribute expand
        self.toggle = self.header.mousePressEvent  # Assign the mousePressEvent method of the header to the instance attribute toggle

    @property
    def contentWidget(self):
        """Getter for the content widget

        Returns: Content widget
        """
        return self._content_widget  # Return the _content_widget when the contentWidget property is accessed
