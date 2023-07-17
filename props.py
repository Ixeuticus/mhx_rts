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
from bpy.props import *

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
        def fixFcurve(fcu, rig):
            for var in list(fcu.driver.variables):
                trg = var.targets[0]
                prop = baseRef(trg.data_path)
                if trg.id == rig.data and prop[0:3] == "Mha":
                    value = getValue(prop, rig.data[prop])
                    if hasattr(rig, prop):
                        setattr(rig, prop, value)
                        nvar = fcu.driver.variables.new()
                        varname = var.name
                        ntrg = nvar.targets[0]
                        ntrg.id_type == 'OBJECT'
                        ntrg.id = rig
                        ntrg.data_path = propRef(prop)
                        fcu.driver.variables.remove(var)
                        nvar.name = varname
                    else:
                        rig[prop] = value
                elif trg.id == rig and prop[0:3] == "Mha":
                    value = getValue(prop, getattr(rig, prop))
                    if hasattr(rig, prop):
                        for trg in var.targets:
                            trg.data_path = propRef(prop)
                    else:
                        rig[prop] = value

        def getValue(key, value):
            if key.startswith("MhaElbowParent") and isinstance(value, int):
                return {0: 'HAND', 1: 'SHOULDER', 2: 'MASTER'}[value]
            elif key.startswith("MhaKneeParent") and isinstance(value, int):
                return {0: 'FOOT', 1: 'HIP', 2: 'MASTER'}[value]
            elif isinstance(value, bool):
                return bool(value)
            else:
                return value

        rig = context.object
        for key in list(rig.data.keys()):
            if key[0:3] == "Mha":
                value = getValue(key, rig.data[key])
                if hasattr(rig, key):
                    setattr(rig, key, value)
                else:
                    rig[key] = value
        if rig.animation_data:
            for fcu in rig.animation_data.drivers:
                fixFcurve(fcu, rig)
        if rig.data.animation_data:
            for fcu in rig.data.animation_data.drivers:
                fixFcurve(fcu, rig)
        for key in list(rig.data.keys()):
            if key[0:3] == "Mha" and hasattr(rig, key):
                del rig.data[key]

        def addStretchDrivers():
            from import_daz.mhx import addDriver, copyLocation
            for suffix in ["L", "R"]:
                useStretch = False
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
                            addDriver(cns, "influence", rig, propRef(prop2), "x")
                for bname,prop in [
                    ("foot.fk", "MhaLegStretch"),
                    ("hand.fk", "MhaArmStretch"),
                ]:
                    pb = rig.pose.bones["%s.%s" % (bname, suffix)]
                    prop2 = "%s_%s" % (prop, suffix)
                    cns = getConstraint(pb, 'COPY_LOCATION')
                    if cns:
                        cns.driver_remove("influence")
                        addDriver(cns, "influence", rig, propRef(prop2), "1-x")
                    else:
                        cns = copyLocation(pb, pb.parent, rig, prop2, "1-x")
                        cns.head_tail = 1.0

        addStretchDrivers()
        setMode('EDIT')
        for suffix in ["L", "R"]:
            for bname,conn in [
                ("hand", False),
                ("hand.fk", False),
                ("foot", False),
                ("foot.fk", False),
                ("toe", True),
                ("toe.fk", True),
            ]:
                eb = rig.data.edit_bones.get("%s.%s" % (bname, suffix))
                if eb:
                    eb.use_connect = conn
        setMode('POSE')
        rig.data.MhaFeatures |= F_IDPROPS


def getConstraint(pb, ctype):
    for cns in pb.constraints:
        if cns.type == ctype:
            return cns
    return None

#-------------------------------------------------------------
#   Bake MHX
#-------------------------------------------------------------

def getProp(string):
    if string[0:2] == '["' and string[-2:] == '"]':
        return string[2:-2]
    return None

class MhxBaker:
    def run(self, context):
        rig = context.object
        props = []
        for prop in dir(rig):
            if prop.startswith(("Mha", "Mhx")):
                props.append(prop)
        self.setProps(rig, props)
        if rig.animation_data:
            self.changeDrivers(rig, props)
        if rig.data.animation_data:
            self.changeDrivers(rig.data, props)
        rig.DazRig = self.rigtype


class MHX_OT_BakeMhx(MhxBaker, MhxOperator):
    bl_idname = "mhx.bake_mhx"
    bl_label = "Bake MHX"
    bl_description = "Bake MHX properties to make MHX animations work\nalso if the MHX RTS add-on is disabled"
    bl_options = {'UNDO'}

    rigtype = "baked-mhx"

    def setProps(self, rig, props):
        for prop in props:
            x = getattr(rig, prop)
            rig[prop] = x

    def changeDrivers(self, rna, props):
        for fcu in list(rna.animation_data.drivers):
            for var in fcu.driver.variables:
                for trg in var.targets:
                    prop = trg.data_path
                    if prop in props:
                        trg.data_path = '["%s"]' % prop


class MHX_OT_UnbakeMhx(MhxBaker, MhxOperator):
    bl_idname = "mhx.unbake_mhx"
    bl_label = "Unbake MHX"
    bl_description = "Remove baked MHX properties to use the MHX RTS add-on"
    bl_options = {'UNDO'}

    rigtype = "mhx"

    def setProps(self, rig, props):
        return

    def changeDrivers(self, rna, props):
        for fcu in list(rna.animation_data.drivers):
            for var in fcu.driver.variables:
                for trg in var.targets:
                    prop = getProp(trg.data_path)
                    if prop and prop in props:
                        trg.data_path = prop

#-------------------------------------------------------------
#   Overridable properties
#-------------------------------------------------------------

if bpy.app.version < (2,90,0):
    def BoolPropOVR(default, name="", description=""):
        return bpy.props.BoolProperty(
            name=name,
            default=default,
            description=description)

    def FloatPropOVR(default, name="", description="", precision=2, min=0, max=1):
        return bpy.props.FloatProperty(
            name=name,
            default=default,
            description=description,
            precision=precision,
            min=min, max=max)
else:
    def BoolPropOVR(default, name="", description=""):
        return bpy.props.BoolProperty(
            name=name,
            default=default,
            description=description,
            override={'LIBRARY_OVERRIDABLE'})

    def FloatPropOVR(default, name="", description="", precision=2, min=0, max=1):
        return bpy.props.FloatProperty(
            name=name,
            default=default,
            description=description,
            precision=precision,
            min=min, max=max,
            override={'LIBRARY_OVERRIDABLE'})


def initMhxProps():
    bpy.types.Object.MhxRig = BoolProperty(default = False)
    bpy.types.Armature.MhaFeatures = IntProperty(default = 0)
    bpy.types.Object.MhxChildOfConstraints = BoolProperty(default = False)

    # Gaze
    bpy.types.Object.MhaGazeFollowsHead = FloatPropOVR(0.0,
        name = "Gaze Follows Head",
        min = 0, max = 1,
        description = "The gaze bone follows the head bone rotations")

    bpy.types.Object.MhaGaze_L = FloatPropOVR(0.0,
        name = "Gaze Left",
        min = 0, max = 1,
        description = "Eye tracking the left gaze bone amount")

    bpy.types.Object.MhaGaze_R = FloatPropOVR(0.0,
        name = "Gaze Right",
        min = 0, max = 1,
        description = "Eye tracking the right gaze bone amount")

    bpy.types.Object.MhaTongueIk = FloatPropOVR(0.0,
        name = "Tongue IK",
        min = 0, max = 1,
        description = "Tongue bones controlled by IK")

    # Hinge
    bpy.types.Object.MhaArmHinge_L = FloatPropOVR(0.0,
        name = "Arm Hinge Left",
        min = 0, max = 1,
        description = "Arm decoupled from the spine rotation")

    bpy.types.Object.MhaArmHinge_R = FloatPropOVR(0.0,
        name = "Arm Hinge Right",
        min = 0, max = 1,
        description = "Arm decoupled from the spine rotation")

    bpy.types.Object.MhaLegHinge_L = FloatPropOVR(0.0,
        name = "Leg Hinge Left",
        min = 0, max = 1,
        description = "Leg decoupled from the pelvis rotation")

    bpy.types.Object.MhaLegHinge_R = FloatPropOVR(0.0,
        name = "Leg Hinge Right",
        min = 0, max = 1,
        description = "Leg decoupled from the pelvis rotation")

    # Hands and fingers
    bpy.types.Object.MhaForearmFollow_L = BoolPropOVR(True,
        name = "Forearm Follows Hand Left",
        description = "Control left forearm twist with left hand twist.\nIt may be necessary to turn this off for correct FK->IK snapping.")

    bpy.types.Object.MhaForearmFollow_R = BoolPropOVR(True,
        name = "Forearm Follows Hand Right",
        description = "Control right forearm twist with right hand twist.\nIt may be necessary to turn this off for correct FK->IK snapping.")

    bpy.types.Object.MhaFingerControl_L = BoolPropOVR(False,
        name = "Long Fingers Left",
        description = "Finger links controlled by the long finger bones")

    bpy.types.Object.MhaFingerControl_R = BoolPropOVR(False,
        name = "Long Fingers Right",
        description = "Finger links controlled by the long finger bones")

    bpy.types.Object.MhaFingerIk_L = FloatPropOVR(0.0,
        name = "Finger IK Left",
        min = 0, max = 1,
        description = "Finger links controlled by IK")

    bpy.types.Object.MhaFingerIk_R = FloatPropOVR(0.0,
        name = "Finger IK Right",
        min = 0, max = 1,
        description = "Finger links controlled by IK")

    # IK
    bpy.types.Object.MhaLimitsOn = BoolPropOVR(True, name = "Rotation Limits")

    bpy.types.Object.MhaLegIkToAnkle_L = FloatPropOVR(0.0, precision=3,
        name = "Ankle IK Left",
        min = 0, max = 1,
        description = "Use ankle bone as IK target for left leg")

    bpy.types.Object.MhaLegIkToAnkle_R = FloatPropOVR(0.0, precision=3,
        name = "Ankle IK Right",
        min = 0, max = 1,
        description = "Use ankle bone as IK target for right leg")

    bpy.types.Object.MhaArmIk_L = FloatPropOVR(0.0, precision=3,
        name = "Arm IK Left",
        min = 0, max = 1,
        description = "Left arm IK influence")

    bpy.types.Object.MhaArmIk_R = FloatPropOVR(0.0, precision=3,
        name = "Arm IK Right",
        min = 0, max = 1,
        description = "Right arm IK influence")

    bpy.types.Object.MhaLegIk_L = FloatPropOVR(0.0, precision=3,
        name = "Leg IK Left",
        min = 0, max = 1,
        description = "Left leg IK influence")

    bpy.types.Object.MhaLegIk_R = FloatPropOVR(0.0, precision=3,
        name = "Leg IK Right",
        min = 0, max = 1,
        description = "Right leg IK influence")

    # Elbow and Knee parents
    bpy.types.Object.MhaElbowHand_L = FloatPropOVR(0.0,
        name = "Hand>Elbow Left",
        min = 0, max = 1,
        description = "Parent left elbow pole to hand")
    bpy.types.Object.MhaElbowShoulder_L = FloatPropOVR(0.0,
        name = "Shoulder>Elbow Left",
        min = 0, max = 1,
        description = "Parent left elbow pole to shoulder")
    bpy.types.Object.MhaElbowHand_R = FloatPropOVR(0.0,
        name = "Hand>Elbow Right",
        min = 0, max = 1,
        description = "Parent right elbow pole to hand")
    bpy.types.Object.MhaElbowShoulder_R = FloatPropOVR(0.0,
        name = "Shoulder>Elbow Right",
        min = 0, max = 1,
        description = "Parent right elbow pole to shoulder")

    bpy.types.Object.MhaKneeFoot_L = FloatPropOVR(0.0,
        name = "Foot>Knee Left",
        min = 0, max = 1,
        description = "Parent left knee pole to foot")
    bpy.types.Object.MhaKneeHip_L = FloatPropOVR(0.0,
        name = "Hip>Knee Left",
        min = 0, max = 1,
        description = "Parent left knee pole to hip")
    bpy.types.Object.MhaKneeFoot_R = FloatPropOVR(0.0,
        name = "Foot>Knee Right",
        min = 0, max = 1,
        description = "Parent right knee pole to foot")
    bpy.types.Object.MhaKneeHip_R = FloatPropOVR(0.0,
        name = "Hip>Knee Right",
        min = 0, max = 1,
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
        min = 0, max = 1,
        description = "Toggle left arm stretchiness")

    bpy.types.Object.MhaLegStretch_L = FloatPropOVR(0.0,
        name = "Leg Stretch Left",
        min = 0, max = 1,
        description = "Toggle left leg stretchiness")

    bpy.types.Object.MhaArmStretch_R = FloatPropOVR(0.0,
        name = "Arm Stretch Right",
        min = 0, max = 1,
        description = "Toggle right arm stretchiness")

    bpy.types.Object.MhaLegStretch_R = FloatPropOVR(0.0,
        name = "Leg Stretch Right",
        min = 0, max = 1,
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
    MHX_OT_BakeMhx,
    MHX_OT_UnbakeMhx,
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
