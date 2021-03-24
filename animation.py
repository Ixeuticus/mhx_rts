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
import time
from mathutils import Vector, Matrix
from bpy.props import *
from .utils import *
from .fkik import Snapper

#-------------------------------------------------------------
#   Frame range
#-------------------------------------------------------------

class FrameRange:
    startFrame : IntProperty(
        name = "Start Frame",
        description = "Starting frame for the animation",
        default = 1)

    endFrame : IntProperty(
        name = "Last Frame",
        description = "Last frame for the animation",
        default = 250)

    def draw(self, context):
        self.layout.prop(self, "startFrame")
        self.layout.prop(self, "endFrame")

#-------------------------------------------------------------
#   Limbs bend positive
#-------------------------------------------------------------

class Bender:
    useElbows : BoolProperty(
        name="Elbows",
        description="Keep elbow bending positive",
        default=True)

    useKnees : BoolProperty(
        name="Knees",
        description="Keep knee bending positive",
        default=True)

    useBendPositive : BoolProperty(
        name="Bend Positive",
        description="Ensure that elbow and knee bending is positive",
        default=True)

    def draw(self, context):
        self.layout.prop(self, "useElbows")
        self.layout.prop(self, "useKnees")

    def limbsBendPositive(self, rig, frames):
        limbs = {}
        if self.useElbows:
            pb = getTrgBone("forearm.L", rig)
            self.minimizeFCurve(pb, rig, 0, frames)
            pb = getTrgBone("forearm.R", rig)
            self.minimizeFCurve(pb, rig, 0, frames)
        if self.useKnees:
            pb = getTrgBone("shin.L", rig)
            self.minimizeFCurve(pb, rig, 0, frames)
            pb = getTrgBone("shin.R", rig)
            self.minimizeFCurve(pb, rig, 0, frames)


    def minimizeFCurve(self, pb, rig, index, frames):
        from .floor import findBoneFCurve
        if pb is None:
            return
        fcu = findBoneFCurve(pb, rig, index)
        if fcu is None:
            return
        y0 = fcu.evaluate(0)
        t0 = frames[0]
        t1 = frames[-1]
        for kp in fcu.keyframe_points:
            t = kp.co[0]
            if t >= t0 and t <= t1:
                y = kp.co[1]
                if y < y0:
                    kp.co[1] = y0


class MHX_OT_LimbsBendPositive(HidePropsOperator, IsArmature, Bender, FrameRange):
    bl_idname = "mhx.limbs_bend_positive"
    bl_label = "Bend Limbs Positive"
    bl_description = "Ensure that limbs' X rotation is positive."
    bl_options = {'UNDO'}

    def draw(self, context):
        Bender.draw(self, context)
        FrameRange.draw(self, context)

    def prequel(self, context):
        rig = context.object
        HidePropsOperator.prequel(self, context)
        return (rig, list(rig.data.layers))

    def run(self, context):
        from .loop import getActiveFrames
        scn = context.scene
        rig = context.object
        frames = getActiveFrames(rig, self.startFrame, self.endFrame)
        self.limbsBendPositive(rig, frames)
        print("Limbs bent positive")

    def sequel(self, context, data):
        rig,layers = data
        rig.data.layers = layers
        return HidePropsOperator.sequel(self, context, data)

#-------------------------------------------------------------
#
#-------------------------------------------------------------

theUseAccurate = True

def updatePose():
    if theUseAccurate:
        #updateScene()
        bpy.context.view_layer.update()


def matchPoseTransform(pb, src):
    pmat = getPoseMatrix(src.matrix, pb)
    insertRotation(pb, pmat)
    #pb.scale = pmat.to_scale()
    #pb.keyframe_insert("scale", group=pb.name)


def matchPoseLocRot(pb, src):
    pmat = getPoseMatrix(src.matrix, pb)
    insertLocation(pb, pmat)
    insertRotation(pb, pmat)


def matchPoseTranslation(pb, src):
    pmat = getPoseMatrix(src.matrix, pb)
    insertLocation(pb, pmat)


def matchPoseRotation(pb, src):
    pmat = getPoseMatrix(src.matrix, pb)
    insertRotation(pb, pmat)


def matchPoseTwist(pb, src):
    pmat0 = src.matrix_basis
    euler = pmat0.to_3x3().to_euler('YZX')
    euler.z = 0
    pmat = euler.to_matrix().to_4x4()
    pmat.col[3] = pmat0.col[3]
    insertRotation(pb, pmat)


def printMatrix(string,mat):
    print(string)
    for i in range(4):
        print("    %.4g %.4g %.4g %.4g" % tuple(mat[i]))


def matchIkLeg(legIk, toeFk, mBall, mToe, mHeel):
    rmat = toeFk.matrix.to_3x3()
    tHead = Vector(toeFk.matrix.col[3][:3])
    ty = rmat.col[1]
    tail = tHead + ty * toeFk.bone.length

    zBall = mBall.matrix.col[3][2]
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

    insertLocation(legIk, pmat)
    insertRotation(legIk, pmat)


def matchPoleTarget(pb, above, below):
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
        p = p0 + 6*pb.bone.length*d
    else:
        p = p0
    gmat = Matrix.Translation(p)
    pmat = getPoseMatrix(gmat, pb)
    insertLocation(pb, pmat)


def matchPoseReverse(pb, src):
    gmat = src.matrix
    tail = gmat.col[3] + src.length * gmat.col[1]
    rmat = Matrix((gmat.col[0], -gmat.col[1], -gmat.col[2], tail))
    rmat.transpose()
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')
    pmat = getPoseMatrix(rmat, pb)
    pb.matrix_basis = pmat
    insertRotation(pb, pmat)


def snapFkArm(rig, snapIk, snapFk, frame):

    (uparmFk, loarmFk, handFk) = snapFk
    (uparmIk, loarmIk, elbow, elbowPt, handIk) = snapIk

    matchPoseTransform(uparmFk, uparmIk)
    updatePose()
    matchPoseTransform(loarmFk, loarmIk)
    updatePose()
    matchPoseTransform(handFk, handIk)


def snapIkArm(rig, snapIk, snapFk, frame):

    (uparmIk, loarmIk, elbow, elbowPt, handIk) = snapIk
    (uparmFk, loarmFk, handFk) = snapFk

    matchPoseLocRot(handIk, handFk)
    updatePose()
    matchPoleTarget(elbowPt, uparmFk, loarmFk)


def snapFkLeg(rig, snapIk, snapFk, frame, legIkToAnkle):
    (uplegIk, lolegIk, kneePt, ankle, ankleIk, legIk, footRev, toeRev, mBall, mToe, mHeel) = snapIk
    (uplegFk, lolegFk, footFk, toeFk) = snapFk

    matchPoseTransform(uplegFk, uplegIk)
    updatePose()
    matchPoseTransform(lolegFk, lolegIk)
    if not legIkToAnkle:
        updatePose()
        matchPoseReverse(footFk, footRev)
        updatePose()
        matchPoseReverse(toeFk, toeRev)


def snapIkLeg(rig, snapIk, snapFk, frame, legIkToAnkle):
    (uplegIk, lolegIk, kneePt, ankle, ankleIk, legIk, footRev, toeRev, mBall, mToe, mHeel) = snapIk
    (uplegFk, lolegFk, footFk, toeFk) = snapFk

    matchPoseTranslation(ankle, footFk)
    updatePose()
    matchIkLeg(legIk, toeFk, mBall, mToe, mHeel)
    updatePose()
    matchPoseReverse(toeRev, toeFk)
    updatePose()
    matchPoseReverse(footRev, footFk)
    updatePose()
    matchPoseTranslation(ankleIk, footFk)
    updatePose()
    matchPoleTarget(kneePt, uplegFk, lolegFk)


SnapBonesAlpha8 = {
    "Arm"   : ["upper_arm", "forearm", "hand"],
    "ArmFK" : ["upper_arm.fk", "forearm.fk", "hand.fk"],
    "ArmIK" : ["upper_arm.ik", "forearm.ik", None, "elbow.pt.ik", "hand.ik"],
    "Leg"   : ["thigh", "shin", "foot", "toe"],
    "LegFK" : ["thigh.fk", "shin.fk", "foot.fk", "toe.fk"],
    "LegIK" : ["thigh.ik", "shin.ik", "knee.pt.ik", "ankle", "ankle.ik", "foot.ik", "foot.rev", "toe.rev", "ball.marker", "toe.marker", "heel.marker"],
}

def getSnapBones(rig, key, suffix):
    try:
        rig.pose.bones["thigh.fk.L"]
        names = SnapBonesAlpha8[key]
        suffix = '.' + suffix[1:]
    except KeyError:
        names = None
    if not names:
        raise MHXError("Not an mhx armature")

    pbones = []
    constraints = []
    for name in names:
        if name:
            pb = rig.pose.bones[name+suffix]
            pbones.append(pb)
            for cns in pb.constraints:
                if cns.type == 'LIMIT_ROTATION' and not cns.mute:
                    constraints.append(cns)
        else:
            pbones.append(None)
    return tuple(pbones),constraints


def muteConstraints(constraints, value):
    for cns in constraints:
        cns.mute = value


class Transferer:
    useArms : BoolProperty(
        name="Include Arms",
        description="Include arms in FK/IK snapping",
        default=False)

    useLegs : BoolProperty(
        name="Include Legs",
        description="Include legs in FK/IK snapping",
        default=True)

    accurate : BoolProperty(
        name="Accurate",
        description="Update pose before transfer each bone.\nMore accurate but much slower",
        default=True)

    def draw(self, context):
        self.layout.prop(self, "useArms")
        self.layout.prop(self, "useLegs")
        self.layout.prop(self, "accurate")


    def setAccuracy(self):
        global theUseAccurate
        theUseAccurate = self.accurate


    def getCurrentAction(self, rig):
        if not rig.animation_data:
            raise MHXError("Rig has no animation data")
        act = rig.animation_data.action
        if not act:
            raise MHXError("Rig has no action")
        return act


    def clearAnimation(self, rig, context, act, type, snapBones):
        scn = context.scene
        bnames = []
        if self.useArms:
            for bname in snapBones["Arm" + type]:
                if bname is not None:
                    bnames += [bname+".L", bname+".R"]
        if self.useLegs:
            for bname in snapBones["Leg" + type]:
                if bname is not None:
                    bnames += [bname+".L", bname+".R"]
        self.removeFcurves(act, type, bnames)


    def removeFcurves(self, act, type, bnames):
        fcus = []
        for fcu in act.fcurves:
            words = fcu.data_path.split('"')
            if (words[0] == "pose.bones[" and
                words[1] in bnames):
                fcus.append(fcu)
        if not fcus:
            raise MHXError("%s bones have no animation" % type)
        for fcu in fcus:
            act.fcurves.remove(fcu)


    def transferMhxToFk(self, rig, context):
        from .loop import getActiveFrames

        scn = context.scene

        lArmSnapIk,lArmCnsIk = getSnapBones(rig, "ArmIK", "_L")
        lArmSnapFk,lArmCnsFk = getSnapBones(rig, "ArmFK", "_L")
        rArmSnapIk,rArmCnsIk = getSnapBones(rig, "ArmIK", "_R")
        rArmSnapFk,rArmCnsFk = getSnapBones(rig, "ArmFK", "_R")
        lLegSnapIk,lLegCnsIk = getSnapBones(rig, "LegIK", "_L")
        lLegSnapFk,lLegCnsFk = getSnapBones(rig, "LegFK", "_L")
        rLegSnapIk,rLegCnsIk = getSnapBones(rig, "LegIK", "_R")
        rLegSnapFk,rLegCnsFk = getSnapBones(rig, "LegFK", "_R")

        oldLayers = list(rig.data.layers)
        setMhxIk(rig, self.useArms, self.useLegs, 1.0)
        rig.data.layers = MhxLayers

        lLegIkToAnkle = rig["MhaLegIkToAnkle_L"]
        rLegIkToAnkle = rig["MhaLegIkToAnkle_R"]

        frames = getActiveFrames(rig, self.startFrame, self.endFrame)
        nFrames = len(frames)
        self.useKnees = self.useElbows = True
        self.limbsBendPositive(rig, frames)

        for n,frame in enumerate(frames):
            showProgress(n, frame, nFrames)
            scn.frame_set(frame)
            updateScene()
            if self.useArms:
                snapFkArm(rig, lArmSnapIk, lArmSnapFk, frame)
                snapFkArm(rig, rArmSnapIk, rArmSnapFk, frame)
            if self.useLegs:
                snapFkLeg(rig, lLegSnapIk, lLegSnapFk, frame, lLegIkToAnkle)
                snapFkLeg(rig, rLegSnapIk, rLegSnapFk, frame, rLegIkToAnkle)

        rig.data.layers = oldLayers
        setMhxIk(rig, self.useArms, self.useLegs, 0.0)
        setInterpolation(rig)


    def transferMhxToIk(self, rig, context):
        from .loop import getActiveFrames

        scn = context.scene

        lArmSnapIk,lArmCnsIk = getSnapBones(rig, "ArmIK", "_L")
        lArmSnapFk,lArmCnsFk = getSnapBones(rig, "ArmFK", "_L")
        rArmSnapIk,rArmCnsIk = getSnapBones(rig, "ArmIK", "_R")
        rArmSnapFk,rArmCnsFk = getSnapBones(rig, "ArmFK", "_R")
        lLegSnapIk,lLegCnsIk = getSnapBones(rig, "LegIK", "_L")
        lLegSnapFk,lLegCnsFk = getSnapBones(rig, "LegFK", "_L")
        rLegSnapIk,rLegCnsIk = getSnapBones(rig, "LegIK", "_R")
        rLegSnapFk,rLegCnsFk = getSnapBones(rig, "LegFK", "_R")

        oldLayers = list(rig.data.layers)
        setMhxIk(rig, self.useArms, self.useLegs, 0.0)
        rig.data.layers = MhxLayers

        lLegIkToAnkle = rig["MhaLegIkToAnkle_L"]
        rLegIkToAnkle = rig["MhaLegIkToAnkle_R"]

        frames = getActiveFrames(rig, self.startFrame, self.endFrame)
        nFrames = len(frames)
        for n,frame in enumerate(frames):
            showProgress(n, frame, nFrames)
            scn.frame_set(frame)
            updateScene()
            if self.useArms:
                snapIkArm(rig, lArmSnapIk, lArmSnapFk, frame)
                snapIkArm(rig, rArmSnapIk, rArmSnapFk, frame)
            if self.useLegs:
                snapIkLeg(rig, lLegSnapIk, lLegSnapFk, frame, lLegIkToAnkle)
                snapIkLeg(rig, rLegSnapIk, rLegSnapFk, frame, rLegIkToAnkle)

        rig.data.layers = oldLayers
        setMhxIk(rig, self.useArms, self.useLegs, 1.0)
        setInterpolation(rig)


def muteAllConstraints(rig, value):
    lArmSnapIk,lArmCnsIk = getSnapBones(rig, "ArmIK", "_L")
    lArmSnapFk,lArmCnsFk = getSnapBones(rig, "ArmFK", "_L")
    rArmSnapIk,rArmCnsIk = getSnapBones(rig, "ArmIK", "_R")
    rArmSnapFk,rArmCnsFk = getSnapBones(rig, "ArmFK", "_R")
    lLegSnapIk,lLegCnsIk = getSnapBones(rig, "LegIK", "_L")
    lLegSnapFk,lLegCnsFk = getSnapBones(rig, "LegFK", "_L")
    rLegSnapIk,rLegCnsIk = getSnapBones(rig, "LegIK", "_R")
    rLegSnapFk,rLegCnsFk = getSnapBones(rig, "LegFK", "_R")

    muteConstraints(lArmCnsIk, value)
    muteConstraints(lArmCnsFk, value)
    muteConstraints(rArmCnsIk, value)
    muteConstraints(rArmCnsFk, value)
    muteConstraints(lLegCnsIk, value)
    muteConstraints(lLegCnsFk, value)
    muteConstraints(rLegCnsIk, value)
    muteConstraints(rLegCnsFk, value)

#------------------------------------------------------------------------
#
#------------------------------------------------------------------------

def setLocation(bname, rig):
    pb = rig.pose.bones[bname]
    pb.keyframe_insert("location", group=pb.name)


def setRotation(bname, rig):
    pb = rig.pose.bones[bname]
    if pb.rotation_mode == 'QUATERNION':
        pb.keyframe_insert("rotation_quaternion", group=pb.name)
    else:
        pb.keyframe_insert("rotation_euler", group=pb.name)


def setLocRot(bname, rig):
    pb = rig.pose.bones[bname]
    pb.keyframe_insert("location", group=pb.name)
    pb = rig.pose.bones[bname]
    if pb.rotation_mode == 'QUATERNION':
        pb.keyframe_insert("rotation_quaternion", group=pb.name)
    else:
        pb.keyframe_insert("rotation_euler", group=pb.name)


def setMhxIk(rig, useArms, useLegs, value):
    if isMhxRig(rig):
        ikLayers = []
        fkLayers = []
        if useArms:
            rig["MhaArmIk_L"] = value
            rig["MhaArmIk_R"] = value
            ikLayers += [2,18]
            fkLayers += [3,19]
        if useLegs:
            rig["MhaLegIk_L"] = value
            rig["MhaLegIk_R"] = value
            ikLayers += [4,20]
            fkLayers += [5,21]

        if value:
            first = ikLayers
            second = fkLayers
        else:
            first = fkLayers
            second = ikLayers
        for n in first:
            rig.data.layers[n] = True
        for n in second:
            rig.data.layers[n] = False


def setRigifyFKIK(rig, value):
    rig.pose.bones["hand.ik.L"]["ikfk_switch"] = value
    rig.pose.bones["hand.ik.R"]["ikfk_switch"] = value
    rig.pose.bones["foot.ik.L"]["ikfk_switch"] = value
    rig.pose.bones["foot.ik.R"]["ikfk_switch"] = value
    on = (value < 0.5)
    for n in [6, 9, 12, 15]:
        rig.data.layers[n] = on
    for n in [7, 10, 13, 16]:
        rig.data.layers[n] = not on


def setRigify2FKIK(rig, value):
    rig.pose.bones["upper_arm_parent.L"]["IK_FK"] = value
    rig.pose.bones["upper_arm_parent.R"]["IK_FK"] = value
    rig.pose.bones["thigh_parent.L"]["IK_FK"] = value
    rig.pose.bones["thigh_parent.R"]["IK_FK"] = value
    on = (value > 0.5)
    for n in [8, 11, 14, 17]:
        rig.data.layers[n] = on
    for n in [7, 10, 13, 16]:
        rig.data.layers[n] = not on
    torso = rig.pose.bones["torso"]
    torso["head_follow"] = 1.0
    torso["neck_follow"] = 1.0


def setRigToFK(rig):
    setMhxIk(rig, True, True, 0.0)
    if isRigify(rig):
        setRigifyFKIK(rig, 0.0)
    elif isRigify2(rig):
        setRigify2FKIK(rig, 1.0)

#------------------------------------------------------------------------
#   Buttons
#------------------------------------------------------------------------

class MHX_OT_TransferToFk(HidePropsOperator, Transferer, Bender, FrameRange):
    bl_idname = "mhx.transfer_to_fk"
    bl_label = "Transfer IK => FK"
    bl_description = "Transfer IK animation to FK bones"
    bl_options = {'UNDO'}

    def draw(self, context):
        Transferer.draw(self, context)
        FrameRange.draw(self, context)

    def prequel(self, context):
        muteAllConstraints(context.object, True)
        return HidePropsOperator.prequel(self, context)

    def run(self, context):
        startProgress("Transfer to FK")
        time1 = time.perf_counter()
        self.setAccuracy()
        rig = context.object
        self.transferMhxToFk(rig, context)
        time2 = time.perf_counter()
        raise MHXMessage("Transfer to FK completed\nin %1f seconds" % (time2-time1))

    def sequel(self, context, data):
        muteAllConstraints(context.object, False)
        return HidePropsOperator.sequel(self, context, data)


class MHX_OT_TransferToIk(HidePropsOperator, Transferer, FrameRange):
    bl_idname = "mhx.transfer_to_ik"
    bl_label = "Transfer FK => IK"
    bl_description = "Transfer FK animation to IK bones"
    bl_options = {'UNDO'}

    def draw(self, context):
        Transferer.draw(self, context)
        FrameRange.draw(self, context)

    def prequel(self, context):
        muteAllConstraints(context.object, True)
        return HidePropsOperator.prequel(self, context)

    def run(self, context):
        startProgress("Transfer to IK")
        time1 = time.perf_counter()
        self.setAccuracy()
        rig = context.object
        scn = context.scene
        self.transferMhxToIk(rig, context)
        time2 = time.perf_counter()
        raise MHXMessage("Transfer to IK completed\nin %1f seconds" % (time2-time1))

    def sequel(self, context, data):
        muteAllConstraints(context.object, False)
        return HidePropsOperator.sequel(self, context, data)


class MHX_OT_ClearAnimation(MhxPropsOperator, Transferer):
    bl_idname = "mhx.clear_animation"
    bl_label = "Clear Animation"
    bl_description = "Clear Animation For FK or IK Bones"
    bl_options = {'UNDO'}

    type : StringProperty()

    def run(self, context):
        startProgress("Clear animation")
        self.setAccuracy()
        rig = context.object
        scn = context.scene
        act = self.getCurrentAction(rig)

        self.clearAnimation(rig, context, act, self.type, SnapBonesAlpha8)
        if self.type == "FK":
            value = 1.0
        else:
            value = 0.0
        setMhxIk(rig, self.useArms, self.useLegs, value)
        raise MHXMessage("Animation cleared")

#----------------------------------------------------------
#   Clear pole targets
#----------------------------------------------------------

class MHX_OT_ClearPoleTargets(MhxPropsOperator, Transferer):
    bl_idname = "mhx.clear_pole_targets"
    bl_label = "Clear Pole Targets"
    bl_description = "Clear animation for pole targets"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        scn = context.scene
        act = self.getCurrentAction(rig)
        self.findTarget(context, rig)
        bnames = []
        if self.useArms:
            bnames += ["elbow.pt.ik.L", "elbow.pt.ik.R"]
        if self.useLegs:
            bnames += ["knee.pt.ik.L", "knee.pt.ik.R"]
        self.removeFcurves(act, "Pole target", bnames)
        for bname in bnames:
            pb = rig.pose.bones[bname]
            pb.matrix_basis = Matrix()

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MHX_OT_LimbsBendPositive,
    MHX_OT_TransferToFk,
    MHX_OT_TransferToIk,
    MHX_OT_ClearAnimation,
    MHX_OT_ClearPoleTargets,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

