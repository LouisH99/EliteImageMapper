Elite Image Mapper - Windows EXE Build
======================================

Version
-------
This build kit is prepared for Elite Image Mapper 0.9.2.

License
-------
This project is released under the MIT License.
See LICENSE.txt for the full license text.

This folder is a build kit for creating a portable Windows version of Elite Image Mapper.
The app includes the GUI, About dialog, version information and optional image conversion.

What you need on the BUILD PC
-----------------------------
- Windows 10 or 11
- 64-bit Python for Windows
- Internet access for the first build (to install PyInstaller and Pillow)

How to build the EXE
--------------------
1. Put all files from this folder into one folder.
2. Double-click Build_EXE.bat
3. Wait until the build finishes.
4. The finished app folder will be created directly here:
   EliteImageMapper

What end users need
-------------------
Nothing extra. End users only need the finished folder:
  EliteImageMapper

Important notes
---------------
- The EXE build must be done on Windows.
- End users do NOT need Python.
- The app starts directly in GUI mode.
- The app can be started by double-clicking EliteImageMapper.exe.
- The output folder can be changed inside the GUI.
- README.md contains the general project and usage documentation.

Typical files after a successful build
--------------------------------------
- EliteImageMapper.exe
- README.txt
- README.md
- LICENSE.txt
- output\
- journals\
