# Copyright (c) 2016-2024, Thomas Larsson
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
    bl_label = "MHX (version 1.7.4.%04d)" % BUILD
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        rig = context.object
        if rig is None:
            pass
        elif rig.DazRig == "mhx":
            self.layout.operator("mhx.bake_mhx")
        elif rig.DazRig == "baked-mhx":
            self.layout.operator("mhx.unbake_mhx")

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
        if bpy.app.version >= (4,0,0) and "Layer 1" in rig.data.collections.keys():
            self.layout.operator("mhx.update_mhx_blender4")
            return True
        if not rig.data.MhaFeatures & F_IDPROPS:
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

        def showCollection(layout, cname):
            coll = rig.data.collections.get(cname)
            if coll:
                layout.prop(coll, "is_visible", toggle=True, text=cname)
            else:
                layout.label(text = cname)

        self.layout.operator("mhx.enable_all_layers")
        self.layout.operator("mhx.disable_all_layers")
        layers = [
            (L_MAIN, L_SPINE),
            (L_HEAD, L_FACE),
            (L_CUSTOM, L_CUSTOM2),
            (L_TWEAK, L_SPINE2),
            ("Left", "Right"),
            (L_LARMFK, L_RARMFK),
            (L_LARMIK, L_RARMIK),
            (L_LARM2IK, L_RARM2IK),
            (L_LLEGFK, L_RLEGFK),
            (L_LLEGIK, L_RLEGIK),
            (L_LLEG2IK, L_RLEG2IK),
            (L_LHAND, L_RHAND),
            (L_LFINGER, L_RFINGER),
            (L_LTOE, L_RTOE)]
        for (left,right) in layers:
            row = self.layout.row()
            if bpy.app.version < (4,0,0):
                if type(left) == str:
                    row.label(text=left)
                    row.label(text=right)
                else:
                    row.prop(rig.data, "layers", index=left, toggle=True, text=MhxLayers[left])
                    row.prop(rig.data, "layers", index=right, toggle=True, text=MhxLayers[right])
            else:
                showCollection(row, left)
                showCollection(row, right)

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
        row = self.layout.row()
        op = row.operator("mhx.unhinge", text="Unhinge Left Arm")
        op.limb = "Arm"
        op.suffix = "L"
        op = row.operator("mhx.unhinge", text="Unhinge Right Arm")
        op.limb = "Arm"
        op.suffix = "R"
        row = self.layout.row()
        op = row.operator("mhx.unhinge", text="Unhinge Left Leg")
        op.limb = "Leg"
        op.suffix = "L"
        op = row.operator("mhx.unhinge", text="Unhinge Right Leg")
        op.limb = "Leg"
        op.suffix = "R"

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
        self.layout.prop(rig, "MhaSpineIk")
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

class MHX_PT_FKIKArmsLegs(MhxPanel):
    bl_label = "FK/IK Arms Legs"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        rig = context.object
        scn = context.scene
        if self.needsMhxUpdate(rig):
            return

        box = self.layout.box()
        box.label(text = "Arms")
        row = box.row()
        row.label(text = "Left")
        row.label(text = "Right")
        row = box.row()
        toggleFKIK(row, rig.MhaArmIk_L, "mhx.toggle_fkik_left_arm")
        toggleFKIK(row, rig.MhaArmIk_R, "mhx.toggle_fkik_right_arm")
        row = box.row()
        row.prop(rig, "MhaArmIk_L")
        row.prop(rig, "MhaArmIk_R")
        row = box.row()
        row.operator("mhx.snap_fk_left_arm")
        row.operator("mhx.snap_fk_right_arm")
        row = box.row()
        row.operator("mhx.snap_ik_left_arm")
        row.operator("mhx.snap_ik_right_arm")

        box = self.layout.box()
        box.label(text = "Legs")
        row = box.row()
        row.label(text = "Left")
        row.label(text = "Right")
        row = box.row()
        toggleFKIK(row, rig.MhaLegIk_L, "mhx.toggle_fkik_left_leg")
        toggleFKIK(row, rig.MhaLegIk_R, "mhx.toggle_fkik_right_leg")
        row = box.row()
        row.prop(rig, "MhaLegIk_L")
        row.prop(rig, "MhaLegIk_R")
        row = box.row()
        row.operator("mhx.snap_fk_left_leg")
        row.operator("mhx.snap_fk_right_leg")
        row = box.row()
        row.operator("mhx.snap_ik_left_leg")
        row.operator("mhx.snap_ik_right_leg")

        self.layout.separator()
        row = self.layout.row()
        row.operator("mhx.enforce_limits")
        row.operator("mhx.clear_ik_twist_bones")
        row = self.layout.row()
        row.operator("mhx.clear_fingers")
        row.operator("mhx.clear_feet")
        row = self.layout.row()
        row.operator("mhx.set_fk_all")
        row.operator("mhx.set_ik_all")
        row = self.layout.row()
        row.operator("mhx.snap_fk_all")
        row.operator("mhx.snap_ik_all")
        self.layout.prop(scn, "MhxUseSwitch")
        self.layout.prop(scn, "MhxUseSnapRotation")


def toggleFKIK(row, value, op):
    if value > 0.5:
        row.operator(op, text="IK")
    else:
        row.operator(op, text="FK")


class MHX_PT_FKIKFingers(MhxPanel):
    bl_label = "FK/IK Spine Fingers Tongue Shaft"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        rig = context.object
        scn = context.scene
        if self.needsMhxUpdate(rig):
            return

        box = self.layout.box()
        box.label(text = "Spine")
        row = box.row()
        row.prop(rig, "MhaSpineControl")
        row.prop(rig, "MhaNeckControl")
        if rig.data.MhaFeatures & F_SPINE:
            box.prop(rig, "MhaSpineIk")
            row = box.row()
            op = row.operator("mhx.snap_reverse", text="Snap FK")
            op.prop = "MhaSpineIk"
            op.value = 0.0
            op.bonename = "back"
            op.revname = "REV-ik_back"
            op.fk = op.ik = L_MAIN
            op = row.operator("mhx.snap_reverse", text="Snap IK")
            op.prop = "MhaSpineIk"
            op.value = 1.0
            op.bonename = "ik_back"
            op.revname = "REV-back"
            op.fk = op.ik = L_MAIN

        row = box.row()
        row.operator("mhx.snap_spine")

        box = self.layout.box()
        box.label(text = "Fingers")
        row = box.row()
        row.label(text = "Left")
        row.label(text = "Right")
        row = box.row()
        row.prop(rig, "MhaFingerControl_L")
        row.prop(rig, "MhaFingerControl_R")
        if rig.data.MhaFeatures & F_FINGER:
            row = box.row()
            row.prop(rig, "MhaFingerIk_L", text="IK Influence")
            row.prop(rig, "MhaFingerIk_R", text="IK Influence")
        row = box.row()
        for suffix in ["L", "R"]:
            op = row.operator("mhx.snap_fingers")
            op.suffix = suffix

        box = self.layout.box()
        box.label(text = "Tongue")
        box.prop(rig, "MhaTongueControl")
        if rig.data.MhaFeatures & F_TONGUE:
            box.prop(rig, "MhaTongueIk")
        box.operator("mhx.snap_tongue")

        box = self.layout.box()
        box.label(text = "Shaft")
        box.prop(rig, "MhaShaftControl")
        if rig.data.MhaFeatures & F_SHAFT:
            box.prop(rig, "MhaShaftIk")
        box.operator("mhx.snap_shaft")

        self.layout.operator("mhx.enforce_limits")

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
        self.layout.operator("mhx.remove_unused_fcurves")
        self.layout.operator("mhx.clear_animation")
        self.layout.operator("mhx.constrain_feet")
        self.layout.operator("mhx.enforce_all_limits")
        self.layout.separator()
        self.layout.operator("mhx.limbs_bend_positive")
        self.layout.operator("mhx.shift_animation")
        self.layout.operator("mhx.floor_fk_feet")
        self.layout.separator()
        self.layout.operator("mhx.transfer_to_ik")
        self.layout.operator("mhx.transfer_to_fk")
        self.layout.operator("mhx.transfer_to_links")
        self.layout.operator("mhx.floor_ik_feet")

#-------------------------------------------------------------
#   Initialize
#-------------------------------------------------------------

classes = [
    MHX_PT_Main,
    MHX_PT_Layers,
    MHX_PT_Properties,
    MHX_PT_FKIKArmsLegs,
    MHX_PT_FKIKFingers,
    MHX_PT_Animation,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)