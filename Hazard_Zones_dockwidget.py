# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HazardZonesByFlowDockWidget
                                 A QGIS plugin
 This Plugin is for the evaluation of hazard zones by torrent flow from pond/dam breach
                             -------------------
        begin                : 2017-06-12
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Ruben Munoz Sanchez
        email                : ruben46@usal.es
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import os,sys
import shutil
reload(sys)
sys.setdefaultencoding("utf-8")
from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal
from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import QgsApplication,QgsCoordinateReferenceSystem
from qgis.core import *
from qgis.core import (QgsGPSDetector, QgsGPSConnectionRegistry, QgsPoint, \
                        QgsCoordinateTransform, QgsCoordinateReferenceSystem, \
                        QgsGPSInformation)
from qgis.core import QgsMapLayerRegistry
from qgis.gui import *
from PyQt4.QtCore import *
import struct
import constants
from osgeo import gdal, osr
import numpy as np
import time



FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Hazard_Zones_dockwidget_base.ui'))


class HazardZonesByFlowDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self,
                 iface,
                 parent=None):
        """Constructor."""
        super(HazardZonesByFlowDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.iface = iface
        self.initialize()
        self.initializeRasterComboBox()
        self.output_format()
        self.canvas = self.iface.mapCanvas()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def initialize(self):
        # Inicio la lectura de capas en el combobox
        self.initializeRasterComboBox()

        self.iface.mapCanvas().mapRenderer().setProjectionsEnabled(True)

        #Variable de control de pulsación de RadioButton
        self.RadioB = False
        self.RadioB_u = False

        # Etiqueta de estado
        self.status(-1)

        # Contador de ejecuciones del programa que llegan hasta el final
        self.ejecuciones = 1

        # Variable para evitar que salga error de sobreescribir datos
        self.var_directorio = False

        # Eventos
        QtCore.QObject.connect(self.startPushButton, QtCore.SIGNAL("clicked(bool)"), self.startProcess)
        self.rasterComboBox.activated.connect(self.loadSourcePath)
        QtCore.QObject.connect(self.cmdBrowse, QtCore.SIGNAL("clicked(bool)"), self.output_patch)
        QtCore.QObject.connect(self.velocidadRadioButton, QtCore.SIGNAL('toggled(bool)'), self.change_units_v)
        QtCore.QObject.connect(self.caladoRadioButton, QtCore.SIGNAL('toggled(bool)'), self.change_units_c)
        QtCore.QObject.connect(self.productRadioButton, QtCore.SIGNAL('toggled(bool)'), self.change_units_p)
        QtCore.QObject.connect(self.usRadioButton, QtCore.SIGNAL('toggled(bool)'), self.control_RB_units)
        QtCore.QObject.connect(self.siRadioButton, QtCore.SIGNAL('toggled(bool)'), self.control_RB_units)
        self.nameoutLineEdit.textChanged.connect(self.actualice_text)
        self.nameoutLineEdit.textChanged.connect(self.actualice_directorio)

        QtCore.QObject.connect(self.iface, QtCore.SIGNAL('layersChanged()'), self.layer_changed)

    def layer_changed(self):
        self.rasterComboBox.clear()
        for layer in self.canvas.layers():
            self.rasterComboBox.addItem(layer.name())

    def actualice_directorio(self):
        # Función que si detecta que ha cambiado el texto del line edit, cambia de valor la variable para que el
        # programa sepa que se ha actualizado el nombre
        self.var_directorio = True

    def actualice_text(self):
        # Actualización al camiar el texto del line edit de nombre de la capa de salida
        if self.ejecuciones > 1:
            self.status(0)
        self.progressBar.setValue(0)

    def control_RB_units (self):
        # Activo la variable que continua la ejecución del proceso
        self.RadioB_u = True
        # Activo los componentes del GroupBox del Raster de Salida
        self.formatComboBox.setEnabled(True)
        self.nameoutLineEdit.setEnabled(True)
        self.OuptDir.setEnabled(True)
        self.cmdBrowse.setEnabled(True)
        self.resultCheckBox.setEnabled(True)
        # Barra progreso y label:
        if self.ejecuciones > 1:
            self.status(5)
        self.progressBar.setValue(0)

    def change_units_c(self):
        self.siRadioButton.setText("m")
        self.usRadioButton.setText("ft")
        self.RadioB = True
        if self.unitsGroupBox.setEnabled != True:
            self.unitsGroupBox.setEnabled(True)
        # Actualización al actualizar el line edit de nombre de la capa de salida
        if self.ejecuciones > 1:
            self.status(5)
        self.progressBar.setValue(0)

    def change_units_v(self):
        self.siRadioButton.setText("m/s")
        self.usRadioButton.setText("ft/s")
        # Modifico la variable que controla si el usuario ha seleccionado las unidades
        self.RadioB = True
        # Activo el siguiente Group Box
        if self.unitsGroupBox.setEnabled != True:
             self.unitsGroupBox.setEnabled(True)
        # Actualización al actualizar el line edit de nombre de la capa de salida
        if self.ejecuciones > 1:
                self.status(5)
        self.progressBar.setValue(0)

    def change_units_p(self):
        self.siRadioButton.setText("m2/s")
        self.usRadioButton.setText("ft2/s")
        self.RadioB = True
        if self.unitsGroupBox.setEnabled != True:
            self.unitsGroupBox.setEnabled(True)
        # Actualización al actualizar el line edit de nombre de la capa de salida
        if self.ejecuciones > 1:
            self.status(5)
        self.progressBar.setValue(0)

    def comprobaciom_cambio_nombre(self):
        if self.nombre != self.nameoutLineEdit.text():
            self.nombre = self.nameoutLineEdit.text()
            self.OuptDir.setText(self.dirname +"/" + self.nombre + "." + self.extension)
            self.var_directorio = True

    #Función para escribir la extensión en el nombre del archivo de salida
    def extension_name_out (self):
        if str(self.formatComboBox.currentText()) == "GTiff":
            self.extension = "tif"

    def file_name_out(self):
        # Función para determinar el nombre de la capa de salida
        # Si el usuario no pone nada, la capa de salida se denomina "output_raster"
        if self.nameoutLineEdit.text() == "":
            self.nombre = "output_raster"+ str(self.ejecuciones)
        elif self.nameoutLineEdit.text() == "output_raster" + str(self.ejecuciones-1):
            self.nombre = "output_raster" + str(self.ejecuciones)
        else:
            self.nombre = str(self.nameoutLineEdit.text())

    def finish(self):
        # Activo botón de lanzar proceso
        self.startPushButton.setEnabled(True)
        # Actualizo etiqueta de estado
        self.status(4)
        # Actualizo Barra de progreso
        self.progressBar.setValue(100)
        self.iface.messageBar().pushMessage("Hazard Zones by Flow", " The process has been succesful",
                                            level=QgsMessageBar.INFO, duration=5)
        self.ejecuciones = self.ejecuciones + 1

        self.var_directorio = False

    def initializeRasterComboBox(self):
        # Añado las capas al combobox de selección de capa
        self.rasterComboBox.clear()
        self.rasterComboBox.addItem(constants.CONST_HAZARD_ZONES_BY_FLOW_COMBOBOX_NO_SELECT_OPTION)
        for layer in self.iface.mapCanvas().layers():
            # Añado únicamente si es raster
            if layer.type() == layer.RasterLayer:
                self.rasterComboBox.addItem(layer.name(), layer.id())

    def layer_and_units(self):
        # Modifico el parámetro de comparación de celdas en función de la variable y las unidades elegidas por el
        # usuario.
        if self.caladoRadioButton.isChecked() and self.siRadioButton.isChecked():
            self.ParamHidra = 1
        if self.caladoRadioButton.isChecked() and self.usRadioButton.isChecked():
            self.ParamHidra = 3.28084
        if self.velocidadRadioButton.isChecked() and self.siRadioButton.isChecked():
            self.ParamHidra = 1
        if self.velocidadRadioButton.isChecked() and self.usRadioButton.isChecked():
            self.ParamHidra = 3.28084
        if self.productRadioButton.isChecked() and self.siRadioButton.isChecked():
            self.ParamHidra = 0.5
        if self.productRadioButton.isChecked() and self.usRadioButton.isChecked():
            self.ParamHidra = 5.38196

    def loadSourcePath(self):
        # Función para añadir al line edit la ruta del archivo de entrada
        if self.sourceRaster() is not None:
            self.sourceRasterPathLineEdit.setText( self.sourceRaster().dataProvider().dataSourceUri() )
        if self.sourceRasterPathLineEdit.text() != "":
            self.HydraulicGroupBox.setEnabled(True)

        # Si se ha ejecutado alguna vez el programa, cambio la etiqueta de estado a "Ready to go"
        if self.ejecuciones > 1:
            self.status(0)
            self.progressBar.setValue(0)
        else:
            self.status(5)


    def output_format(self):
        # Se añade la etiqueta de los formatos compatibles de salida al combobox correspondiente
        self.formatComboBox.addItem("GTiff")

    # Función para escribir el directorio de la capa de salida
    def output_patch(self):
        # Ejecuto las funciones para conocer el nombre y extensión del archivo de salida
        self.file_name_out()
        self.extension_name_out()
        # Diálogo de selección de carpeta
        self.dirname = str(QtGui.QFileDialog.getExistingDirectory(self, "Select Directory"))
        # Limpio el line Edit
        self.OuptDir.clear()
        # Escribo en el line Edit la ruta, el nombre y la extensión del archivo
        self.OuptDir.setText(self.dirname + "/" + self.nombre + "." + self.extension)
        # Actualizo estado del programa y barra de progreso
        self.status(0)
        self.progressBar.setValue(0)

        # Actualizo el nombre del resultado
        self.nameoutLineEdit.setText(self.nombre)

        self.var_directorio = True

    def refreshStates(self):
        # Función para inicializar la lectura de capas
        self.initializeRasterComboBox()

    def sourceRaster(self):
        """
        Returns the current toBend layer depending on what is choosen in the pairsLayerComboBox
        """
        layerId = self.rasterComboBox.itemData(self.rasterComboBox.currentIndex())
        return QgsMapLayerRegistry.instance().mapLayer(layerId)

    def sourceRasterPath(self):
        """
        Returns the current source raster path
        """
        return self.sourceRasterPathLineEdit.text()

    def startProcess(self):

            #Selecciono la capa actual en función la que ha seleccionado el usuario en el combobox
            current_layer =self.sourceRasterPathLineEdit.text()
            layer = self.rasterComboBox.itemData(self.rasterComboBox.currentIndex())

            if str(self.rasterComboBox.currentText()) != constants.CONST_HAZARD_ZONES_BY_FLOW_COMBOBOX_NO_SELECT_OPTION:

                if self.RadioB == True:

                    # Llamo a la función que detecta, según preferencia del usuario, cuál es la variable hidráulica y qué
                    # unidades tiene
                    self.layer_and_units()

                    if self.RadioB_u == True:

                        if not self.resultCheckBox.isChecked():
                            self.var_directorio = True


                        if self.OuptDir.text() != "":
                            # Lanzo la comprobación para ver si el usuario ha cambiado el nombre
                            self.comprobaciom_cambio_nombre()

                            if self.var_directorio == True:

                                # Desconecto el botón de Start y conecto el start
                                self.startPushButton.setEnabled(False)

                                # Función Control del estado del programa
                                self.status(1)

                                # La variable path almacena la ruta
                                path = current_layer
                                (raiz, filename) = os.path.split(path)
                                dataset = gdal.Open(path)

                                # Adquiero la proyección
                                prj = dataset.GetProjection()

                                # Configuración de la banda raster
                                number_band = 1
                                band = dataset.GetRasterBand(number_band)

                                # Obtengo los metadatos del raster
                                geotransform = dataset.GetGeoTransform()

                                # Set name of output raster
                                # La ruta de guardado del raster de salida, coincide con la que se ha almacenado en el line edit
                                output_file =  str(self.OuptDir.text())

                                # Create gtif file with rows and columns from parent raster
                                # Selecciono el formato en función de lo que ha decidido el usuario, dentro del paréntesis debería
                                # poner "GTiff", importante que vaya en string
                                self.formato = self.formatComboBox.currentText()
                                driver = gdal.GetDriverByName(str(self.formato))

                                ####raster = self.changeRasterValues(band)
                                fmttypes = {'Byte': 'B', 'UInt16': 'H', 'Int16': 'h', 'UInt32': 'I', 'Int32': 'i', 'Float32': 'f',
                                            'Float64': 'd'}

                                # Configuración de la banda
                                data_type = band.DataType
                                BandType = gdal.GetDataTypeName(band.DataType)
                                raster = []
                                contador = 0
                                lenbanda = len(range(band.YSize))
                                for y in range(band.YSize):
                                    contador = contador + 1
                                    scanline = band.ReadRaster(0, y, band.XSize, 1, band.XSize, 1, data_type)
                                    values = struct.unpack(fmttypes[BandType] * band.XSize, scanline)
                                    raster.append(values)
                                    self.progressBar.setValue(contador * 19 / lenbanda)

                                raster = [list(item) for item in raster]

                                # Cuento las columnas y las filas del raster. Importante para conocer el número de
                                # iteraciones del bucle.
                                cols = len(item)
                                rows = len(raster)

                                # Actualizo etiqueda de estado
                                self.status(2)
                                # Contador para controlar el progres bar.
                                contador = 0
                                # Bucle que cambia los valores del raster, en función de la variables que haya introducido el usuario
                                for i, item in enumerate(raster):
                                    contador = contador + 1
                                    for j, value in enumerate(item):
                                        contador = contador + 1
                                        if value < self.ParamHidra:
                                            raster[i][j] = None
                                        #if value < self.ParamHidra:
                                        else:
                                            raster[i][j] =  1
                                            #isnan(float(raster[i][j]))
                                        #Actualizao la barra de progreso
                                        self.progressBar.setValue(19 + int(contador * 77.5 / (cols*rows)))

                                self.status(3)
                                self.progressBar.setValue(97)

                                # Transformación de la lista en array
                                raster = np.asarray(raster)

                                #enconding: utf-8
                                dst_ds = driver.Create(output_file,
                                                       band.XSize,
                                                       band.YSize,
                                                       number_band,
                                                       data_type)
                                self.progressBar.setValue(98)

                                # Aquí se escribe el raster de salida
                                dst_ds.GetRasterBand(number_band).WriteArray(raster)
                                # Las celdas que son igual a 0, los cambio a No data
                                dst_ds.GetRasterBand(number_band).SetNoDataValue(0)

                                # Configuración de la extensión
                                # top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
                                dst_ds.SetGeoTransform(geotransform)

                                # setting spatial reference of output raster
                                srs = osr.SpatialReference(wkt=prj)
                                dst_ds.SetProjection(srs.ExportToWkt())
                                self.progressBar.setValue(99)

                                band.FlushCache()

                                # Se cierra el raster
                                band = None
                                dst_ds = None
                                dataset = None

                                # Ejecuto la función de finalización
                                self.finish()

                                #Si el usuario ha dejado marcado el CheckBox correspondiente, se añade la capa resultado al proyecto
                                if self.resultCheckBox.isChecked():
                                    self.iface.addRasterLayer(output_file)
                                    self.iface.legendInterface().refreshLayerSymbology(str(output_file))

                            else:
                                QMessageBox.warning(None, constants.CONST_HAZARD_ZONES_BY_FLOW__WINDOW_TITLE,
                                                    self.tr("Cannot overwrite file. Please change the name layer or output directory"))
                                self.status(5)
                                self.progressBar.setValue(0)
                        else:
                            QMessageBox.warning(None, constants.CONST_HAZARD_ZONES_BY_FLOW__WINDOW_TITLE,
                                                self.tr("Please specify the parameters of the result layer"))
                    else:
                        QMessageBox.warning(None, constants.CONST_HAZARD_ZONES_BY_FLOW__WINDOW_TITLE,
                                            self.tr("Please specify: Units"))
                elif self.RadioB == False:
                    QMessageBox.warning(None, constants.CONST_HAZARD_ZONES_BY_FLOW__WINDOW_TITLE,
                                        self.tr("Please specify: Type of hydraulic data"))
            else:
                QMessageBox.warning(None, constants.CONST_HAZARD_ZONES_BY_FLOW__WINDOW_TITLE,
                                    self.tr("Please specify the input layer"))

    def status(self, estado):
        # Función para el control de la etiqueta de estado.
        if estado == -1:
            info_program = "Status label"
        if estado == 0:
            info_program = "Ready to go"
        if estado == 1:
            info_program = "Reading layer"
        if estado == 2:
            info_program = "Changing pixel values"
        if estado == 3:
            info_program = "Assembling layer"
        if estado == 4:
            info_program = "Done!"
        if estado == 5:
            info_program = "Configuring"

        self.statusLabel.setText(info_program)
