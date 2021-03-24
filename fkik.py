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
from bpy.props import StringProperty
from mathutils import *
from .utils import *
from .layers import *

#------------------------------------------------------------------
#   Get pose matrix
#------------------------------------------------------------------

def getPoseMatrix(gmat, pb):
    restInv = pb.bone.matrix_local.inverted()
    if pb.parent:
        parInv = pb.parent.matrix.inverted()
        parRest = pb.parent.bone.matrix_local
        return restInv @ parRest @ parInv @ gmat
    else:
        return restInv @ gmat


def getGlobalMatrix(mat, pb):
    gmat = pb.bone.matrix_local @ mat
    if pb.parent:
        parMat = pb.parent.matrix
        parRest = pb.parent.bone.matrix_local
        return parMat @ parRest.inverted() @ gmat
    else:
        return gmat


def updatePose():
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')

#------------------------------------------------------------------
#   Snapper class
#------------------------------------------------------------------

class Snapper:

    def setup(self, context, value):
        bpy.ops.object.mode_set(mode='POSE')
        rig = context.object
        self.rig = rig
        self.amt = rig.data
        self.auto = context.scene.tool_settings.use_keyframe_insert_auto
        self.amt[self.prop] = value
        rig.data.layers[self.ik] = True
        rig.data.layers[self.fk] = True
        rig.data.layers[self.extra] = True
        self.muteAllConstraints(True)
        updatePose()


    def restore(self, value, ik, fk):
        (oldValue, oldIk, oldFk, oldExtra) = old
        self.amt[self.prop] = oldValue
        self.rig.data.layers[self.ik] = oldIk
        self.rig.data.layers[self.fk] = oldFk
        self.rig.data.layers[self.extra] = oldExtra
        self.amt[self.prop] = value
        self.muteAllConstraints(False)
        updatePose()


    def matchPoseTranslation(self, pb, src):
        pmat = getPoseMatrix(src.matrix, pb)
        self.insertLocation(pb, pmat)


    def insertLocation(self, pb, mat):
        pb.location = mat.to_translation()
        if self.auto or self.isKeyed(pb, "location"):
            pb.keyframe_insert("location", group=pb.name)


    def matchPoseRotation(self, pb, src):
        pmat = getPoseMatrix(src.matrix, pb)
        self.insertRotation(pb, pmat)


    def matchPoseLocRot(self, pb, src):
        pmat = getPoseMatrix(src.matrix, pb)
        self.insertLocation(pb, pmat)
        self.insertRotation(pb, pmat)


    def matchPoseTransform(self, pb, src):
        pmat = getPoseMatrix(src.matrix, pb)
        self.insertRotation(pb, pmat)


    def insertRotation(self, pb, mat):
        quat = mat.to_quaternion()
        if pb.rotation_mode == 'QUATERNION':
            pb.rotation_quaternion = quat
            if self.auto or self.isKeyed(pb, "rotation_quaternion"):
                pb.keyframe_insert("rotation_quaternion", group=pb.name)
        else:
            pb.rotation_euler = quat.to_euler(pb.rotation_mode)
            if self.auto or self.isKeyed(pb, "rotation_euler"):
                pb.keyframe_insert("rotation_euler", group=pb.name)


    def matchPoseTwist(self, pb, src):
        pmat0 = src.matrix_basis
        euler = pmat0.to_3x3().to_euler('YZX')
        euler.z = 0
        pmat = euler.to_matrix().to_4x4()
        pmat.col[3] = pmat0.col[3]
        self.insertRotation(pb, pmat)


    def matchIkLeg(self, legIk, toeFk, mBall, mToe, mHeel):
        rmat = toeFk.matrix.to_3x3()
        tHead = Vector(toeFk.matrix.col[3][:3])
        ty = rmat.col[1]
        tail = tHead + ty * toeFk.bone.length

        try:
            zBall = mBall.matrix.col[3][2]
        except AttributeError:
            return
        zToe = mToe.matrix.col[3][2]
        zHeel = mHeel.matrix.col[3][2]

        x = Vector(rmat.col[0])
        y = Vector(rmat.col[1])
        z = Vector(rmat.col[2])

        if zHeel > zBall and zHeel > zToe:
            # 1. foot.ik is flat
            if abs(y[2]) > abs(z[2]):
                y = -z
            y[2] = 0
        else:
            # 2. foot.ik starts at heel
            hHead = Vector(mHeel.matrix.col[3][:3])
            y = tail - hHead

        y.normalize()
        x -= x.dot(y)*y
        x.normalize()
        z = x.cross(y)
        head = tail - y * legIk.bone.length

        # Create matrix
        gmat = Matrix()
        gmat.col[0][:3] = x
        gmat.col[1][:3] = y
        gmat.col[2][:3] = z
        gmat.col[3][:3] = head
        pmat = getPoseMatrix(gmat, legIk)

        self.insertLocation(legIk, pmat)
        self.insertRotation(legIk, pmat)


    def matchPoleTarget(self, pb, above, below):
        ay = Vector(above.matrix.col[1][:3])
        by = Vector(below.matrix.col[1][:3])
        az = Vector(above.matrix.col[2][:3])
        bz = Vector(below.matrix.col[2][:3])
        p0 = Vector(below.matrix.col[3][:3])
        n = ay.cross(by)
        if abs(n.length) > 1e-4:
            d = ay - by
            n.normalize()
            d -= d.dot(n)*n
            d.normalize()
            if d.dot(az) > 0:
                d = -d
            p = p0 + 1*pb.bone.length*d
        else:
            p = p0
        gmat = Matrix.Translation(p)
        pmat = getPoseMatrix(gmat, pb)
        self.insertLocation(pb, pmat)


    def matchPoseReverse(self, pb, src):
        gmat = src.matrix
        tail = gmat.col[3] + src.length * gmat.col[1]
        rmat = Matrix((gmat.col[0], -gmat.col[1], -gmat.col[2], tail))
        rmat.transpose()
        pmat = getPoseMatrix(rmat, pb)
        pb.matrix_basis = pmat
        self.insertRotation(pb, pmat)


    def matchPoseScale(self, pb, src):
        pmat = getPoseMatrix(src.matrix, pb)
        pb.scale = pmat.to_scale()
        if self.auto or self.isKeyed(pb, "scale"):
            pb.keyframe_insert("scale", group=pb.name)


    def isKeyed(self, pb, path):
        if self.rig.animation_data:
            act = self.rig.animation_data.action
            if act:
                if pb:
                    path = ('pose.bones["%s"].%s' % (pb.name, path))
                for fcu in act.fcurves:
                    if fcu.data_path == path:
                        return True
        return False


    def getSnapBones(self, key, suffix):
        SnapBones = {
            "Arm"   : ["upper_arm", "forearm", "hand"],
            "ArmFK" : ["upper_arm.fk", "forearm.fk", "hand.fk"],
            "ArmIK" : ["upper_arm.ik", "forearm.ik", None, "elbow.pt.ik", "hand.ik"],
            "Leg"   : ["thigh", "shin", "foot", "toe"],
            "LegFK" : ["thigh.fk", "shin.fk", "foot.fk", "toe.fk"],
            "LegIK" : ["thigh.ik", "shin.ik", "knee.pt.ik", "ankle", "ankle.ik", "foot.ik", "foot.rev", "toe.rev", "ball.marker", "toe.marker", "heel.marker"],
        }
        pbones = []
        constraints = []
        if suffix is None:
            suffix = '.' + self.suffix[1:]
        for name in SnapBones[key]:
            if name:
                try:
                    pb = self.rig.pose.bones[name+suffix]
                except KeyError:
                    pb = None
                pbones.append(pb)
                if pb is not None:
                    for cns in pb.constraints:
                        if cns.type == 'LIMIT_ROTATION' and not cns.mute:
                            constraints.append(cns)
            else:
                pbones.append(None)
        return tuple(pbones),constraints


    def snapFkArm(rig, snapIk, snapFk):
        (uparmFk, loarmFk, handFk) = snapFk
        (uparmIk, loarmIk, elbow, elbowPt, handIk) = snapIk

        self.matchPoseTransform(uparmFk, uparmIk)
        updatePose()
        self.matchPoseTransform(loarmFk, loarmIk)
        updatePose()
        self.matchPoseTransform(handFk, handIk)


    def snapIkArm(rig, snapIk, snapFk):
        (uparmIk, loarmIk, elbow, elbowPt, handIk) = snapIk
        (uparmFk, loarmFk, handFk) = snapFk

        self.matchPoseLocRot(handIk, handFk)
        updatePose()
        self.matchPoleTarget(elbowPt, uparmFk, loarmFk)


    def snapFkLeg(rig, snapIk, snapFk, legIkToAnkle):
        (uplegIk, lolegIk, kneePt, ankle, ankleIk, legIk, footRev, toeRev, mBall, mToe, mHeel) = snapIk
        (uplegFk, lolegFk, footFk, toeFk) = snapFk

        self.matchPoseTransform(uplegFk, uplegIk)
        updatePose()
        self.matchPoseTransform(lolegFk, lolegIk)
        if not legIkToAnkle:
            updatePose()
            self.matchPoseReverse(footFk, footRev)
            updatePose()
            self.matchPoseReverse(toeFk, toeRev)


    def snapIkLeg(rig, snapIk, snapFk, legIkToAnkle):
        (uplegIk, lolegIk, kneePt, ankle, ankleIk, legIk, footRev, toeRev, mBall, mToe, mHeel) = snapIk
        (uplegFk, lolegFk, footFk, toeFk) = snapFk

        self.matchPoseTranslation(ankle, footFk)
        updatePose()
        self.matchIkLeg(legIk, toeFk, mBall, mToe, mHeel)
        updatePose()
        self.matchPoseReverse(toeRev, toeFk)
        updatePose()
        self.matchPoseReverse(footRev, footFk)
        updatePose()
        self.matchPoseTranslation(ankleIk, footFk)
        updatePose()
        self.matchPoleTarget(kneePt, uplegFk, lolegFk)


    def muteAllConstraints(self, value):
        for part in ["ArmIK", "ArmFK", "LegIK", "LegFK"]:
            for suffix in ["_L", "_R"]:
                _snap,constraints = self.getSnapBones(part, suffix)
                for cns in constraints:
                    cns.mute = value


class MHX_OT_MhxSnapFkLeftArm(MhxOperator, Snapper):
    bl_idname = "mhx.snap_fk_left_arm"
    bl_label = "Snap L FK Arm"
    bl_options = {'UNDO'}

    suffix = ".L"
    prop = "MhaArmIk_L"
    ik = L_LARMIK
    fk = L_LARMFK
    extra = L_LEXTRA

    def run(self, context):
        print("Snap Left FK Arm")
        self.setup(context, 1.0)
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "_L")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "_L")
        self.snapFkArm(snapFk, snapIk)
        self.restore(0.0, False, True)


class MHX_OT_MhxSnapFkRightArm(MhxOperator, Snapper):
    bl_idname = "mhx.snap_fk_right_arm"
    bl_label = "Snap R FK Arm"
    bl_options = {'UNDO'}

    suffix = ".R"
    prop = "MhaArmIk_R"
    ik = L_RARMIK
    fk = L_RARMFK
    extra = L_REXTRA

    def run(self, context):
        print("Snap Right FK Arm")
        self.setup(context, 1.0)
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "_R")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "_R")
        self.snapFkArm(snapFk, snapIk)
        self.restore(0.0, False, True)


class MHX_OT_MhxSnapFkLeftLeg(MhxOperator, Snapper):
    bl_idname = "mhx.snap_fk_left_leg"
    bl_label = "Snap L FK Leg"
    bl_options = {'UNDO'}

    suffix = ".L"
    prop = "MhaLegIk_L"
    ik = L_LLEGIK
    fk = L_LLEGFK
    extra = L_LEXTRA

    def run(self, context):
        print("Snap Left FK Leg")
        self.setup(context, 1.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "_L")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "_L")
        self.snapFkLeg(snapFk, snapIk)
        self.restore(0.0, False, True)


class MHX_OT_MhxSnapFkRightLeg(MhxOperator, Snapper):
    bl_idname = "mhx.snap_fk_right_leg"
    bl_label = "Snap R FK Leg"
    bl_options = {'UNDO'}

    suffix = ".R"
    prop = "MhaLegIk_R"
    ik = L_RLEGIK
    fk = L_RLEGFK
    extra = L_REXTRA

    def run(self, context):
        print("Snap Right FK Leg")
        self.setup(context, 1.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "_R")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "_R")
        self.snapFkLeg(snapFk, snapIk)
        self.restore(0.0, False, True)


class MHX_OT_MhxSnapIkLeftArm(MhxOperator, Snapper):
    bl_idname = "mhx.snap_ik_left_arm"
    bl_label = "Snap L IK Arm"
    bl_options = {'UNDO'}

    suffix = ".L"
    prop = "MhaArmIk_L"
    ik = L_LARMIK
    fk = L_LARMFK
    extra = L_LEXTRA

    def run(self, context):
        print("Snap Left IK Arm")
        self.setup(context, 0.0)
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "_L")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "_L")
        self.snapIkArm(snapFk, snapIk)
        self.restore(1.0, False, True)


class MHX_OT_MhxSnapIkRightArm(MhxOperator, Snapper):
    bl_idname = "mhx.snap_ik_right_arm"
    bl_label = "Snap R IK Arm"
    bl_options = {'UNDO'}

    suffix = ".R"
    prop = "MhaArmIk_R"
    ik = L_RARMIK
    fk = L_RARMFK
    extra = L_REXTRA

    def run(self, context):
        print("Snap Right IK Arm")
        self.setup(context, 0.0)
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "_R")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "_R")
        self.snapIkArm(snapFk, snapIk)
        self.restore(1.0, False, True)


class MHX_OT_MhxSnapIkLeftLeg(MhxOperator, Snapper):
    bl_idname = "mhx.snap_ik_left_leg"
    bl_label = "Snap L IK Leg"
    bl_options = {'UNDO'}

    suffix = ".L"
    prop = "MhaLegIk_L"
    ik = L_LLEGIK
    fk = L_LLEGFK
    extra = L_LEXTRA

    def run(self, context):
        print("Snap Left IK Leg")
        self.setup(context, 0.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "_L")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "_L")
        self.snapIkLeg(snapFk, snapIk)
        self.restore(1.0, False, True)


class MHX_OT_MhxSnapIkRightLeg(MhxOperator, Snapper):
    bl_idname = "mhx.snap_ik_right_leg"
    bl_label = "Snap R IK Leg"
    bl_options = {'UNDO'}

    suffix = ".R"
    prop = "MhaLegIk_R"
    ik = L_RLEGIK
    fk = L_RLEGFK
    extra = L_REXTRA

    def run(self, context):
        print("Snap Right IK Leg")
        self.setup(context, 0.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "_R")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "_R")
        self.snapIkLeg(snapFk, snapIk)
        self.restore(1.0, False, True)


class MHX_OT_MhxToggleFkIk(MhxOperator, Snapper):
    bl_idname = "mhx.toggle_fk_ik"
    bl_label = "FK - IK"
    bl_options = {'UNDO'}

    toggle : StringProperty()

    def run(self, context):
        words = self.toggle.split()
        self.setRig(context.object)
        scn = context.scene
        prop = words[0]
        value = float(words[1])
        onLayer = int(words[2])
        offLayer = int(words[3])
        self.rig.data.layers[onLayer] = True
        self.rig.data.layers[offLayer] = False
        self.amt[prop] = value
        path = (propRef(prop))
        if self.isKeyed(None, path):
            self.amt.keyframe_insert(path, frame=scn.frame_current)
        updatePose()


class MHX_OT_MhxToggleHints(MhxOperator):
    bl_idname = "mhx.toggle_hints"
    bl_label = "Elbow And Knee Hints"
    bl_description = "Toggle hints for elbow and knee bending.\nIt may be necessary to turn these off for correct FK->IK snapping."

    def run(self, context):
        rig = context.object
        for pb in rig.pose.bones:
            for cns in pb.constraints:
                if cns.type == 'LIMIT_ROTATION' and cns.name == "Hint":
                    cns.mute = not cns.mute
        rig.data["MhaHintsOn"] = not rig.data["MhaHintsOn"]
        updatePose()

#----------------------------------------------------------
#   Update
#----------------------------------------------------------

theUseAccurate = True

def updatePose():
    if theUseAccurate:
        #updateScene()
        bpy.context.view_layer.update()

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MHX_OT_MhxSnapFkLeftArm,
    MHX_OT_MhxSnapFkRightArm,
    MHX_OT_MhxSnapFkLeftLeg,
    MHX_OT_MhxSnapFkRightLeg,
    MHX_OT_MhxSnapIkLeftArm,
    MHX_OT_MhxSnapIkRightArm,
    MHX_OT_MhxSnapIkLeftLeg,
    MHX_OT_MhxSnapIkRightLeg,
    MHX_OT_MhxToggleFkIk,
    MHX_OT_MhxToggleHints,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

