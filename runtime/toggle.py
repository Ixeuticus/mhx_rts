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
    pb = rig.pose.bones[bname]
    wmat = pb.matrix.copy()
    partype = getattr(rig.data, prop)
    if partype in ['HAND', 'FOOT']:
        parname = polep
    elif partype in ['SHOULDER', 'HIP']:
        parname = limbpar
    elif partype == 'MASTER':
        parname = 'master'
    try:
        bpy.ops.object.mode_set(mode='EDIT')
    except RuntimeError as err:
        print(err)
        return
    eb = rig.data.edit_bones[bname]
    eb.parent = rig.data.edit_bones[parname]
    bpy.ops.object.mode_set(mode='POSE')
    pb = rig.pose.bones[bname]
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

@persistent
def updateHandler(scn):
    for rig in scn.objects:
        if (rig.MhxRig and
            not rig.hide_get() and
            not rig.hide_viewport):
            toggleElbowKneeParent(rig, "MhaElbowParent_L", "elbow.pt.ik.L", "elbowPoleP.L",  "arm_parent.L")
            toggleElbowKneeParent(rig, "MhaElbowParent_R", "elbow.pt.ik.R", "elbowPoleP.R",  "arm_parent.R")
            toggleElbowKneeParent(rig, "MhaKneeParent_L", "knee.pt.ik.L", "kneePoleP.L",  "hip")
            toggleElbowKneeParent(rig, "MhaKneeParent_R", "knee.pt.ik.R", "kneePoleP.R",  "hip")


def register():
    bpy.app.handlers.frame_change_post.append(updateHandler)

def unregister():
    bpy.app.handlers.frame_change_post.remove(updateHandler)

if __name__ == "__main__":
    register()