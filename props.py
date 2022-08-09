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
#   Update MHX
#-------------------------------------------------------------

class MHX_OT_UpdateMhx(MhxOperator):
    bl_idname = "mhx.update_mhx"
    bl_label = "Update MHX"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        for key in list(rig.data.keys()):
            if key[0:3] == "Mha" and hasattr(rig, key):
                value = rig.data[key]
                if key.startswith("MhaElbowParent") and isinstance(value, int):
                    value = {0: 'HAND', 1: 'SHOULDER', 2: 'MASTER'}[value]
                elif key.startswith("MhaKneeParent") and isinstance(value, int):
                    value = {0: 'FOOT', 1: 'HIP', 2: 'MASTER'}[value]
                print("FIX", key, value)
                setattr(rig, key, value)
                del rig.data[key]

        if rig.animation_data:
            amt = rig.data
            for fcu in rig.animation_data.drivers:
                channel = fcu.data_path.rsplit(".")[-1]
                if channel in ["influence", "mute"]:
                    for var in list(fcu.driver.variables):
                        trg = var.targets[0]
                        if trg.id == amt and trg.data_path[0:5] == '["Mha':
                            prop = baseRef(trg.data_path)
                            if hasattr(rig, prop):
                                nvar = fcu.driver.variables.new()
                                varname = var.name
                                ntrg = nvar.targets[0]
                                ntrg.id_type == 'OBJECT'
                                ntrg.id = rig
                                ntrg.data_path = prop
                                fcu.driver.variables.remove(var)
                                nvar.name = varname

        from import_daz.mhx import addDriver, copyLocation
        for suffix in ["L", "R"]:
            for bname,prop in [
                ("shin", "MhaLegStretch"),
                ("shin.bend", "MhaLegStretch"),
                ("shin.twist", "MhaLegStretch"),
                ("forearm.bend", "MhaArmStretch"),
                ("forearm.twist", "MhaArmStretch"),
            ]:
                pb = rig.pose.bones.get("%s.%s" % (bname, suffix))
                prop2 = "%s_%s" % (prop, suffix)
                if pb:
                    cns = getConstraint(pb, 'STRETCH_TO')
                    if cns:
                        cns.driver_remove("influence")
                        addDriver(cns, "influence", rig, prop2, "x")
            for bname,prop in [
                ("foot", "MhaLegStretch"),
                ("foot.fk", "MhaLegStretch"),
                ("hand", "MhaArmStretch"),
                ("hand.fk", "MhaArmStretch"),
            ]:
                pb = rig.pose.bones["%s.%s" % (bname, suffix)]
                prop2 = "%s_%s" % (prop, suffix)
                if not getConstraint(pb, 'COPY_LOCATION'):
                    cns = copyLocation(pb, pb.parent, rig, prop2, "1-x")
                    cns.head_tail = 1.0


def getConstraint(pb, ctype):
    for cns in pb.constraints:
        if cns.type == ctype:
            return cns
    return None

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
            override={'LIBRARY_OVERRIDABLE'})

    def FloatPropOVR(default, name="", description="", precision=2, min=0, max=1, update=None):
        return bpy.props.FloatProperty(
            name=name,
            default=default,
            description=description,
            precision=precision,
            min=min, max=max,
            update=update,
            override={'LIBRARY_OVERRIDABLE'})


def initMhxProps():
    from . import fkik

    bpy.types.Object.MhxRig = BoolProperty(default = False)
    bpy.types.Object.MhxChildOfConstraints = BoolProperty(default = False)

    # Gaze
    bpy.types.Object.MhaGazeFollowsHead = FloatPropOVR(0.0,
        name = "Gaze Follows Head",
        description = "The gaze bone follows the head bone rotations")

    bpy.types.Object.MhaGaze_L = FloatPropOVR(0.0,
        name = "Gaze Left",
        description = "eye tracking the left gaze bone amount")

    bpy.types.Object.MhaGaze_R = FloatPropOVR(0.0,
        name = "Gaze Right",
        description = "eye tracking the right gaze bone amount")

    bpy.types.Object.MhaTongueIk = BoolPropOVR(False,
        name = "Tongue IK",
        description = "Tongue bones controlled by IK")

    # Hinge
    bpy.types.Object.MhaArmHinge_L = FloatPropOVR(0.0,
        name = "Arm Hinge Left",
        description = "arm decoupled from the spine rotation")

    bpy.types.Object.MhaArmHinge_R = FloatPropOVR(0.0,
        name = "Arm Hinge Right",
        description = "arm decoupled from the spine rotation")

    bpy.types.Object.MhaLegHinge_L = FloatPropOVR(0.0,
        name = "Leg Hinge Left",
        description = "leg decoupled from the pelvis rotation")

    bpy.types.Object.MhaLegHinge_R = FloatPropOVR(0.0,
        name = "Leg Hinge Right",
        description = "leg decoupled from the pelvis rotation")

    # Hands and fingers
    bpy.types.Object.MhaForearmFollow_L = BoolPropOVR(True,
        name = "Forearm Follows Hand Left",
        description = "Control left forearm twist with left hand twist.\nIt may be necessary to turn this off for correct FK->IK snapping.",
        update = fkik.setForearmFollowLeft)

    bpy.types.Object.MhaForearmFollow_R = BoolPropOVR(True,
        name = "Forearm Follows Hand Right",
        description = "Control right forearm twist with right hand twist.\nIt may be necessary to turn this off for correct FK->IK snapping.",
        update = fkik.setForearmFollowRight)

    bpy.types.Object.MhaFingerControl_L = BoolPropOVR(False,
        name = "Long Fingers Left",
        description = "finger links controlled by the long finger bones")

    bpy.types.Object.MhaFingerControl_R = BoolPropOVR(False,
        name = "Long Fingers Right",
        description = "finger links controlled by the long finger bones")

    bpy.types.Object.MhaFingerIk_L = BoolPropOVR(False,
        name = "Finger IK Left",
        description = "finger links controlled by IK")

    bpy.types.Object.MhaFingerIk_R = BoolPropOVR(False,
        name = "Finger IK Right",
        description = "finger links controlled by IK")

    # IK
    bpy.types.Object.MhaLimitsOn = BoolPropOVR(True,
        name = "Rotation Limits",
        description = "Toggle FK and IK rotation limits.\nIt may be necessary to turn these off for correct FK->IK snapping.",
        update = fkik.toggleFkIkLimits)

    bpy.types.Object.MhaLegIkToAnkle_L = BoolPropOVR(False,
        name = "Ankle IK Left",
        description = "Use ankle bone as IK target for left leg")

    bpy.types.Object.MhaLegIkToAnkle_R = BoolPropOVR(False,
        name = "Ankle IK Right",
        description = "Use ankle bone as IK target for right leg")

    bpy.types.Object.MhaArmIk_L = FloatPropOVR(0.0, precision=3,
        name = "Arm IK Left",
        description = "Left arm IK influence")

    bpy.types.Object.MhaLegIk_L = FloatPropOVR(0.0, precision=3,
        name = "Arm IK Right",
        description = "Right arm IK influence")

    bpy.types.Object.MhaArmIk_R = FloatPropOVR(0.0, precision=3,
        name = "Leg IK Left",
        description = "Left leg IK influence")

    bpy.types.Object.MhaLegIk_R = FloatPropOVR(0.0, precision=3,
        name = "Leg IK Right",
        description = "Right leg IK influence")

    # Elbow and Knee parents
    bpy.types.Object.MhaElbowHand_L = FloatPropOVR(0.0,
        name = "Hand>Elbow Left",
        description = "Parent left elbow pole to hand")
    bpy.types.Object.MhaElbowShoulder_L = FloatPropOVR(0.0,
        name = "Shoulder>Elbow Left",
        description = "Parent left elbow pole to shoulder")
    bpy.types.Object.MhaElbowHand_R = FloatPropOVR(0.0,
        name = "Hand>Elbow Right",
        description = "Parent right elbow pole to hand")
    bpy.types.Object.MhaElbowShoulder_R = FloatPropOVR(0.0,
        name = "Shoulder>Elbow Right",
        description = "Parent right elbow pole to shoulder")

    bpy.types.Object.MhaKneeFoot_L = FloatPropOVR(0.0,
        name = "Foot>Knee Left",
        description = "Parent left knee pole to foot")
    bpy.types.Object.MhaKneeHip_L = FloatPropOVR(0.0,
        name = "Hip>Knee Left",
        description = "Parent left knee pole to hip")
    bpy.types.Object.MhaKneeFoot_R = FloatPropOVR(0.0,
        name = "Foot>Knee Right",
        description = "Parent right knee pole to foot")
    bpy.types.Object.MhaKneeHip_R = FloatPropOVR(0.0,
        name = "Hip>Knee Right",
        description = "Parent right knee pole to hip")

    # Elbow and knee parents, changed in edit mode
    elbowEnums = [
        ('HAND', "Hand", "Parent elbow pole target to IK hand"),
        ('SHOULDER', "Shoulder", "Parent elbow pole target to shoulder"),
        ('MASTER', "Master", "Parent elbow pole target to the master bone")]
    bpy.types.Object.MhaElbowParent_L = EnumProperty(
        items = elbowEnums,
        name = "Left Elbow Parent",
        description = "Parent of left elbow pole target")
    bpy.types.Object.MhaElbowParent_R = EnumProperty(
        items = elbowEnums,
        name = "Right Elbow Parent",
        description = "Parent of right elbow pole target")

    kneeEnums = [
        ('FOOT', "Foot", "Parent knee pole target to IK foot"),
        ('HIP', "Hip", "Parent knee pole target to hip"),
        ('MASTER', "Master", "Parent knee pole target to the master bone")]
    bpy.types.Object.MhaKneeParent_L = EnumProperty(
        items = kneeEnums,
        name = "Left Knee Parent",
        description = "Parent of left knee pole target")
    bpy.types.Object.MhaKneeParent_R = EnumProperty(
        items = kneeEnums,
        name = "Right Knee Parent",
        description = "Parent of right knee pole target")

    # Stretchiness
    bpy.types.Object.MhaArmStretch_L = FloatPropOVR(0.0,
        name = "Arm Stretch Left",
        description = "Toggle left arm stretchiness")

    bpy.types.Object.MhaLegStretch_L = FloatPropOVR(0.0,
        name = "Leg Stretch Left",
        description = "Toggle left leg stretchiness")

    bpy.types.Object.MhaArmStretch_R = FloatPropOVR(0.0,
        name = "Arm Stretch Right",
        description = "Toggle right arm stretchiness")

    bpy.types.Object.MhaLegStretch_R = FloatPropOVR(0.0,
        name = "Leg Stretch Right",
        description = "Toggle right leg stretchiness")

    bpy.types.Object.MhaToeTarsal_L = BoolProperty(
        name = "Toes Tarsal Parent Left",
        description = "Toggle left toes tarsal parent",
        default = False)

    bpy.types.Object.MhaToeTarsal_R = BoolProperty(
        name = "Toes Tarsal Parent Right",
        description = "Toggle right toes tarsal parent",
        default = False)


classes = [
    MHX_OT_EnableAllLayers,
    MHX_OT_DisableAllLayers,
    MHX_OT_ConvertMhxActions,
    MHX_OT_UpdateMhx,
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
