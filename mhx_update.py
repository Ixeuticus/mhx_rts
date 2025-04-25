# SPDX-FileCopyrightText: 2016-2025, Thomas Larsson
#
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from mathutils import *
from .utils import *

#-------------------------------------------------------------
#   Update MHX
#-------------------------------------------------------------

class MHX_OT_UpdateMhx(MhxOperator):
    bl_idname = "mhx.update_mhx_animation"
    bl_label = "Update MHX Animation"
    bl_description = "Update MHX animation"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        if rig.animation_data and rig.animation_data.action:
            fcurves = getActionBag(rig.animation_data.action).fcurves
            for fcu in list(fcurves):
                if fcu.data_path.startswith("Mha"):
                    fcu.data_path = propRef(fcu.data_path)

#-------------------------------------------------------------
#   Register
#-------------------------------------------------------------

classes = [
    MHX_OT_UpdateMhx,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
