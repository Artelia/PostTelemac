from qgis.PyQt import uic, QtCore, QtGui
try:
    from qgis.PyQt.QtGui import QDockWidget, QFileDialog
except:
    from qgis.PyQt.QtWidgets import QDockWidget, QFileDialog

if True:
    filedlg = QFileDialog()
    filedlg.setNameFilters(["Text files (*.txt)", "Images (*.png *.jpg)"])
    filedlg.selectNameFilter("Images (*.png *.jpg)")




    temp = filedlg.exec_()

    print(temp,filedlg.selectedFiles(),filedlg.selectedNameFilter())
    
if False:
    filedlg = QFileDialog()
    tempname,extension = self.qfiledlg.getOpenFileNameAndFilter(None,'Choose the file',self.loaddirectory, str1, options = QFileDialog.DontUseNativeDialog)