# Copyright (c) 2016-2021, Thomas Larsson
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
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

import bpy
from .utils import *
from .layers import *
from .buildnumber import BUILD

#------------------------------------------------------------------------
#    Mhx Layers Panel
#------------------------------------------------------------------------

class MHX_PT_Main(bpy.types.Panel):
    bl_label = "MHX (version 0.1.0.%04d)" % BUILD
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    #bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        rig = context.object

#------------------------------------------------------------------------
#    Mhx Layers Panel
#------------------------------------------------------------------------

class MhxPanel(bpy.types.Panel):
    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and (ob.DazRig == "mhx" or ob.MhxRig == True))

    def needsMhxUpdate(self, rig):
        if rig is None:
            return True
        if "MhaGaze_L" in rig.keys():
            self.layout.operator("mhx.update_mhx")
            return True
        return False


class MHX_PT_Layers(MhxPanel):
    bl_label = "Layers"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        rig = context.object
        if self.needsMhxUpdate(rig):
            return

        self.layout.operator("mhx.enable_all_layers")
        self.layout.operator("mhx.disable_all_layers")
        for (left,right) in MhxLayers:
            row = self.layout.row()
            if type(left) == str:
                row.label(text=left)
                row.label(text=right)
            else:
                for (n, name, prop) in [left,right]:
                    row.prop(rig.data, "layers", index=n, toggle=True, text=name)

#------------------------------------------------------------------------
#    Mhx Properties Panel
#------------------------------------------------------------------------

class MHX_PT_Properties(MhxPanel):
    bl_label = "Properties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        rig = context.object
        if self.needsMhxUpdate(rig):
            return

        amt = rig.data
        self.layout.separator()
        self.layout.prop(amt, propRef("MhaGazeFollowsHead"), text="Gaze Follows Head")
        row = self.layout.row()
        row.label(text = "Left")
        row.label(text = "Right")
        props = [key for key in amt.keys() if key[0:3] == "Mha" and key[-1] in ["L", "R"]]
        props.sort()
        while props:
            left,right = props[0:2]
            props = props[2:]
            row = self.layout.row()
            row.prop(amt, propRef(left), text=left[3:-2])
            row.prop(amt, propRef(right), text=right[3:-2])

#------------------------------------------------------------------------
#    Mhx FK/IK switch panel
#------------------------------------------------------------------------

class MHX_PT_FKIK(MhxPanel):
    bl_label = "FK/IK Switch"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        rig = context.object
        scn = context.scene
        if self.needsMhxUpdate(rig):
            return

        amt = rig.data
        row = self.layout.row()
        row.label(text = "")
        row.label(text = "Left")
        row.label(text = "Right")

        self.layout.label(text = "FK/IK switch")
        row = self.layout.row()
        row.label(text = "Arm")
        self.toggleFKIK(row, amt["MhaArmIk_L"], "mhx.toggle_left_arm")
        self.toggleFKIK(row, amt["MhaArmIk_R"], "mhx.toggle_right_arm")
        row = self.layout.row()
        row.label(text = "Leg")
        self.toggleFKIK(row, amt["MhaLegIk_L"], "mhx.toggle_left_leg")
        self.toggleFKIK(row, amt["MhaLegIk_R"], "mhx.toggle_right_leg")

        self.layout.label(text = "IK Influence")
        row = self.layout.row()
        row.label(text = "Arm")
        row.prop(amt, propRef("MhaArmIk_L"), text="")
        row.prop(amt, propRef("MhaArmIk_R"), text="")
        row = self.layout.row()
        row.label(text = "Leg")
        row.prop(amt, propRef("MhaLegIk_L"), text="")
        row.prop(amt, propRef("MhaLegIk_R"), text="")

        self.layout.separator()
        self.layout.label(text = "Snap Arm Bones")
        row = self.layout.row()
        row.label(text = "FK Arm")
        row.operator("mhx.snap_fk_left_arm")
        row.operator("mhx.snap_fk_right_arm")
        row = self.layout.row()
        row.label(text = "IK Arm")
        row.operator("mhx.snap_ik_left_arm")
        row.operator("mhx.snap_ik_right_arm")

        self.layout.label(text = "Snap Leg Bones")
        row = self.layout.row()
        row.label(text = "FK Leg")
        row.operator("mhx.snap_fk_left_leg")
        row.operator("mhx.snap_fk_right_leg")
        row = self.layout.row()
        row.label(text = "IK Leg")
        row.operator("mhx.snap_ik_left_leg")
        row.operator("mhx.snap_ik_right_leg")
        self.layout.prop(scn, "MhxUseSnapRotation")

        self.layout.separator()
        icon = 'CHECKBOX_HLT' if amt.MhaLimitsOn else 'CHECKBOX_DEHLT'
        self.layout.operator("mhx.toggle_limits", icon=icon, emboss=False)
        icon = 'CHECKBOX_HLT' if amt.MhaHintsOn else 'CHECKBOX_DEHLT'
        self.layout.operator("mhx.toggle_hints", icon=icon, emboss=False)


    def toggleFKIK(self, row, value, op):
        if value > 0.5:
            row.operator(op, text="IK")
        else:
            row.operator(op, text="FK")

#------------------------------------------------------------------------
#    Mhx Animation Panel
#------------------------------------------------------------------------

class MHX_PT_Animation(MhxPanel):
    bl_label = "Animation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        rig = context.object
        if self.needsMhxUpdate(rig):
            return
        self.layout.operator("mhx.remove_frame_zero")
        self.layout.operator("mhx.remove_unused_fcurves")
        self.layout.operator("mhx.clear_animation")
        self.layout.operator("mhx.set_constraints")
        self.layout.operator("mhx.enforce_constraints")
        self.layout.separator()
        self.layout.operator("mhx.limbs_bend_positive")
        self.layout.operator("mhx.shift_animation")
        self.layout.operator("mhx.floor_fk_feet")
        self.layout.separator()
        self.layout.operator("mhx.transfer_to_ik")
        self.layout.operator("mhx.transfer_to_fk")
        self.layout.operator("mhx.floor_ik_feet")

#-------------------------------------------------------------
#   Initialize
#-------------------------------------------------------------

classes = [
    MHX_PT_Main,
    MHX_PT_Layers,
    MHX_PT_Properties,
    MHX_PT_FKIK,
    MHX_PT_Animation,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)