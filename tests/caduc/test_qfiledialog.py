from qgis.PyQt import uic, QtCore, QtGui
try:
    from qgis.PyQt.QtGui import QDockWidget, QFileDialog
except:
    from qgis.PyQt.QtWidgets import QDockWidget, QFileDialog

if False:
    filedlg = QFileDialog()
    filedlg.setNameFilters(["Text files (*.txt)", "Images (*.png *.jpg)"])
    filedlg.selectNameFilter("Images (*.png *.jpg)")




    temp = filedlg.exec_()

    print(temp,filedlg.selectedFiles(),filedlg.selectedNameFilter())
    
if True:
    filedlg = QFileDialog()
    #tempname,extension = filedlg.getOpenFileName(None,'Choose the file',None, "Text files (*.txt) ;; Images (*.png *.jpg)", options = QFileDialog.DontUseNativeDialog)
    tempname = filedlg.getOpenFileName(None,'Choose the file',None, "Text files (*.txt);; Images (*.png *.jpg)")
    print('tempname',tempname)
    print(filedlg.selectedNameFilter())
    print(filedlg.selectedFilter () )
    