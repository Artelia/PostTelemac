from qgis.PyQt import uic, QtCore, QtGui

filedlg = QtGui.QFileDialog()
filedlg.setNameFilters(["Text files (*.txt)", "Images (*.png *.jpg)"])
filedlg.selectNameFilter("Images (*.png *.jpg)")




temp = filedlg.exec_()

print(temp,filedlg.selectedFiles(),filedlg.selectedNameFilter())