RoadEmissionCalculator
=======================

This python plugin calculate emissions for selected roads. The plugin using external library "EmissionCalculatorLib". This python library uses formulas and factors from EU to calculate the emission(s) from personal cars, busses to trailers of various sizes give a start and stop point.


Download/Install
----------------

For using the plugin you should download RoadEmissionCalculator project to .qgis folder.

Windows
> C:Users\username\.qgis2\python\plugins

Linux
> /Users/username/.qgis2/python/plugins

Mac
> /home/username/.qgis2/python/plugins

Open the QGIS. You will notice that there is a new icon in the toolbar and a new menu entry. Select it to lunch the plugin dialog.
 
Description
-----------
The plugin has been build with [Plugin Builder](http://g-sherman.github.io/Qgis-Plugin-Builder/) which created all the necessary files and the boilerplate code for a plugin.

Plugin using external libraries:
+ EmissionCalculatorLib, fork on GitHub:[https://github.com/NPRA/EmissionCalculatorLib](https://github.com/NPRA/EmissionCalculatorLib)
+ Lat Lon Tools Plugin, for on GitHub: [https://github.com/NationalSecurityAgency/qgis-latlontools-plugin/#readme](https://github.com/NationalSecurityAgency/qgis-latlontools-plugin/)
