"""
Thermal Temperature Reconstructor QGIS Plugin
Reconstructs temperature values from thermal RGB orthomosaics
"""

def classFactory(iface):
    """Load ThermalTemperatureReconstructor class from file thermal_temperature_reconstructor.
    
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .thermal_temperature_reconstructor import ThermalTemperatureReconstructor
    return ThermalTemperatureReconstructor(iface)




