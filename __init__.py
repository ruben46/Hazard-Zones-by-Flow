# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HazardZonesByFlow
                                 A QGIS plugin
 This Plugin is for the evaluation of hazard zones by torrent flow from pond/dam breach
                             -------------------
        begin                : 2017-06-12
        copyright            : (C) 2017 by Ruben Munoz Sanchez
        email                : ruben46@usal.es
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load HazardZonesByFlow class from file HazardZonesByFlow.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .Hazard_Zones import HazardZonesByFlow
    return HazardZonesByFlow(iface)
