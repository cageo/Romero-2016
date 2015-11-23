# encoding: utf-8
'''
@author:     Jose Emilio Romero Lopez

@license:    GPL

@contact:    jemromerol@gmail.com

  This file is part of APASVO.

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from PySide import QtCore
from PySide import QtGui
import numpy as np

from apasvo.gui.views import navigationtoolbar
from apasvo.gui.views import tsvwidget
from apasvo.gui.views import staltadialog
from apasvo.gui.views import ampadialog
from apasvo.picking import stalta
from apasvo.picking import ampa
from apasvo.gui.models import pickingtask
from apasvo.gui.models import eventcommands as commands
from apasvo.gui.views import error

from apasvo._version import _application_name
from apasvo._version import _organization


class TraceSelectorDialog(QtGui.QMainWindow):
    """A dialog to apply Takanami's AR picking method to a selected piece of a
    seismic signal.

    Attributes:
        document: Current opened document containing a seismic record.
        seismic_event: A seismic event to be refined by using Takanami method.
            If no event is provided, then a new seismic event will be created
            by using the estimated arrival time after clicking on 'Accept'
    """

    closed = QtCore.Signal()
    selection_changed = QtCore.Signal(int)
    events_created = QtCore.Signal(dict)
    events_deleted = QtCore.Signal(dict)
    detection_performed = QtCore.Signal()

    def __init__(self, stream, parent):
        super(TraceSelectorDialog, self).__init__(parent)

        self.main_window = parent
        self.stream = stream

        self._init_ui()


    def _init_ui(self):
        self.set_title()
        # Create main structure
        self.centralwidget = QtGui.QWidget(self)
        self.centralwidget.setVisible(False)
        self.setCentralWidget(self.centralwidget)
        self.layout = QtGui.QVBoxLayout(self.centralwidget)
        self.stream_viewer = tsvwidget.StreamViewerWidget(self)
        self.layout.addWidget(self.stream_viewer)

        # Add main toolbar
        self.tool_bar_main = QtGui.QToolBar(self)
        self.action_save = QtGui.QAction(self)
        self.action_save.setIcon(QtGui.QIcon(":/save.png"))
        self.action_save.setEnabled(False)
        self.action_close = QtGui.QAction(self)
        self.action_close.setIcon(QtGui.QIcon(":/close.png"))
        self.action_close.setEnabled(False)
        self.tool_bar_main.addAction(self.action_save)
        self.tool_bar_main.addAction(self.action_close)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.tool_bar_main)

        # Add analysis toolbar
        self.tool_bar_analysis = QtGui.QToolBar(self)
        self.action_sta_lta = QtGui.QAction(self)
        self.action_sta_lta.setIcon(QtGui.QIcon(":/stalta.png"))
        self.action_sta_lta.setEnabled(False)
        self.action_sta_lta.setToolTip("Apply STA-LTA algorithm")
        self.action_ampa = QtGui.QAction(self)
        self.action_ampa.setIcon(QtGui.QIcon(":/ampa.png"))
        self.action_ampa.setEnabled(False)
        self.action_ampa.setToolTip("Apply AMPA algorithm")
        self.tool_bar_analysis.addAction(self.action_sta_lta)
        self.tool_bar_analysis.addAction(self.action_ampa)
        # self.tool_bar_analysis.addSeparator()
        # self.action_activate_threshold = QtGui.QAction(self)
        # self.action_activate_threshold.setIcon(QtGui.QIcon(":/threshold.png"))
        # self.action_activate_threshold.setCheckable(True)
        # self.action_activate_threshold.setChecked(False)
        # self.action_activate_threshold.setToolTip("Enable/Disable Threshold")
        # self.tool_bar_analysis.addAction(self.action_activate_threshold)
        # self.threshold_label = QtGui.QLabel(" Threshold value: ", parent=self.tool_bar_analysis)
        # self.threshold_label.setEnabled(False)
        # self.tool_bar_analysis.addWidget(self.threshold_label)
        # self.threshold_spinbox = QtGui.QDoubleSpinBox(self.tool_bar_analysis)
        # self.threshold_spinbox.setMinimum(0.0)
        # self.threshold_spinbox.setMaximum(20.0)
        # self.threshold_spinbox.setSingleStep(0.01)
        # self.threshold_spinbox.setValue(1.0)
        # self.threshold_spinbox.setAccelerated(True)
        # self.threshold_spinbox.setEnabled(False)
        # self.tool_bar_analysis.addWidget(self.threshold_spinbox)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.tool_bar_analysis)

        # Add navigation toolbar
        # self.tool_bar_navigation = navigationtoolbar.NavigationToolBar(self.stream_viewer.canvas, self)
        # self.addToolBar(QtCore.Qt.TopToolBarArea, self.tool_bar_navigation)
        # self.addToolBarBreak()

        # set up status bar
        self.statusbar = QtGui.QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)
        self.analysis_label = QtGui.QLabel("", self.statusbar)
        self.analysis_progress_bar = QtGui.QProgressBar(self.statusbar)
        self.analysis_progress_bar.setOrientation(QtCore.Qt.Horizontal)
        self.analysis_progress_bar.setRange(0, 0)
        self.analysis_progress_bar.hide()
        self.statusbar.addPermanentWidget(self.analysis_label)
        self.statusbar.addPermanentWidget(self.analysis_progress_bar)

        # Connect widget signals
        self.events_created.connect(self.stream_viewer.update_markers)
        self.events_deleted.connect(self.stream_viewer.update_markers)
        self.stream_viewer.trace_selected.connect(lambda x: self.selection_changed.emit(x))
        self.stream_viewer.selection_made.connect(self.action_close.setEnabled)
        self.action_sta_lta.triggered.connect(self.doSTALTA)
        self.action_ampa.triggered.connect(self.doAMPA)
        self.action_close.triggered.connect(self.close_selected_traces)

    def closeEvent(self, event):
        settings = QtCore.QSettings(_organization, _application_name)
        settings.beginGroup("geometry")
        settings.setValue("trace_selector", self.saveGeometry())
        settings.endGroup()
        self.closed.emit()
        super(TraceSelectorDialog, self).closeEvent(event)

    def showEvent(self, event):
        settings = QtCore.QSettings(_organization, _application_name)
        settings.beginGroup("geometry")
        self.restoreGeometry(settings.value("trace_selector"))
        settings.endGroup()
        super(TraceSelectorDialog, self).showEvent(event)

    def set_title(self):
        self.setWindowTitle("Opened Traces - {}".format(", ".join([tr.id for tr in self.stream])))

    def set_stream(self, stream):
        self.stream = stream
        self.stream_viewer.set_stream(self.stream)
        stream_has_any_trace = len(self.stream)
        self.centralwidget.setVisible(stream_has_any_trace)
        self.action_sta_lta.setEnabled(stream_has_any_trace)
        self.action_ampa.setEnabled(stream_has_any_trace)
        self.set_title()

    def update_events(self, *args, **kwargs):
        self.stream_viewer.update_markers()

    def doSTALTA(self):
        """Performs event detection/picking by using STA-LTA method."""
        dialog = staltadialog.StaLtaDialog(self.stream)
        return_code = dialog.exec_()
        if return_code == QtGui.QDialog.Accepted:
            # Read settings
            settings = QtCore.QSettings(_organization, _application_name)
            settings.beginGroup('stalta_settings')
            sta_length = float(settings.value('sta_window_len', 5.0))
            lta_length = float(settings.value('lta_window_len', 100.0))
            settings.endGroup()
            # # Get threshold value
            # if self.actionActivateThreshold.isChecked():
            #     threshold = self.thresholdSpinBox.value()
            # else:
            #     threshold = None
            # # Create an STA-LTA algorithm instance with selected settings
            alg = stalta.StaLta(sta_length, lta_length)
            # perform task
            selected_traces = self.stream_viewer.selected_traces
            selected_traces = selected_traces if selected_traces else self.stream_viewer.stream.traces
            analysis_task = pickingtask.PickingStreamTask(self,
                                                          alg,
                                                          trace_list=selected_traces)
            self.launch_analysis_task(analysis_task,
                                      label="Applying %s..." % alg.__class__.__name__.upper())

    def doAMPA(self):
        """Performs event detection/picking by using AMPA method."""
        dialog = ampadialog.AmpaDialog(self.stream)
        return_code = dialog.exec_()
        if return_code == QtGui.QDialog.Accepted:
            # Read settings
            settings = QtCore.QSettings(_organization, _application_name)
            settings.beginGroup('ampa_settings')
            wlen = float(settings.value('window_len', 100.0))
            wstep = float(settings.value('step', 50.0))
            nthres = float(settings.value('noise_threshold', 90))
            filters = settings.value('filters', [30.0, 20.0, 10.0,
                                                               5.0, 2.5])
            filters = list(filters) if isinstance(filters, list) else [filters]
            filters = np.array(filters).astype(float)
            settings.beginGroup('filter_bank_settings')
            startf = float(settings.value('startf', 2.0))
            endf = float(settings.value('endf', 12.0))
            bandwidth = float(settings.value('bandwidth', 3.0))
            overlap = float(settings.value('overlap', 1.0))
            settings.endGroup()
            settings.endGroup()
            # Get threshold value
            # if self.actionActivateThreshold.isChecked():
            #     threshold = self.thresholdSpinBox.value()
            # else:
            #     threshold = None
            # Create an AMPA algorithm instance with selected settings
            alg = ampa.Ampa(wlen, wstep, filters, noise_thr=nthres,
                            bandwidth=bandwidth, overlap=overlap,
                            f_start=startf, f_end=endf)
            # perform task
            selected_traces = self.stream_viewer.selected_traces
            selected_traces = selected_traces if selected_traces else self.stream_viewer.stream.traces
            analysis_task = pickingtask.PickingStreamTask(self,
                                                          alg,
                                                          trace_list=selected_traces)
            self.launch_analysis_task(analysis_task,
                                      label="Applying %s..." % alg.__class__.__name__.upper())

    def launch_analysis_task(self, task, label=""):
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.action_ampa.setEnabled(False)
        self.action_sta_lta.setEnabled(False)
        self.analysis_label.setText(label)
        self.analysis_progress_bar.show()
        self._thread = QtCore.QThread(self)
        task.moveToThread(self._thread)
        self._thread.started.connect(task.run)
        task.finished.connect(self._thread.quit)
        task.finished.connect(self.on_analysis_finished)
        task.finished.connect(task.deleteLater)
        task.error.connect(error.display_error_dlg)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def on_analysis_finished(self):
        QtGui.QApplication.restoreOverrideCursor()
        self.action_ampa.setEnabled(True)
        self.action_sta_lta.setEnabled(True)
        self.analysis_progress_bar.hide()
        self.analysis_label.setText("")

    def close_selected_traces(self):
        selected_traces_idx = [self.stream.traces.index(trace) for trace in self.stream_viewer.selected_traces]
        if selected_traces_idx:
            self.main_window.command_stack.push(commands.CloseTraces(self.main_window, selected_traces_idx))