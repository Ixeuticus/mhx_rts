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
#
# ---------------------------------------------------------------------------
#
# The purpose of this file is to make morphing armatures work even if the
# import_daz add-on is not available. A typical situation might be if you send
# the blend file to an external rendering service.
#
# 1. Open this file (runtime/toggle.py) in a text editor window.
# 2. Enable the Text > Register checkbox.
# 3. Run the script (Run Script)
# 4. Save the blend file.
# 5. Reload the blend file.
#
# ---------------------------------------------------------------------------

import bpy
from bpy.app.handlers import persistent

#----------------------------------------------------------
#   Get MHX rig
#----------------------------------------------------------

def getMhxRig(amt, context):
    rigs = [ob for ob in context.view_layer.objects if ob.data == amt]
    if rigs:
        return rigs[0]
    else:
        print("No MHX rig found")

#----------------------------------------------------------
#   Toggle elbow and knee parents
#----------------------------------------------------------

def toggleElbowKneeParent(rig, prop, bname, polep, limbpar):
    def getChildOf(pb):
        for cns in pb.constraints:
            if cns.type == 'CHILD_OF':
                return cns
        return None

    pb = rig.pose.bones[bname]
    cns = getChildOf(pb)
    if cns is None:
        print("%s has not child-of constraint." % bname)
        return
    wmat = pb.matrix.copy()
    partype = getattr(rig.data, prop)
    if partype in ['HAND', 'FOOT']:
        cns.subtarget = polep
    elif partype in ['SHOULDER', 'HIP']:
        cns.subtarget = limbpar
    elif partype == 'MASTER':
        cns.subtarget = 'master'
    bones = rig.data.bones
    if bones.active:
        active = bones.active.name
    else:
        active = None
    bones.active = pb.bone
    bpy.ops.constraint.childof_set_inverse(constraint=cns.name, owner='BONE')
    if active:
        bones.active = bones[active]
    pb.bone.select = False
    pb.matrix = wmat


def toggleElbowParent_L(amt, context):
    rig = getMhxRig(amt, context)
    if rig:
        toggleElbowKneeParent(rig, "MhaElbowParent_L", "elbow.pt.ik.L", "elbowPoleP.L",  "arm_parent.L")

def toggleElbowParent_R(amt, context):
    rig = getMhxRig(amt, context)
    if rig:
        toggleElbowKneeParent(rig, "MhaElbowParent_R", "elbow.pt.ik.R", "elbowPoleP.R",  "arm_parent.R")

def toggleKneeParent_L(amt, context):
    rig = getMhxRig(amt, context)
    if rig:
        toggleElbowKneeParent(rig, "MhaKneeParent_L", "knee.pt.ik.L", "kneePoleP.L",  "hip")

def toggleKneeParent_R(amt, context):
    rig = getMhxRig(amt, context)
    if rig:
        toggleElbowKneeParent(rig, "MhaKneeParent_R", "knee.pt.ik.R", "kneePoleP.R",  "hip")

#----------------------------------------------------------
#   Register
#----------------------------------------------------------

def initToggleProps():
    from bpy.props import EnumProperty, BoolProperty
    bpy.types.Object.MhxRig = BoolProperty(default = False)

    elbowEnums = [
        ('HAND', "Hand", "Parent elbow pole target to IK hand"),
        ('SHOULDER', "Shoulder", "Parent elbow pole target to shoulder"),
        ('MASTER', "Master", "Parent elbow pole target to the master bone")]
    bpy.types.Armature.MhaElbowParent_L = EnumProperty(
        items = elbowEnums,
        name = "Left Elbow Parent",
        description = "Parent of left elbow pole target",
        options={'LIBRARY_EDITABLE'},
        override={'LIBRARY_OVERRIDABLE'},
        update = toggleElbowParent_L)
    bpy.types.Armature.MhaElbowParent_R = EnumProperty(
        items = elbowEnums,
        name = "Right Elbow Parent",
        description = "Parent of right elbow pole target",
        options={'LIBRARY_EDITABLE'},
        override={'LIBRARY_OVERRIDABLE'},
        update = toggleElbowParent_R)

    kneeEnums = [
        ('FOOT', "Foot", "Parent knee pole target to IK foot"),
        ('HIP', "Hip", "Parent knee pole target to hip"),
        ('MASTER', "Master", "Parent knee pole target to the master bone")]
    bpy.types.Armature.MhaKneeParent_L = EnumProperty(
        items = kneeEnums,
        name = "Left Knee Parent",
        description = "Parent of left knee pole target",
        options={'LIBRARY_EDITABLE'},
        override={'LIBRARY_OVERRIDABLE'},
        update = toggleKneeParent_L)
    bpy.types.Armature.MhaKneeParent_R = EnumProperty(
        items = kneeEnums,
        name = "Right Knee Parent",
        description = "Parent of right knee pole target",
        options={'LIBRARY_EDITABLE'},
        override={'LIBRARY_OVERRIDABLE'},
        update = toggleKneeParent_R)


@persistent
def updateHandler(scn):
    elbowKnees = [
        ("MhaElbowParent_L", "elbow.pt.ik.L", "elbowPoleP.L",  "arm_parent.L"),
        ("MhaElbowParent_R", "elbow.pt.ik.R", "elbowPoleP.R",  "arm_parent.R"),
        ("MhaKneeParent_L", "knee.pt.ik.L", "kneePoleP.L",  "hip"),
        ("MhaKneeParent_R", "knee.pt.ik.R", "kneePoleP.R",  "hip")]
    for rig in scn.objects:
        if (rig.MhxRig and
            not rig.hide_get() and
            not rig.hide_viewport):
            for prop,bname,polep,limbpar in elbowKnees:
                toggleElbowKneeParent(rig, prop, bname, polep, limbpar)


def register():
    initToggleProps()
    bpy.app.handlers.frame_change_post.append(updateHandler)

def unregister():
    bpy.app.handlers.frame_change_post.remove(updateHandler)

if __name__ == "__main__":
    register()