#  MHX Runtime System
#  Copyright (c) 2016-2025, Thomas Larsson
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
    "version": (4,4,0),
    "blender": (4,4,0),
    "location": "UI > MHX",
    "description": "Runtime system for MHX rig (DAZ Importer)",
    "warning": "",
    "doc_url": "https://bitbucket.org/Diffeomorphic/mhx_rts/wiki/Home",
    "tracker_url": "https://bitbucket.org/Diffeomorphic/import_daz/issues?status=new&status=open",
    "category": "Animation"}

Modules = ["utils", "layers", "fkik", "props", "animation", "mhx_update", "panel"]

if "bpy" in locals():
    print("Reloading MHX RTS v %d.%d.%d" % bl_info["version"])
    import imp
    for modname in Modules:
        exec("imp.reload(%s)" % modname)
else:
    print("Loading MHX RTS v %d.%d.%d" % bl_info["version"])
    import bpy
    for modname in Modules:
        exec("from . import %s" % modname)

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
    mhx_update.register()
    panel.register()
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    panel.unregister()
    mhx_update.unregister()
    animation.unregister()
    props.unregister()
    fkik.unregister()
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

print("MHX RTS loaded")
