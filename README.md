RoadEmissionCalculator
=======================

[![License](https://img.shields.io/badge/license-BSD-brightgreen.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.5-blue.svg)](https://github.com/NPRA/RoadEmissionCalculator)
[![GitHub release](https://img.shields.io/github/release/NPRA/RoadEmissionCalculator.svg)](https://github.com/NPRA/RoadEmissionCalculator/releases/)
[![GitHub Ïssues](https://img.shields.io/github/issues-raw/NPRA/RoadEmissionCalculator/good-first-issue.svg)](https://github.com/NPRA/RoadEmissionCalculator/issues/)


This python plugin calculate emissions for selected roads. The plugin using external library "EmissionCalculatorLib". This python library uses formulas and factors from EU to calculate the emission(s) from personal cars, busses to trailers of various sizes give a start and stop point.


Download/Install
----------------

For using the plugin you should download RoadEmissionCalculator plugin from the "Manage and Install Plugins" option in the QGIS3 application. 

If you want to make changes to the code and install a "local" version you can either do a manually deployment or create a deployment ZIP file 
from your command line. You need to install the [pb_tool](https://pypi.python.org/pypi/pb_tool/). This is a "plugin build tool" for QGIS development.


#### Manually deployment

After installing the tool you need to stand in the root of the "RoadEmissionCalculator" folder (where 'metadata.txt' is located). Then type:
```
$ pb_tool deploy
```

pb_tool will then compile the UI and resource files, build docs and deploy the code to your QGIS3 installation.


#### Create deployment package (zip file)

You need to stand in the root of the "RoadEmissionCalculator" folder (where 'metadata.txt' is located). Then type:
```
$ pb_tool zip
```

A new file named 'RoadEmissionCalculator.zip' is now created in your current working directory. You can install this
plugin in QGIS3 inside the "Manage and Install Plugins" option. You should see an "Install from ZIP" option on the
left side of the "Manage and Install Plugins". Simply point it to your newly created ZIP file and install the plugin.

You should be good to go!


Have fun and play hard!


 
Description
-----------
The plugin has been build with [Plugin Builder](http://g-sherman.github.io/Qgis-Plugin-Builder/) which created all the necessary files and the boilerplate code for a plugin.

Plugin using external libraries:
+ EmissionCalculatorLib, fork on GitHub:[https://github.com/NPRA/EmissionCalculatorLib](https://github.com/NPRA/EmissionCalculatorLib)
+ Lat Lon Tools Plugin, fork on GitHub: [https://github.com/NationalSecurityAgency/qgis-latlontools-plugin](https://github.com/NationalSecurityAgency/qgis-latlontools-plugin/)
