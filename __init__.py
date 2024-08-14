#  MHX Runtime System
#  Copyright (c) 2016-2024, Thomas Larsson
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

bl_info = {
    "name": "MHX Runtime System",
    "author": "Thomas Larsson",
    "version": (4,2,1),
    "blender": (4,2,0),
    "location": "UI > MHX",
    "description": "MHX runtime system",
    "warning": "",
    "doc_url": "https://bitbucket.org/Diffeomorphic/mhx_rts/wiki/Home",
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
        print("\nReloading MHX RTS v %d.%d.%d" % bl_info["version"])
        for mod in theModules:
            importlib.reload(mod)
    else:
        print("\nLoading MHX RTS v %d.%d.%d" % bl_info["version"])
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
