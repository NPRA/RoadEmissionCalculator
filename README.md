RoadEmissionCalculator
=======================

[![License](https://img.shields.io/badge/license-BSD-brightgreen.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.5-blue.svg)](https://github.com/NPRA/RoadEmissionCalculator)
[![GitHub release](https://img.shields.io/github/release/Naereen/StrapDown.js.svg)](https://github.com/NPRA/RoadEmissionCalculator/releases/)
[![GitHub Ïssues](https://img.shields.io/github/issues-raw/NPRA/RoadEmissionCalculator/good-first-issue.svg)](https://github.com/NPRA/RoadEmissionCalculator/issues/)


This python plugin calculate emissions for selected roads. The plugin using external library "EmissionCalculatorLib". This python library uses formulas and factors from EU to calculate the emission(s) from personal cars, busses to trailers of various sizes give a start and stop point.


Download/Install
----------------

For using the plugin you should download RoadEmissionCalculator project to QGIS3 folder.

Windows
> %userprofile%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins

Linux
> $HOME/.local/share/QGIS/QGIS3/profiles/default/python/plugins

Mac
> $HOME/.local/share/QGIS/QGIS3/profiles/default/python/plugins

Open the QGIS. You will notice that there is a new icon in the toolbar and a new menu entry. Select it to lunch the plugin dialog.
 
Description
-----------
The plugin has been build with [Plugin Builder](http://g-sherman.github.io/Qgis-Plugin-Builder/) which created all the necessary files and the boilerplate code for a plugin.

Plugin using external libraries:
+ EmissionCalculatorLib, fork on GitHub:[https://github.com/NPRA/EmissionCalculatorLib](https://github.com/NPRA/EmissionCalculatorLib)
+ Lat Lon Tools Plugin, fork on GitHub: [https://github.com/NationalSecurityAgency/qgis-latlontools-plugin](https://github.com/NationalSecurityAgency/qgis-latlontools-plugin/)
