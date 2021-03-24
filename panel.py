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

class MhxPanel(bpy.types.Panel):
    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and (ob.MhxRig == "mhx" or ob.MhxRig == True))

    def needsMhxUpdate(self, rig):
        if rig is None:
            return True
        if "MhaGaze_L" in rig.keys():
            self.layout.operator("mhx.update_mhx")
            return True
        return False


MhxLayers = [
    ((L_MAIN,       'Root', 'MhxRoot'),
     (L_SPINE ,     'Spine', 'MhxFKSpine')),
    ((L_HEAD,       'Head', 'MhxHead'),
     (L_FACE,       'Face', 'MhxFace')),
    ((L_TWEAK,      'Tweak', 'MhxTweak'),
     (L_CUSTOM,     'Custom', 'MhxCustom')),
    ('Left', 'Right'),
    ((L_LARMIK,     'IK Arm', 'MhxIKArm'),
     (L_RARMIK,     'IK Arm', 'MhxIKArm')),
    ((L_LARMFK,     'FK Arm', 'MhxFKArm'),
     (L_RARMFK,     'FK Arm', 'MhxFKArm')),
    ((L_LLEGIK,     'IK Leg', 'MhxIKLeg'),
     (L_RLEGIK,     'IK Leg', 'MhxIKLeg')),
    ((L_LLEGFK,     'FK Leg', 'MhxFKLeg'),
     (L_RLEGFK,     'FK Leg', 'MhxFKLeg')),
    ((L_LEXTRA,     'Extra', 'MhxExtra'),
     (L_REXTRA,     'Extra', 'MhxExtra')),
    ((L_LHAND,      'Hand', 'MhxHand'),
     (L_RHAND,      'Hand', 'MhxHand')),
    ((L_LFINGER,    'Fingers', 'MhxFingers'),
     (L_RFINGER,    'Fingers', 'MhxFingers')),
    ((L_LTOE,       'Toes', 'MhxToe'),
     (L_RTOE,       'Toes', 'MhxToe')),
]


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
        self.toggle(row, amt, "MhaArmIk_L", " 3", " 2")
        self.toggle(row, amt, "MhaArmIk_R", " 19", " 18")
        row = self.layout.row()
        row.label(text = "Leg")
        self.toggle(row, amt, "MhaLegIk_L", " 5", " 4")
        self.toggle(row, amt, "MhaLegIk_R", " 21", " 20")

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

        self.layout.separator()
        icon = 'CHECKBOX_HLT' if amt["MhaHintsOn"] else 'CHECKBOX_DEHLT'
        self.layout.operator("mhx.toggle_hints", icon=icon, emboss=False)


    def toggle(self, row, amt, prop, fk, ik):
        if amt[prop] > 0.5:
            row.operator("mhx.toggle_fk_ik", text="IK").toggle = prop + " 0" + fk + ik
        else:
            row.operator("mhx.toggle_fk_ik", text="FK").toggle = prop + " 1" + ik + fk

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
        self.layout.operator("mhx.offset_toes")
        self.layout.operator("mhx.transfer_to_ik")
        self.layout.operator("mhx.transfer_to_fk")
        self.layout.operator("mhx.clear_pole_targets")
        self.layout.operator("mhx.clear_animation", text="Clear IK Animation").type = "IK"
        self.layout.operator("mhx.clear_animation", text="Clear FK Animation").type = "FK"

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

#-------------------------------------------------------------
#   Enable and disable layers
#-------------------------------------------------------------

class MHX_OT_EnableAllLayers(MhxOperator, IsArmature):
    bl_idname = "mhx.enable_all_layers"
    bl_label = "Enable all layers"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        for (left,right) in MhxLayers:
            if type(left) != str:
                for (n, name, prop) in [left,right]:
                    rig.data.layers[n] = True


class MHX_OT_DisableAllLayers(MhxOperator, IsArmature):
    bl_idname = "mhx.disable_all_layers"
    bl_label = "Disable all layers"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        layers = 32*[False]
        pb = context.active_pose_bone
        if pb:
            for n in range(32):
                if pb.bone.layers[n]:
                    layers[n] = True
                    break
        else:
            layers[0] = True
        if rig:
            rig.data.layers = layers

#-------------------------------------------------------------
#   Initialize
#-------------------------------------------------------------

classes = [
    MHX_OT_EnableAllLayers,
    MHX_OT_DisableAllLayers,

    MHX_PT_Layers,
    MHX_PT_FKIK,
    MHX_PT_Animation,
    MHX_PT_Properties,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)