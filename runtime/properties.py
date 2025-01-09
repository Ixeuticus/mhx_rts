# SPDX-FileCopyrightText: 2016-2024, Thomas Larsson
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# ---------------------------------------------------------------------------
#
# The purpose of this file is to make MHX animations work correctly even if the
# mhx_rts add-on is not available. A typical situation might be if you send
# the blend file to an external rendering service.
#
# 1. Open this file (runtime/properties.py) in a text editor window.
# 2. Enable the Text > Register checkbox.
# 3. Run the script (Run Script)
# 4. Save the blend file.
# 5. Reload the blend file.
#
# ---------------------------------------------------------------------------

import bpy
from bpy.props import *

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

#----------------------------------------------------------
#   Init MHX Properties
#----------------------------------------------------------

def initMhxProps():
    bpy.types.Armature.MhaFeatures = IntProperty(default = 0)

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

    bpy.types.Object.MhaTongueControl = BoolPropOVR(True,
        name = "FK/IK Tongue",
        description = "Tongue links controlled by the FK/IK tongue bones")

    bpy.types.Object.MhaTongueIk = FloatPropOVR(0.0,
        name = "Tongue IK",
        min = 0, max = 1,
        description = "Tongue bones controlled by IK")

    # Neck - head follows
    bpy.types.Object.MhaNeckFollows = FloatPropOVR(1.0,
        name = "Neck Follows",
        min = 0, max = 1,
        description = "Neck rotation follows spine")

    bpy.types.Object.MhaHeadFollows = FloatPropOVR(1.0,
        name = "Head Follows",
        min = 0, max = 1,
        description = "Head rotation follows spine")

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
        name = "FK/IK Fingers Left",
        description = "Finger links controlled by the FK/IK finger bones")

    bpy.types.Object.MhaFingerControl_R = BoolPropOVR(False,
        name = "FK/IK Fingers Right",
        description = "Finger links controlled by the FK/IK finger bones")

    bpy.types.Object.MhaFingerIk_L = FloatPropOVR(0.0, precision=3,
        name = "Finger IK Left",
        min = 0, max = 1,
        description = "Finger IK influence")

    bpy.types.Object.MhaFingerIk_R = FloatPropOVR(0.0, precision=3,
        name = "Finger IK Right",
        min = 0, max = 1,
        description = "Finger IK influence")

    # IK
    bpy.types.Object.MhaLimitsOn = BoolPropOVR(True, name = "Rotation Limits")

    bpy.types.Object.MhaNeckControl = BoolPropOVR(True,
        name = "FK/IK Neck",
        description = "Neck links controlled by the FK/IK back bones")

    bpy.types.Object.MhaSpineControl = BoolPropOVR(True,
        name = "FK/IK Spine",
        description = "Spine links controlled by the FK/IK back bones")

    bpy.types.Object.MhaSpineIk = FloatPropOVR(0.0, precision=3,
        name = "Spine IK",
        min = 0, max = 1,
        description = "Spine IK influence")

    bpy.types.Object.MhaSpineFollowsHip = FloatPropOVR(0.0, precision=3,
        name = "IK Spine Follows Hip",
        min = 0, max = 1,
        description = "IK spine follows hip")

    bpy.types.Object.MhaShaftControl = BoolPropOVR(True,
        name = "FK/IK Shaft",
        description = "Shaft links controlled by the FK/IK shaft bones")

    bpy.types.Object.MhaShaftIk = FloatPropOVR(0.0, precision=3,
        name = "Shaft IK",
        min = 0, max = 1,
        description = "Shaft IK influence")

    bpy.types.Object.MhaLegIkToAnkle_L = BoolPropOVR(False,
        name = "Ankle IK Left",
        description = "Use ankle bone as IK target for left leg")

    bpy.types.Object.MhaLegIkToAnkle_R = BoolPropOVR(False,
        name = "Ankle IK Right",
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
    bpy.types.Object.MhaArmStretch_L = FloatPropOVR(1.0,
        name = "Arm Stretch Left",
        min = 0, max = 1,
        description = "Toggle left arm stretchiness")

    bpy.types.Object.MhaLegStretch_L = FloatPropOVR(1.0,
        name = "Leg Stretch Left",
        min = 0, max = 1,
        description = "Toggle left leg stretchiness")

    bpy.types.Object.MhaArmStretch_R = FloatPropOVR(1.0,
        name = "Arm Stretch Right",
        min = 0, max = 1,
        description = "Toggle right arm stretchiness")

    bpy.types.Object.MhaLegStretch_R = FloatPropOVR(1.0,
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

#----------------------------------------------------------
#
#----------------------------------------------------------

if __name__ == "__main__":
    initMhxProps()