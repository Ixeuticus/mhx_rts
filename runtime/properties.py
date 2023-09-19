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

    bpy.types.Object.MhaTongueControl = BoolPropOVR(True,
        name = "FK/IK Tongue",
        description = "Tongue links controlled by the FK/IK tongue bones")

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

#----------------------------------------------------------
#
#----------------------------------------------------------

if __name__ == "__main__":
    initMhxProps()