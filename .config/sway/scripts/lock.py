#!/bin/python3

import os
import subprocess
import sys
import tempfile

import i3ipc.i3ipc
i3 = i3ipc.Connection()
outputs = [x['name'] for x in i3.get_outputs()]
images = [tempfile.mktemp() for _ in outputs]
lockcmd = ["swaylock"]

# take the screenshots
for output,image in zip(outputs, images):
    subprocess.call(["grim", "-o", output, image])
    subprocess.call(["convert", image, "-scale", "10%", "-scale", "1000%", image])
    lockcmd.extend(["-F", "-c", "333333", "-s", "fill",  "-i", output+":"+image])

# lock the screen
lockcmd.extend(sys.argv[1:])
subprocess.call(lockcmd)

# cleanup
for img in images:
    os.remove(img)
