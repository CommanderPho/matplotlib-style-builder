from __future__ import print_function, division

from collections import OrderedDict

from matplotlib.backends.qt_editor.formlayout import ColorLayout, to_qcolor

from PyQt4.QtCore import (
    pyqtSignal,
    Qt,
)

from PyQt4 import QtCore
from PyQt4 import QtGui

from PyQt4.QtGui import (
    QLabel,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QSlider,

)

def get_reasonable_range_limits(value):
    if value < 0:
        limits = (value * 4, value / 10)
    elif 0 <= value < 1:
        limits = (0, 2)
    elif 1 <= value < 10:
        limits = (0, 20)
    elif value >= 10:
        limits = (value / 10, value * 4)

    return limits


class ParamWidget(QFrame):
    sig_param_updated = pyqtSignal(object, object)

    def __init__(self, name, props):
        super(ParamWidget, self).__init__()
        self.name = name
        self.props = props

    def emit_update(self):
        self.sig_param_updated.emit(self.name, self.get_value())

    def reset_value(self):
        # TODO not tested
        self.set_value(self.props['default'])
        self.emit_update()

    def set_value(self, value):
        raise NotImplementedError()

    def get_value(self):
        raise NotImplementedError()


class ComboboxParam(ParamWidget):
    def __init__(self, name, props): # TODO could calculate default index automatically if non-integer supplied
        super(ComboboxParam, self).__init__(name, props)
        self.setLayout( QHBoxLayout() )
        self.combobox = QComboBox()
        self.layout().addWidget(self.combobox)
        options = [False, True] if props['type'] == 'bool' else props['options']
        self.choices = OrderedDict(
            (str(choice), choice) for choice in options
        )
        assert str(props['default']) in self.choices
        self.combobox.addItems(self.choices.keys())
        self.set_value(str(props['default']))
        self.combobox.currentIndexChanged.connect(self.update)

    def set_value(self, value):
        self.combobox.setCurrentIndex(
            self.choices.keys().index(str(value))
        )

    def get_value(self):
        return self.choices[str(self.combobox.currentText())]

    def update(self, _placeholder):
        new_choice = str(self.combobox.currentText())
        if new_choice not in self.choices:
            logging.error('Could not find among choices: %s (%s)',
                          new_choice,
                          self.choices)
            return
        self.emit_update()


class TextParam(ParamWidget):
    def __init__(self, name, props, default=None):
        super(TextParam, self).__init__(name, props)
        self.setLayout( QHBoxLayout() )
        self.lineedit = QLineEdit()
        self.layout().addWidget(self.lineedit)
        self.set_value(
            default or str(props['default'])  # cast because value could be none
        )
        self.lineedit.editingFinished.connect(self.update)

    def set_value(self, value):
        self.lineedit.setText(value)

    def get_value(self):
        return str(self.lineedit.text())

    def update(self):
        self.emit_update()


class ColorLayoutEmitting(ColorLayout):
    sig_color_updated = pyqtSignal()
    def update_text(self, color):
        super(ColorLayoutEmitting, self).update_text(color)
        self.sig_color_updated.emit()


class ColorParam(ParamWidget):
    def __init__(self, name, props):
        super(ColorParam, self).__init__(name, props)
        colorstr = props['default']
        self.setLayout(
            ColorLayoutEmitting(to_qcolor(colorstr))
        )
        self.layout().sig_color_updated.connect(self.emit_update)

    def set_value(self, value):
        self.layout().update_text(to_qcolor(value))
        self.layout().update_color()

    def get_value(self):
        return str(self.layout().text())


class SliderParam(ParamWidget):
    def __init__(self, name, props):
        super(SliderParam, self).__init__(name, props)
        self.setLayout( QHBoxLayout() )
        self.slider = QSlider()
        self.slider.setMouseTracking(False)
        self.slider.setProperty("value", 0)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.slider.setInvertedAppearance(False)
        self.slider.setInvertedControls(False)
        self.slider.setTickPosition(QSlider.TicksAbove)
        self.slider.setTickInterval(5)

        self.value_edit = QLineEdit('0')
        self.value_edit.setMinimumSize(QtCore.QSize(20, 0))
        self.value_edit.setMaximumWidth(100)
        self.value_edit.setAlignment(
            QtCore.Qt.AlignRight |
            QtCore.Qt.AlignTrailing |
            QtCore.Qt.AlignVCenter)

        self.layout().addWidget(self.slider, stretch=4)
        self.layout().addWidget(self.value_edit, stretch=1)

        self.slider.valueChanged.connect(self.on_slider_changed)
        self.value_edit.editingFinished.connect(self.on_box_changed)
        start_value = self.props['default']
        limits = get_reasonable_range_limits(start_value)
        self.set_minimum(limits[0])
        self.set_maximum(limits[1])
        self.set_value(start_value)

    def set_minimum(self, value):
        self.slider.setMinimum(value * 100)

    def set_maximum(self, value):
        self.slider.setMaximum(value * 100)

    def get_value(self):
        return self.slider.value() / 100

    def set_value(self, value):
        factored = value * 100
        if factored > self.slider.maximum():
            self.slider.setMaximum(factored)
        self.slider.setValue(factored)

    def on_slider_changed(self, val):
        text = "%.2f" % self.get_value()
        if str(self.value_edit.text()) != text:
            self.value_edit.setText(text)
        self.emit_update()

    def on_box_changed(self):
        text = self.value_edit.text()
        try:
            value = float(text)
        except ValueError as ve:
            logger.error('Could not convert argument to float %s', text)
            return
        self.set_value(value)
