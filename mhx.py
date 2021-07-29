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
from bpy.props import EnumProperty
from .utils import *
from .layers import *

# ---------------------------------------------------------------------
#   Convert MHX actions from legacy to modern
# ---------------------------------------------------------------------

class MHX_OT_ConvertMhxActions(MhxOperator):
    bl_idname = "mhx.convert_mhx_actions"
    bl_label = "Convert MHX Actions"
    bl_description = "Convert actions between legacy MHX (root/hips) and modern MHX (hip/pelvis)"
    bl_options = {'UNDO'}

    direction : EnumProperty(
        items = [
            ('MODERN', "Legacy => Modern", "Convert from legacy MHX (root/hips) to modern MHX (hip/pelvis)"),
            ('LEGACY', "Modern => Legacy", "Convert from modern MHX (hip/pelvis) to legacy MHX (root/hips)"),
        ],
        name = "Direction",
        default = 'MODERN'
    )

    def draw(self, context):
        self.layout.prop(self, "direction")


    def run(self, context):
        if self.direction == 'MODERN':
            replace = {
                '"root"' : '"hip"',
                '"hips"' : '"pelvis"',
            }
        else:
            replace = {
                '"hip"' : '"root"',
                '"pelvis"' : '"hips"',
            }
        for item in self.getSelectedItems():
            act = bpy.data.actions[item.name]
            for fcu in act.fcurves:
                for old,new in replace.items():
                    if old in fcu.data_path:
                        fcu.data_path = fcu.data_path.replace(old, new)


    def invoke(self, context, event):
        self.selection.clear()
        for act in bpy.data.actions:
            item = self.selection.add()
            item.name = act.name
            item.text = act.name
            item.select = False
        return self.invokeDialog(context)

#-------------------------------------------------------------
#   Enable and disable layers
#-------------------------------------------------------------

class MHX_OT_EnableAllLayers(MhxOperator):
    bl_idname = "mhx.enable_all_layers"
    bl_label = "Enable all layers"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        for (left,right) in MhxLayers:
            if type(left) != str:
                for (n, name, prop) in [left,right]:
                    rig.data.layers[n] = True


class MHX_OT_DisableAllLayers(MhxOperator):
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
#   Update MHX rig for armature properties
#-------------------------------------------------------------

def getMhxProps(amt):
    floats = ["MhaGazeFollowsHead"]
    bools = []
    for prop in ["MhaArmIk", "MhaGaze", "MhaLegIk"]:
        floats.append(prop+"_L")
        floats.append(prop+"_R")
    for prop in ["MhaArmHinge", "MhaFingerControl", "MhaLegHinge", "MhaLegIkToAnkle"]:
        bools.append(prop+"_L")
        bools.append(prop+"_R")
    return floats, bools


def setPropMinMax(rna, prop, min, max):
    rna_ui = rna.get('_RNA_UI')
    if rna_ui is None:
        rna_ui = rna['_RNA_UI'] = {}
    struct = { "min": min, "max": max, "soft_min": min, "soft_max": max}
    rna_ui[prop] = struct


class MHX_OT_UpdateMhx(MhxOperator):
    bl_idname = "mhx.update_mhx"
    bl_label = "Update MHX"
    bl_description = "Update MHX rig for driving armature properties"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        initMhxProps()
        floats,bools = getMhxProps(rig)
        for prop in floats+bools:
            if prop in rig.keys():
                del rig[prop]
        for prop in bools:
            rig.data[prop] = False
        for prop in floats:
            rig.data[prop] = 1.0
            setPropMinMax(rig, prop, 0.0, 1.0)
        self.updateDrivers(rig)

    def updateDrivers(self, rig):
        if rig.animation_data:
            for fcu in rig.animation_data.drivers:
                for var in fcu.driver.variables:
                    for trg in var.targets:
                        if trg.data_path[0:5] == '["Mha':
                            trg.id_type = 'ARMATURE'
                            trg.id = rig.data
                        elif trg.data_path == propRef("MhxGazeFollowsHead"):
                            trg.id_type = 'ARMATURE'
                            trg.id = rig.data
                            trg.data_path = propRef("MhaGazeFollowsHead")


def initMhxProps():
    # Gaze
    bpy.types.Armature.MhaGazeFollowsHead = FloatPropOVR(0.0, min=0.0, max=1.0,
        name = "Gaze Follows Head",
        description = "The gaze bone follows the head bone rotations")
    bpy.types.Armature.MhaGaze_L = FloatPropOVR(0.0, min=0.0, max=1.0,
        name = "Left Gaze",
        description = "Left eye tracking the left gaze bone amount")
    bpy.types.Armature.MhaGaze_R = FloatPropOVR(0.0, min=0.0, max=1.0,
        name = "Right Gaze",
        description = "Right eye tracking the right gaze bone amount")

    # Hinge
    bpy.types.Armature.MhaArmHinge_L = BoolPropOVR(False,
        name = "Left Arm Hinge",
        description = "Left arm decoupled from the spine rotation")
    bpy.types.Armature.MhaArmHinge_R = BoolPropOVR(False,
        name = "Right Arm Hinge",
        description = "Right arm decoupled from the spine rotation")
    bpy.types.Armature.MhaLegHinge_L = BoolPropOVR(False,
        name = "Left Leg Hinge",
        description = "Left leg decoupled from the pelvis rotation")
    bpy.types.Armature.MhaLegHinge_R = BoolPropOVR(False,
        name = "Right Leg Hinge",
        description = "Right leg decoupled from the pelvis rotation")

    # Hands and fingers
    bpy.types.Armature.MhaForearmsFollow_L = BoolPropOVR(True)
    bpy.types.Armature.MhaForearmsFollow_R = BoolPropOVR(True)
    bpy.types.Armature.MhaFingerControl_L = BoolPropOVR(False,
        name = "Left Fingers",
        description = "Left finger links controlled by the long finger bones")
    bpy.types.Armature.MhaFingerControl_R = BoolPropOVR(False,
        name = "Right Fingers",
        description = "Right finger links controlled by the long finger bones")

    # IK
    bpy.types.Armature.MhaLimitsOn = BoolPropOVR(True)

    bpy.types.Armature.MhaLegIkToAnkle_L = BoolPropOVR(False,
        name = "Left Ankle IK",
        description = "Use ankle bone as IK target for left leg")
    bpy.types.Armature.MhaLegIkToAnkle_R = BoolPropOVR(False,
        name = "Right Ankle IK",
        description = "Use ankle bone as IK target for right leg")

    bpy.types.Armature.MhaArmIk_L = FloatPropOVR(0.0, precision=3, min=0.0, max=1.0)
    bpy.types.Armature.MhaLegIk_L = FloatPropOVR(0.0, precision=3, min=0.0, max=1.0)
    bpy.types.Armature.MhaArmIk_R = FloatPropOVR(0.0, precision=3, min=0.0, max=1.0)
    bpy.types.Armature.MhaLegIk_R = FloatPropOVR(0.0, precision=3, min=0.0, max=1.0)

    # Stretchiness
    bpy.types.Armature.MhaArmStretch_L = BoolPropOVR(True)
    bpy.types.Armature.MhaLegStretch_L = BoolPropOVR(True)
    bpy.types.Armature.MhaToeTarsal_L = BoolPropOVR(False)
    bpy.types.Armature.MhaArmStretch_R = BoolPropOVR(True)
    bpy.types.Armature.MhaLegStretch_R = BoolPropOVR(True)
    bpy.types.Armature.MhaToeTarsal_R = BoolPropOVR(False)


classes = [
    MHX_OT_EnableAllLayers,
    MHX_OT_DisableAllLayers,
    MHX_OT_ConvertMhxActions,
    MHX_OT_UpdateMhx,
]

def register():
    bpy.types.Object.MhxLegacy = bpy.props.BoolProperty(default = True)
    bpy.types.Object.MhxRig = bpy.props.BoolProperty(default = False)
    bpy.types.Object.DazRig = bpy.props.StringProperty(default = "")
    initMhxProps()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
