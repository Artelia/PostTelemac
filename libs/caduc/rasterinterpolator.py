"""
ld=qgis.analysis.QgsIDWInterpolator.LayerData
ld.vectorLayer=iface.activeLayer()

ld.zCoordInterpolation=0
ld.interpolationAttribute=5
ld.mInputType=0

#print str( qgis.analysis.QgsIDWInterpolator.layerData() )
"""

ld1 = qgis.analysis.QgsInterpolator.LayerData()
ld1.vectorLayer=iface.activeLayer()
ld1.zCoordInterpolation=0
ld1.interpolationAttribute=5
ld1.mInputType=0

#print dir(qgis.analysis.QgsIDWInterpolator)
#print dir(qgis.analysis.QgsInterpolator.LayerData)

itp=qgis.analysis.QgsIDWInterpolator([ld1])


rect = iface.mapCanvas().extent()
ncol = 10
res = 1.0
test = qgis.analysis.QgsGridFileWriter(itp,'c:/test1.asc',rect,ncol,ncol,res,res)
test.writeFile(True)

