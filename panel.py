# Copyright (c) 2016-2023, Thomas Larsson
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

F_TONGUE = 1
F_FINGER = 2

#------------------------------------------------------------------------
#    Mhx Layers Panel
#------------------------------------------------------------------------

class MHX_PT_Main(bpy.types.Panel):
    bl_label = "MHX (version 1.7.0.%04d)" % BUILD
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
        if "MhaGaze_L" in rig.data.keys():
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

        self.layout.label(text = "Gaze")
        self.layout.prop(rig, "MhaGazeFollowsHead")
        row = self.layout.row()
        row.prop(rig, "MhaGaze_L")
        row.prop(rig, "MhaGaze_R")
        if rig.data.MhaFeatures & F_TONGUE:
            self.layout.prop(rig, "MhaTongueIk")

        self.layout.separator()
        self.layout.label(text = "Hinge")
        row = self.layout.row()
        row.prop(rig, "MhaArmHinge_L")
        row.prop(rig, "MhaArmHinge_R")
        row = self.layout.row()
        row.prop(rig, "MhaLegHinge_L")
        row.prop(rig, "MhaLegHinge_R")

        self.layout.separator()
        self.layout.label(text = "Hands And Fingers")
        row = self.layout.row()
        row.prop(rig, "MhaForearmFollow_L")
        row.prop(rig, "MhaForearmFollow_R")
        row = self.layout.row()
        row.prop(rig, "MhaFingerControl_L")
        row.prop(rig, "MhaFingerControl_R")
        if rig.data.MhaFeatures & F_FINGER:
            row = self.layout.row()
            row.prop(rig, "MhaFingerIk_L")
            row.prop(rig, "MhaFingerIk_R")

        self.layout.separator()
        self.layout.label(text = "IK And Limits")
        row = self.layout.row()
        self.updateFunction(row, rig, "MhaLimitsOn", "mhx.toggle_limits")
        row.operator("mhx.enforce_limits")
        row = self.layout.row()
        row.prop(rig, "MhaArmIk_L")
        row.prop(rig, "MhaArmIk_R")
        row = self.layout.row()
        row.prop(rig, "MhaLegIk_L")
        row.prop(rig, "MhaLegIk_R")
        if "foot.2.L" in rig.pose.bones.keys():
            row = self.layout.row()
            row.prop(rig, "MhaLegIkToAnkle_L")
            row.prop(rig, "MhaLegIkToAnkle_R")

        if rig.MhxChildOfConstraints:
            self.layout.separator()
            self.layout.label(text = "Pole Target Parents")
            row = self.layout.row()
            row.prop(rig, "MhaElbowHand_L")
            row.prop(rig, "MhaElbowHand_R")
            row = self.layout.row()
            row.prop(rig, "MhaElbowShoulder_L")
            row.prop(rig, "MhaElbowShoulder_R")
            row = self.layout.row()
            row.prop(rig, "MhaKneeFoot_L")
            row.prop(rig, "MhaKneeFoot_R")
            row = self.layout.row()
            row.prop(rig, "MhaKneeHip_L")
            row.prop(rig, "MhaKneeHip_R")
        else:
            self.layout.separator()
            self.layout.label(text = "Pole Target Parents")
            row = self.layout.row()
            row.prop(rig, "MhaElbowParent_L")
            row.prop(rig, "MhaElbowParent_R")
            row = self.layout.row()
            row.prop(rig, "MhaKneeParent_L")
            row.prop(rig, "MhaKneeParent_R")
            self.layout.operator("mhx.update_elbow_knee_parents")

        self.layout.separator()
        self.layout.label(text = "Stretchiness")
        row = self.layout.row()
        row.prop(rig, "MhaArmStretch_L")
        row.prop(rig, "MhaArmStretch_R")
        row = self.layout.row()
        row.prop(rig, "MhaLegStretch_L")
        row.prop(rig, "MhaLegStretch_R")

        self.layout.separator()
        self.layout.label(text = "Toes Tarsal Parents")
        row = self.layout.row()
        self.updateFunction(row, rig, "MhaToeTarsal_L", "mhx.toggle_left_toe_tarsal")
        self.updateFunction(row, rig, "MhaToeTarsal_R", "mhx.toggle_right_toe_tarsal")

        self.layout.separator()
        self.layout.operator("mhx.update_mhx")


    def updateFunction(self, layout, rig, prop, opname):
        icon = ('CHECKBOX_HLT' if getattr(rig, prop) else 'CHECKBOX_DEHLT')
        layout.operator(opname, icon=icon)


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

        row = self.layout.row()
        row.label(text = "")
        row.label(text = "Left")
        row.label(text = "Right")

        self.layout.label(text = "FK/IK switch")
        row = self.layout.row()
        row.label(text = "Arm")
        self.toggleFKIK(row, rig.MhaArmIk_L, "mhx.toggle_fkik_left_arm")
        self.toggleFKIK(row, rig.MhaArmIk_R, "mhx.toggle_fkik_right_arm")
        row = self.layout.row()
        row.label(text = "Leg")
        self.toggleFKIK(row, rig.MhaLegIk_L, "mhx.toggle_fkik_left_leg")
        self.toggleFKIK(row, rig.MhaLegIk_R, "mhx.toggle_fkik_right_leg")

        self.layout.label(text = "IK Influence")
        row = self.layout.row()
        row.label(text = "Arm")
        row.prop(rig, "MhaArmIk_L", text="")
        row.prop(rig, "MhaArmIk_R", text="")
        row = self.layout.row()
        row.label(text = "Leg")
        row.prop(rig, "MhaLegIk_L", text="")
        row.prop(rig, "MhaLegIk_R", text="")

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

        self.layout.separator()
        self.layout.operator("mhx.snap_fk_all")
        self.layout.operator("mhx.snap_ik_all")
        self.layout.prop(scn, "MhxUseSwitch")
        self.layout.prop(scn, "MhxUseSnapRotation")

        if rig.data.MhaFeatures & F_FINGER:
            self.layout.separator()
            self.layout.label(text = "Finger IK")
            self.layout.label(text = "IK Influence")
            row = self.layout.row()
            row.prop(rig, "MhaFingerIk_L", text="")
            row.prop(rig, "MhaFingerIk_R", text="")
            self.layout.label(text = "Snap Finger Bones")
            row = self.layout.row()
            row.label(text = "FK Fingers")
            row.operator("mhx.snap_fk_left_fingers")
            row.operator("mhx.snap_fk_right_fingers")
            row = self.layout.row()
            row.label(text = "IK Fingers")
            row.operator("mhx.snap_ik_left_fingers")
            row.operator("mhx.snap_ik_right_fingers")

        if rig.data.MhaFeatures & F_TONGUE:
            self.layout.separator()
            self.layout.label(text = "Tongue IK")
            self.layout.label(text = "IK Influence")
            self.layout.prop(rig, "MhaTongueIk", text="")
            self.layout.label(text = "Snap Tongue Bones")
            self.layout.operator("mhx.snap_fk_tongue")
            self.layout.operator("mhx.snap_ik_tongue")

        self.layout.separator()
        self.layout.label(text = "Spine, Neck, Head")
        self.layout.operator("mhx.snap_spine")
        self.layout.operator("mhx.snap_neck_head")


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
        scn = context.scene
        if self.needsMhxUpdate(rig):
            return
        self.layout.operator("mhx.remove_frame_zero")
        self.layout.operator("mhx.remove_unused_fcurves")
        self.layout.operator("mhx.clear_animation")
        self.layout.operator("mhx.set_constraints")
        self.layout.operator("mhx.enforce_all_limits")
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