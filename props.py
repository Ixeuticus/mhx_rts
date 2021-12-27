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
from bpy.props import EnumProperty, BoolProperty

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
#   Overridable properties
#-------------------------------------------------------------

if bpy.app.version < (2,90,0):
    def BoolPropOVR(default, name="", description="", update=None):
        return bpy.props.BoolProperty(
            name=name,
            default=default,
            description=description,
            update=update)

    def FloatPropOVR(default, name="", description="", precision=2, min=0, max=1, update=None):
        return bpy.props.FloatProperty(
            name=name,
            default=default,
            description=description,
            precision=precision,
            min=min, max=max,
            update=update)
else:
    def BoolPropOVR(default, name="", description="", update=None):
        return bpy.props.BoolProperty(
            name=name,
            default=default,
            description=description,
            update=update,
            options={'LIBRARY_EDITABLE'},
            override={'LIBRARY_OVERRIDABLE'})

    def FloatPropOVR(default, name="", description="", precision=2, min=0, max=1, update=None):
        return bpy.props.FloatProperty(
            name=name,
            default=default,
            description=description,
            precision=precision,
            min=min, max=max,
            update=update,
            options={'LIBRARY_EDITABLE'},
            override={'LIBRARY_OVERRIDABLE'})


def initMhxProps():
    from . import fkik

    bpy.types.Object.MhxRig = BoolProperty(default = False)

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
    bpy.types.Armature.MhaForearmFollow_L = BoolPropOVR(True,
        name = "Left Forearm Follows Hand",
        description = "Control left forearm twist with left hand twist.\nIt may be necessary to turn this off for correct FK->IK snapping.",
        update = fkik.setForearmFollowLeft)
    bpy.types.Armature.MhaForearmFollow_R = BoolPropOVR(True,
        name = "Right Forearm Follows Hand",
        description = "Control right forearm twist with right hand twist.\nIt may be necessary to turn this off for correct FK->IK snapping.",
        update = fkik.setForearmFollowRight)

    bpy.types.Armature.MhaFingerControl_L = BoolPropOVR(False,
        name = "Left Long Fingers",
        description = "Left finger links controlled by the long finger bones")
    bpy.types.Armature.MhaFingerControl_R = BoolPropOVR(False,
        name = "Right Long Fingers",
        description = "Right finger links controlled by the long finger bones")

    bpy.types.Armature.MhaFingerIk_L = BoolPropOVR(False,
        name = "Left Finger IK",
        description = "Left finger links controlled by IK")
    bpy.types.Armature.MhaFingerIk_R = BoolPropOVR(False,
        name = "Right Finger IK",
        description = "Right finger links controlled by IK")

    # Legs
    bpy.types.Armature.MhaDazShin_L = BoolPropOVR(False,
        name = "Left DAZ Shin",
        description = "Left shin as in DAZ Studio")
    bpy.types.Armature.MhaDazShin_R = BoolPropOVR(False,
        name = "Right DAZ Shin",
        description = "Right shin as in DAZ Studio")

    # IK
    bpy.types.Armature.MhaLimitsOn = BoolPropOVR(True,
        name = "Rotation Limits",
        description = "Toggle FK and IK rotation limits.\nIt may be necessary to turn these off for correct FK->IK snapping.",
        update = fkik.toggleFkIkLimits)

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

    #
    elbowEnums = [
        ('HAND', "Hand", "Parent elbow pole target to IK hand"),
        ('SHOULDER', "Shoulder", "Parent elbow pole target to shoulder"),
        ('MASTER', "Master", "Parent elbow pole target to the master bone")]
    bpy.types.Armature.MhaElbowParent_L = EnumProperty(
        items = elbowEnums,
        name = "Left Elbow Parent",
        description = "Parent of left elbow pole target")
    bpy.types.Armature.MhaElbowParent_R = EnumProperty(
        items = elbowEnums,
        name = "Right Elbow Parent",
        description = "Parent of right elbow pole target")

    kneeEnums = [
        ('FOOT', "Foot", "Parent knee pole target to IK foot"),
        ('HIP', "Hip", "Parent knee pole target to hip"),
        ('MASTER', "Master", "Parent knee pole target to the master bone")]
    bpy.types.Armature.MhaKneeParent_L = EnumProperty(
        items = kneeEnums,
        name = "Left Knee Parent",
        description = "Parent of left knee pole target")
    bpy.types.Armature.MhaKneeParent_R = EnumProperty(
        items = kneeEnums,
        name = "Right Knee Parent",
        description = "Parent of right knee pole target")

    # Stretchiness
    bpy.types.Armature.MhaArmStretch_L = BoolProperty(
        name = "Left Arm Stretch",
        description = "Toggle left arm stretchiness",
        default = True)

    bpy.types.Armature.MhaLegStretch_L = BoolProperty(
        name = "Left Leg Stretch",
        description = "Toggle left leg stretchiness",
        default = True)

    bpy.types.Armature.MhaArmStretch_R = BoolProperty(
        name = "Right Arm Stretch",
        description = "Toggle right arm stretchiness",
        default = True)

    bpy.types.Armature.MhaLegStretch_R = BoolProperty(
        name = "Right Leg Stretch",
        description = "Toggle right leg stretchiness",
        default = True)

    bpy.types.Armature.MhaToeTarsal_L = BoolProperty(
        name = "Left Toes Tarsal Parent",
        description = "Toggle left toes tarsal parent",
        default = False)

    bpy.types.Armature.MhaToeTarsal_R = BoolProperty(
        name = "Right Toes Tarsal Parent",
        description = "Toggle right toes tarsal parent",
        default = False)


classes = [
    MHX_OT_EnableAllLayers,
    MHX_OT_DisableAllLayers,
    MHX_OT_ConvertMhxActions,
]

def register():
    bpy.types.Object.MhxLegacy = bpy.props.BoolProperty(default = True)
    bpy.types.Object.MhxRig = bpy.props.BoolProperty(default = False)
    bpy.types.Object.DazRig = bpy.props.StringProperty(
        name = "Rig Type",
        default = "")
    initMhxProps()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
