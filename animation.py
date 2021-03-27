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
from .layers import *
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


    def getActiveFrames(self):
        def getActiveFrames0(rig):
            active = {}
            if rig.animation_data is None:
                return active
            action = rig.animation_data.action
            if action is None:
                return active
            for fcu in action.fcurves:
                for kp in fcu.keyframe_points:
                    active[kp.co[0]] = True
            return active

        active = getActiveFrames0(self.rig)
        frames = list(active.keys())
        frames.sort()
        while frames[0] < self.startFrame:
            frames = frames[1:]
        frames.reverse()
        while frames[0] > self.endFrame:
            frames = frames[1:]
        frames.reverse()
        return frames

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

    def limbsBendPositive(self, frames):
        limbs = {}
        if self.useElbows:
            pb = self.getBone("forearm.L")
            self.minimizeFCurve(pb, 0, frames)
            pb = self.getBone("forearm.R")
            self.minimizeFCurve(pb, 0, frames)
        if self.useKnees:
            pb = self.getBone("shin.L")
            self.minimizeFCurve(pb, 0, frames)
            pb = self.getBone("shin.R")
            self.minimizeFCurve(pb, 0, frames)


    def minimizeFCurve(self, pb, idx, frames):
        if pb is None:
            return
        fcu = findBoneFCurve(pb, self.rig, idx)
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
        self.state = (rig, list(rig.data.layers))

    def run(self, context):
        scn = context.scene
        self.rig = context.object
        frames = self.getActiveFrames()
        self.limbsBendPositive(frames)
        print("Limbs bent positive")

    def sequel(self, context):
        rig,layers = self.state
        rig.data.layers = layers
        return HidePropsOperator.sequel(self, context)

#-------------------------------------------------------------
#
#-------------------------------------------------------------

class Transferer(Snapper):
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


    def setMhxIk(self, value):
        ikLayers = []
        fkLayers = []
        if self.useArms:
            self.rig["MhaArmIk_L"] = value
            self.rig["MhaArmIk_R"] = value
            ikLayers += [L_LARMIK, L_RARMIK]
            fkLayers += [L_LARMFK, L_RARMFK]
        if self.useLegs:
            self.rig["MhaLegIk_L"] = value
            self.rig["MhaLegIk_R"] = value
            ikLayers += [L_LLEGIK, L_RLEGIK]
            fkLayers += [L_LLEGFK, L_RLEGFK]
        if value:
            first = ikLayers
            second = fkLayers
        else:
            first = fkLayers
            second = ikLayers
        for n in first:
            self.rig.data.layers[n] = True
        for n in second:
            self.rig.data.layers[n] = False


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


    def transferMhxToFk(self, context):
        scn = context.scene

        lArmSnapIk,lArmCnsIk = self.getSnapBones("ArmIK", "L")
        lArmSnapFk,lArmCnsFk = self.getSnapBones("ArmFK", "L")
        rArmSnapIk,rArmCnsIk = self.getSnapBones("ArmIK", "R")
        rArmSnapFk,rArmCnsFk = self.getSnapBones("ArmFK", "R")
        lLegSnapIk,lLegCnsIk = self.getSnapBones("LegIK", "L")
        lLegSnapFk,lLegCnsFk = self.getSnapBones("LegFK", "L")
        rLegSnapIk,rLegCnsIk = self.getSnapBones("LegIK", "R")
        rLegSnapFk,rLegCnsFk = self.getSnapBones("LegFK", "R")

        self.setMhxIk(1.0)
        lLegIkToAnkle = self.amt["MhaLegIkToAnkle_L"]
        rLegIkToAnkle = self.amt["MhaLegIkToAnkle_R"]
        frames = self.getActiveFrames()
        nFrames = len(frames)
        self.useKnees = self.useElbows = True
        self.limbsBendPositive(frames)

        for n,frame in enumerate(frames):
            showProgress(n, frame, nFrames)
            scn.frame_set(frame)
            if self.useArms:
                self.snapFkArm(lArmSnapFk, lArmSnapIk, frame)
                self.snapFkArm(rArmSnapFk, rArmSnapIk, frame)
            if self.useLegs:
                self.snapFkLeg(lLegSnapFk, lLegSnapIk, lLegIkToAnkle, frame)
                self.snapFkLeg(rLegSnapFk, rLegSnapIk, rLegIkToAnkle, frame)
        self.setMhxIk(0.0)


    def transferMhxToIk(self, context):
        scn = context.scene

        lArmSnapIk,lArmCnsIk = self.getSnapBones("ArmIK", "L")
        lArmSnapFk,lArmCnsFk = self.getSnapBones("ArmFK", "L")
        rArmSnapIk,rArmCnsIk = self.getSnapBones("ArmIK", "R")
        rArmSnapFk,rArmCnsFk = self.getSnapBones("ArmFK", "R")
        lLegSnapIk,lLegCnsIk = self.getSnapBones("LegIK", "L")
        lLegSnapFk,lLegCnsFk = self.getSnapBones("LegFK", "L")
        rLegSnapIk,rLegCnsIk = self.getSnapBones("LegIK", "R")
        rLegSnapFk,rLegCnsFk = self.getSnapBones("LegFK", "R")

        self.setMhxIk(0.0)

        lLegIkToAnkle = self.amt["MhaLegIkToAnkle_L"]
        rLegIkToAnkle = self.amt["MhaLegIkToAnkle_R"]

        frames = self.getActiveFrames()
        nFrames = len(frames)
        for n,frame in enumerate(frames):
            showProgress(n, frame, nFrames)
            scn.frame_set(frame)
            updatePose()
            if self.useArms:
                self.snapIkArm(lArmSnapFk, lArmSnapIk, frame)
                self.snapIkArm(rArmSnapFk, rArmSnapIk, frame)
            if self.useLegs:
                self.snapIkLeg(lLegSnapFk, lLegSnapIk, lLegIkToAnkle, frame)
                self.snapIkLeg(rLegSnapFk, rLegSnapIk, rLegIkToAnkle, frame)

        self.setMhxIk(1.0)

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
        HidePropsOperator.prequel(self, context)
        Snapper.prequel(self, context)

    def sequel(self, context):
        HidePropsOperator.sequel(self, context)
        Snapper.sequel(self, context)

    def run(self, context):
        startProgress("Transfer to FK")
        time1 = time.perf_counter()
        self.setAccuracy()
        self.transferMhxToFk(context)
        time2 = time.perf_counter()
        raise MHXMessage("Transfer to FK completed\nin %1f seconds" % (time2-time1))


class MHX_OT_TransferToIk(HidePropsOperator, Transferer, FrameRange):
    bl_idname = "mhx.transfer_to_ik"
    bl_label = "Transfer FK => IK"
    bl_description = "Transfer FK animation to IK bones"
    bl_options = {'UNDO'}

    def draw(self, context):
        Transferer.draw(self, context)
        FrameRange.draw(self, context)

    def prequel(self, context):
        HidePropsOperator.prequel(self, context)
        Snapper.prequel(self, context)

    def sequel(self, context):
        HidePropsOperator.sequel(self, context)
        Snapper.sequel(self, context)

    def run(self, context):
        startProgress("Transfer to IK")
        time1 = time.perf_counter()
        self.setAccuracy()
        self.transferMhxToIk(context)
        time2 = time.perf_counter()
        raise MHXMessage("Transfer to IK completed\nin %1f seconds" % (time2-time1))


class MHX_OT_ClearAnimation(HidePropsOperator):
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
        self.setMhxIk(value)
        raise MHXMessage("Animation cleared")

#----------------------------------------------------------
#   Clear pole targets
#----------------------------------------------------------

class MHX_OT_ClearPoleTargets(HidePropsOperator):
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

#-------------------------------------------------------------
#   Toe below ball
#-------------------------------------------------------------

class Feet:
    def getFkFeetBones(suffix):
        foot = self.getBone("foot" + suffix)
        toe = self.getBone("toe" + suffix)
        try:
            mBall = self.getBone("ball.marker")
            mToe = self.getBone("toe.marker")
            mHeel = self.getBone("heel.marker")
        except KeyError:
            mBall = mToe = mHeel = None
        return foot,toe,mBall,mToe,mHeel


class MHX_OT_OffsetToes(HidePropsOperator, FrameRange, Feet):
    bl_idname = "mhx.offset_toes"
    bl_label = "Offset Toes"
    bl_description = "Keep toes below the ball of the feet"
    bl_options = {'UNDO'}

    def draw(self, context):
        FrameRange.draw(self, context)


    def run(self, context):
        rig = context.object
        scn = context.scene
        rig,plane = getRigAndPlane(context)
        try:
            useIk = rig["MhaLegIk_L"] or rig["MhaLegIk_R"]
        except KeyError:
            useIk = False
        if useIk:
            raise MocapError("Toe Below Ball only for FK feet")

        layers = list(rig.data.layers)
        startProgress("Keep toes down")
        frames = self.getActiveFrames()
        print("Left toe")
        self.toeBelowBall(context, frames, rig, plane, ".L")
        print("Right toe")
        self.toeBelowBall(context, frames, rig, plane, ".R")
        rig.data.layers = layers
        raise MocapMessage("Toes kept down")


    def toeBelowBall(self, context, frames, rig, plane, suffix):
        from .retarget import getLocks
        from .fkik import getPoseMatrix

        scn = context.scene
        foot,toe,mBall,mToe,mHeel = self.getFkFeetBones(suffix)
        ez,origin,rot = getPlaneInfo(plane)
        order,lock = getLocks(toe, context)
        factor = 1.0/toe.length
        nFrames = len(frames)
        if mBall:
            for n,frame in enumerate(frames):
                scn.frame_set(frame)
                showProgress(n, frame, nFrames)
                zToe = getProjection(mToe.matrix.col[3], ez)
                zBall = getProjection(mBall.matrix.col[3], ez)
                if zToe > zBall:
                    pmat = self.offsetToeRotation(toe, ez, factor, order, lock, context)
                else:
                    pmat = getPoseMatrix(toe.matrix, toe)
                pmat = self.keepToeRotationNegative(pmat, scn)
                insertRotation(toe, pmat)
        else:
            for n,frame in enumerate(frames):
                scn.frame_set(frame)
                showProgress(n, frame, nFrames)
                dzToe = getProjection(toe.matrix.col[1], ez)
                if dzToe > 0:
                    pmat = self.offsetToeRotation(toe, ez, factor, order, lock, context)
                else:
                    pmat = getPoseMatrix(toe.matrix, toe)
                pmat = self.keepToeRotationNegative(pmat, scn)
                insertRotation(toe, pmat)


    def offsetToeRotation(self, toe, ez, factor, order, lock, context):
        from .retarget import correctMatrixForLocks
        from .fkik import getPoseMatrix

        mat = toe.matrix.to_3x3()
        y = mat.col[1]
        y -= ez.dot(y)*ez
        y.normalize()
        x = mat.col[0]
        x -= x.dot(y)*y
        x.normalize()
        z = x.cross(y)
        mat.col[0] = x
        mat.col[1] = y
        mat.col[2] = z
        gmat = mat.to_4x4()
        gmat.col[3] = toe.matrix.col[3]
        pmat = getPoseMatrix(gmat, toe)
        return correctMatrixForLocks(pmat, order, lock, toe, context.scene.McpUseLimits)


    def keepToeRotationNegative(self, pmat, scn):
        euler = pmat.to_3x3().to_euler('YZX')
        if euler.x > 0:
            pmat0 = pmat
            euler.x = 0
            pmat = euler.to_matrix().to_4x4()
            pmat.col[3] = pmat0.col[3]
        return pmat

#-------------------------------------------------------------
#   Floor
#-------------------------------------------------------------

class MHX_OT_FloorFoot(MhxPropsOperator, IsArmature, FrameRange, Feet):
    bl_idname = "mhx.floor_foot"
    bl_label = "Keep Feet Above Floor"
    bl_description = "Keep Feet Above Plane"
    bl_options = {'UNDO'}

    useLeft : BoolProperty(
        name="Left",
        description="Keep left foot above floor",
        default=True)

    useRight : BoolProperty(
        name="Right",
        description="Keep right foot above floor",
        default=True)

    useHips : BoolProperty(
        name="Hips",
        description="Also adjust character COM when keeping feet above floor",
        default=True)

    def draw(self, context):
        self.layout.prop(self, "useLeft")
        self.layout.prop(self, "useRight")
        self.layout.prop(self, "useHips")
        FrameRange.draw(self, context)


    def run(self, context):
        startProgress("Keep feet above floor")
        self.findTarget(context, context.object)
        scn = context.scene
        rig,plane = getRigAndPlane(context)
        try:
            useIk = rig["MhaLegIk_L"] or rig["MhaLegIk_R"]
        except KeyError:
            useIk = False
        frames = self.getActiveFrames()
        if useIk:
            self.floorIkFoot(rig, plane, scn, frames)
        else:
            self.floorFkFoot(rig, plane, scn, frames)
        raise MocapMessage("Feet kept above floor")


    def floorFkFoot(self, rig, plane, scn, frames):
        hips = self.getBone("hips")
        lFoot,lToe,lmBall,lmToe,lmHeel = self.getFkFeetBones(".L")
        rFoot,rToe,rmBall,rmToe,rmHeel = self.getFkFeetBones(".R")
        ez,origin,rot = getPlaneInfo(plane)

        nFrames = len(frames)
        for n,frame in enumerate(frames):
            scn.frame_set(frame)
            updateScene()
            offset = 0
            if self.useLeft:
                offset = self.getFkOffset(rig, ez, origin, lFoot, lToe, lmBall, lmToe, lmHeel)
            if self.useRight:
                rOffset = self.getFkOffset(rig, ez, origin, rFoot, rToe, rmBall, rmToe, rmHeel)
                if rOffset > offset:
                    offset = rOffset
            showProgress(n, frame, nFrames)
            if offset > 0:
                addOffset(hips, offset, ez)


    def getFkOffset(self, rig, ez, origin, foot, toe, mBall, mToe, mHeel):
        if mBall:
            offset = toeOffset = getHeadOffset(mToe, ez, origin)
            ballOffset = getHeadOffset(mBall, ez, origin)
            if ballOffset > offset:
                offset = ballOffset
            heelOffset = getHeadOffset(mHeel, ez, origin)
            if heelOffset > offset:
                offset = heelOffset
        elif toe:
            offset = getTailOffset(toe, ez, origin)
            ballOffset = getHeadOffset(toe, ez, origin)
            if ballOffset > offset:
                offset = ballOffset
            ball = toe.matrix.col[3]
            y = toe.matrix.col[1]
            heel = ball - y*foot.length
            heelOffset = getOffset(heel, ez, origin)
            if heelOffset > offset:
                offset = heelOffset
        else:
            offset = 0

        return offset


    def floorIkFoot(self, rig, plane, scn, frames):
        root = rig.pose.bones["root"]
        lleg = rig.pose.bones["foot.ik.L"]
        rleg = rig.pose.bones["foot.ik.R"]
        ez,origin,rot = getPlaneInfo(plane)

        self.fillKeyFrames(lleg, rig, frames, 3, mode='location')
        self.fillKeyFrames(rleg, rig, frames, 3, mode='location')
        if self.useHips:
            self.fillKeyFrames(root, rig, frames, 3, mode='location')

        nFrames = len(frames)
        for n,frame in enumerate(frames):
            scn.frame_set(frame)
            showProgress(n, frame, nFrames)

            if self.useLeft:
                lOffset = self.getIkOffset(rig, ez, origin, lleg)
                if lOffset > 0:
                    addOffset(lleg, lOffset, ez)
            else:
                lOffset = 0
            if self.useRight:
                rOffset = self.getIkOffset(rig, ez, origin, rleg)
                if rOffset > 0:
                    addOffset(rleg, rOffset, ez)
            else:
                rOffset = 0

            hOffset = min(lOffset,rOffset)
            if hOffset > 0 and self.useHips:
                addOffset(root, hOffset, ez)


    def fillKeyFrames(self, pb, rig, frames, nIndices, mode='rotation'):
        for idx in range(nIndices):
            fcu = findBoneFCurve(pb, self.rig, idx, mode)
            if fcu is None:
                return
            for frame in frames:
                y = fcu.evaluate(frame)
                fcu.keyframe_points.insert(frame, y, options={'FAST'})


    def getIkOffset(self, rig, ez, origin, leg):
        offset = getHeadOffset(leg, ez, origin)
        tailOffset = getTailOffset(leg, ez, origin)
        if tailOffset > offset:
            offset = tailOffset
        return offset

        foot = rig.pose.bones["foot.rev" + suffix]
        toe = rig.pose.bones["toe.rev" + suffix]

        ballOffset = getTailOffset(toe, ez, origin)
        if ballOffset > offset:
            offset = ballOffset

        ball = foot.matrix.col[3]
        y = toe.matrix.col[1]
        heel = ball + y*foot.length
        heelOffset = getOffset(heel, ez, origin)
        if heelOffset > offset:
            offset = heelOffset

        return offset

#----------------------------------------------------------
#   Utilities
#----------------------------------------------------------

def findBoneFCurve(pb, rig, idx, mode='rotation'):
    if rig.animation_data is None:
        return None
    act = rig.animation_data.action
    if act is None:
        return None
    if mode == 'rotation':
        if pb.rotation_mode == 'QUATERNION':
            mode = "rotation_quaternion"
        else:
            mode = "rotation_euler"
    path = 'pose.bones["%s"].%s' % (pb.name, mode)
    for fcu in act.fcurves:
        if (fcu.data_path == path and
            fcu.array_index == idx):
            return fcu
    print('F-curve "%s" not found.' % path)
    return None

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MHX_OT_LimbsBendPositive,
    MHX_OT_TransferToFk,
    MHX_OT_TransferToIk,
    MHX_OT_ClearAnimation,
    MHX_OT_ClearPoleTargets,
    MHX_OT_OffsetToes,
    MHX_OT_FloorFoot,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

