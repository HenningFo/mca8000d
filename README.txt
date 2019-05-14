MCA8000D
========

Library to control a AMPTEK MCA8000d device.

mca/mca8000d.py
===============
This is the utility library. Everything you need to
communicate to a mca8000d device is in there.
It requires the python-usb library.
There is a demo() which is executed if mca8000d.py
is executed directly.

etc/mca8000d.rules
==================
udev rules for linux. Copy this to
/etc/udev/rules.d
You have to reload the rules after you copied the file
to have any effect. You also could restart the computer,
after reboot the rules will take effect too.
This will allow any user access to the mca8000d device.


mca/mca.py
==========
Simple UI program based on wxPython.
It requires wxPython and matplotlib and numpy for
displaying the spectrum.

