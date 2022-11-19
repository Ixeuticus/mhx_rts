# Copyright (c) 2016-2021, Thomas Larsson
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies,
# either expressed or implied, of the FreeBSD Project.


bl_info = {
    "name": "MHX Runtime System",
    "author": "Thomas Larsson",
    "version": (1,6,1),
    "blender": (2,93,0),
    "location": "UI > MHX",
    "description": "MHX runtime system",
    "warning": "",
    "wiki_url": "https://diffeomorphic.blogspot.com/p/mhx-runtime-system.html",
    "tracker_url": "https://bitbucket.org/Diffeomorphic/import_daz/issues?status=new&status=open",
    "category": "Rigging"}

def importModules():
    import os
    import importlib
    global theModules

    try:
        theModules
    except NameError:
        theModules = []

    if theModules:
        print("\nReloading MHX RTS")
        for mod in theModules:
            importlib.reload(mod)
    else:
        print("\nLoading MHX RTS")
        modnames = ["utils", "layers", "fkik",
                    "props", "animation", "panel"]
        anchor = os.path.basename(__file__[0:-12])
        theModules = []
        for modname in modnames:
            mod = importlib.import_module("." + modname, anchor)
            theModules.append(mod)

import bpy
importModules()


#----------------------------------------------------------
#   Register
#----------------------------------------------------------

classes = [
    utils.ErrorOperator,
    utils.MessageOperator,
]

def register():
    fkik.register()
    props.register()
    animation.register()
    panel.register()
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    panel.unregister()
    animation.unregister()
    props.unregister()
    fkik.unregister()
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

print("MHX RTS loaded")
