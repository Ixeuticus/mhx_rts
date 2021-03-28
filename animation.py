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
from .fkik import Snapper, Basic, Updater

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

class Bender(Basic):
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
            pb = self.getBone("forearm.fk.L")
            self.minimizeFCurve(pb, 0, frames)
            pb = self.getBone("forearm.fk.R")
            self.minimizeFCurve(pb, 0, frames)
        if self.useKnees:
            pb = self.getBone("shin.fk.L")
            self.minimizeFCurve(pb, 0, frames)
            pb = self.getBone("shin.fk.R")
            self.minimizeFCurve(pb, 0, frames)


    def minimizeFCurve(self, pb, idx, frames):
        if pb is None:
            return
        fcu = self.findBoneFCurve(pb, idx)
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


class MHX_OT_LimbsBendPositive(HidePropsOperator, Bender, FrameRange):
    bl_idname = "mhx.limbs_bend_positive"
    bl_label = "Bend Limbs Positive"
    bl_description = "Ensure that limbs' X rotation is positive."
    bl_options = {'UNDO'}

    def draw(self, context):
        Bender.draw(self, context)
        FrameRange.draw(self, context)

    def run(self, context):
        frames = self.getActiveFrames()
        self.limbsBendPositive(frames)
        print("Limbs bent positive")


#-------------------------------------------------------------
#
#-------------------------------------------------------------

class MHX_OT_EnforceConstraints(HidePropsOperator, Basic, FrameRange):
    bl_idname = "mhx.enforce_constraints"
    bl_label = "Enforce Constraints"
    bl_description = "Keep all rotations within constraints"
    bl_options = {'UNDO'}

    def draw(self, context):
        FrameRange.draw(self, context)

    def run(self, context):
        frames = self.getActiveFrames()
        for pb in self.rig.pose.bones:
            cns = self.getLimitRotConstraint(pb)
            if cns and pb.rotation_mode != 'QUATERNION':
                for idx in range(3):
                    char = chr(ord("x")+idx)
                    if getattr(cns, "use_limit_%s" % char):
                        ymin = getattr(cns, "min_%s" % char)
                        ymax = getattr(cns, "max_%s" % char)
                        self.constrainFCurve(pb, idx, ymin, ymax, frames)
        print("F-curves constrained")


    def getLimitRotConstraint(self, pb):
        for cns in pb.constraints:
            if cns.type == 'LIMIT_ROTATION':
                return cns
        return None


    def constrainFCurve(self, pb, idx, ymin, ymax, frames):
        fcu = self.findBoneFCurve(pb, idx)
        if fcu is None:
            return
        t0 = frames[0]
        t1 = frames[-1]
        for kp in fcu.keyframe_points:
            t = kp.co[0]
            if t >= t0 and t <= t1:
                y = kp.co[1]
                if y < ymin:
                    kp.co[1] = ymin
                elif y > ymax:
                    kp.co[1] = ymax

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

    def draw(self, context):
        self.layout.prop(self, "useArms")
        self.layout.prop(self, "useLegs")


    def setMhxIk(self, value):
        ikLayers = []
        fkLayers = []
        if self.useArms:
            self.amt["MhaArmIk_L"] = value
            self.amt["MhaArmIk_R"] = value
            ikLayers += [L_LARMIK, L_RARMIK]
            fkLayers += [L_LARMFK, L_RARMFK]
        if self.useLegs:
            self.amt["MhaLegIk_L"] = value
            self.amt["MhaLegIk_R"] = value
            ikLayers += [L_LLEGIK, L_RLEGIK]
            fkLayers += [L_LLEGFK, L_RLEGFK]
        if value:
            onLayers = ikLayers
            offLayers = fkLayers
        else:
            onLayers = fkLayers
            offLayers = ikLayers
        for n in onLayers:
            self.state[n] = self.rig.data.layers[n] = True
        for n in offLayers:
            self.state[n] = self.rig.data.layers[n] = False

#------------------------------------------------------------------------
#   Transfer FK - IK
#------------------------------------------------------------------------

class MHX_OT_TransferToFk(Transferer, HidePropsOperator, Bender, FrameRange):
    bl_idname = "mhx.transfer_to_fk"
    bl_label = "Transfer IK => FK"
    bl_description = "Transfer IK animation to FK bones"
    bl_options = {'UNDO'}

    def draw(self, context):
        Transferer.draw(self, context)
        FrameRange.draw(self, context)

    def run(self, context):
        startProgress("Transfer to FK")
        time1 = time.perf_counter()
        self.transferMhxToFk(context)
        time2 = time.perf_counter()
        raise MhxMessage("Transfer to FK completed\nin %1f seconds" % (time2-time1))


    def transferMhxToFk(self, context):
        lArmSnapIk,lArmCnsIk = self.getSnapBones("ArmIK", "L")
        lArmSnapFk,lArmCnsFk = self.getSnapBones("ArmFK", "L")
        rArmSnapIk,rArmCnsIk = self.getSnapBones("ArmIK", "R")
        rArmSnapFk,rArmCnsFk = self.getSnapBones("ArmFK", "R")
        lLegSnapIk,lLegCnsIk = self.getSnapBones("LegIK", "L")
        lLegSnapFk,lLegCnsFk = self.getSnapBones("LegFK", "L")
        rLegSnapIk,rLegCnsIk = self.getSnapBones("LegIK", "R")
        rLegSnapFk,rLegCnsFk = self.getSnapBones("LegFK", "R")

        scn = context.scene
        self.auto = True
        self.setMhxIk(1.0)
        lLegIkToAnkle = self.amt["MhaLegIkToAnkle_L"]
        rLegIkToAnkle = self.amt["MhaLegIkToAnkle_R"]
        frames = self.getActiveFrames()
        nFrames = len(frames)

        for n,frame in enumerate(frames):
            showProgress(n, frame, nFrames)
            self.setFrame(scn, frame)
            if self.useArms:
                self.snapFkArm(lArmSnapFk, lArmSnapIk)
                self.snapFkArm(rArmSnapFk, rArmSnapIk)
            if self.useLegs:
                self.snapFkLeg(lLegSnapFk, lLegSnapIk, lLegIkToAnkle)
                self.snapFkLeg(rLegSnapFk, rLegSnapIk, rLegIkToAnkle)
        self.setMhxIk(0.0)


class MHX_OT_TransferToIk(Transferer, HidePropsOperator, FrameRange):
    bl_idname = "mhx.transfer_to_ik"
    bl_label = "Transfer FK => IK"
    bl_description = "Transfer FK animation to IK bones"
    bl_options = {'UNDO'}

    def draw(self, context):
        Transferer.draw(self, context)
        FrameRange.draw(self, context)

    def run(self, context):
        startProgress("Transfer to IK")
        time1 = time.perf_counter()
        self.transferMhxToIk(context)
        time2 = time.perf_counter()
        raise MhxMessage("Transfer to IK completed\nin %1f seconds" % (time2-time1))


    def transferMhxToIk(self, context):
        lArmSnapIk,lArmCnsIk = self.getSnapBones("ArmIK", "L")
        lArmSnapFk,lArmCnsFk = self.getSnapBones("ArmFK", "L")
        rArmSnapIk,rArmCnsIk = self.getSnapBones("ArmIK", "R")
        rArmSnapFk,rArmCnsFk = self.getSnapBones("ArmFK", "R")
        lLegSnapIk,lLegCnsIk = self.getSnapBones("LegIK", "L")
        lLegSnapFk,lLegCnsFk = self.getSnapBones("LegFK", "L")
        rLegSnapIk,rLegCnsIk = self.getSnapBones("LegIK", "R")
        rLegSnapFk,rLegCnsFk = self.getSnapBones("LegFK", "R")

        scn = context.scene
        self.auto = True
        self.setMhxIk(0.0)
        lLegIkToAnkle = self.amt["MhaLegIkToAnkle_L"]
        rLegIkToAnkle = self.amt["MhaLegIkToAnkle_R"]
        frames = self.getActiveFrames()
        nFrames = len(frames)
        for n,frame in enumerate(frames):
            showProgress(n, frame, nFrames)
            self.setFrame(scn, frame)
            if self.useArms:
                self.snapIkArm(lArmSnapFk, lArmSnapIk)
                self.snapIkArm(rArmSnapFk, rArmSnapIk)
            if self.useLegs:
                self.snapIkLeg(lLegSnapFk, lLegSnapIk, lLegIkToAnkle)
                self.snapIkLeg(rLegSnapFk, rLegSnapIk, rLegIkToAnkle)
        self.setMhxIk(1.0)

#------------------------------------------------------------------------
#   Clear animation
#------------------------------------------------------------------------

class MHX_OT_ClearAnimation(HidePropsOperator):
    bl_idname = "mhx.clear_animation"
    bl_label = "Clear Animation"
    bl_description = "Clear Animation For FK or IK Bones"
    bl_options = {'UNDO'}

    clearArmFK : BoolProperty(
        name = "Clear FK Arm",
        description = "Clear Arm FK animation",
        default = False)

    clearArmIK : BoolProperty(
        name = "Clear IK Arm",
        description = "Clear Arm IK animation",
        default = False)

    clearLegFK : BoolProperty(
        name = "Clear FK Leg",
        description = "Clear Leg FK animation",
        default = False)

    clearLegIK : BoolProperty(
        name = "Clear IK Leg",
        description = "Clear Leg IK animation",
        default = False)

    def draw(self, context):
        self.layout.prop(self, "clearArmFK")
        self.layout.prop(self, "clearLegFK")
        self.layout.prop(self, "clearArmIK")
        self.layout.prop(self, "clearLegIK")

    def run(self, context):
        from .fkik import SnapBones
        startProgress("Clear animation")
        rig = context.object
        act = self.getCurrentAction(rig)
        bnames = []
        if self.clearArmFK:
            bnames += SnapBones["ArmFK"]
        if self.clearArmIK:
            bnames += SnapBones["ArmIK"]
        if self.clearLegFK:
            bnames += SnapBones["LegFK"]
        if self.clearLegIK:
            bnames += SnapBones["LegIK"]
        lBnames = [bname+".L" for bname in bnames]
        rBnames = [bname+".R" for bname in bnames]
        nfcus = self.removeFcurves(act, lBnames+rBnames)
        if nfcus:
            msg = "Animation cleared"
        else:
            msg = "No F-curves removed"
        raise MhxMessage(msg)

    def getCurrentAction(self, rig):
        if not rig.animation_data:
            raise MhxError("Rig has no animation data")
        act = rig.animation_data.action
        if not act:
            raise MhxError("Rig has no action")
        return act

    def removeFcurves(self, act, bnames):
        fcus = []
        for fcu in act.fcurves:
            words = fcu.data_path.split('"')
            if (words[0] == "pose.bones[" and
                words[1] in bnames):
                fcus.append(fcu)
        ncurves = len(fcus)
        for fcu in fcus:
            act.fcurves.remove(fcu)
        return ncurves

#-------------------------------------------------------------
#   Toe below ball
#-------------------------------------------------------------

class FeetOperator(HidePropsOperator, Basic):

    def getFkFeetBones(self, suffix):
        foot = self.getBone("foot.fk" + suffix)
        toe = self.getBone("toe.fk" + suffix)
        try:
            mBall = self.getBone("ball.marker" + suffix)
            mToe = self.getBone("toe.marker" + suffix)
            mHeel = self.getBone("heel.marker" + suffix)
        except KeyError:
            mBall = mToe = mHeel = None
        return foot,toe,mBall,mToe,mHeel


    def getRigAndPlane(self, context):
        rig = None
        plane = None
        for ob in context.view_layer.objects:
            if ob.select_get():
                if ob.type == 'ARMATURE':
                    if rig:
                        raise MhxError("Two armatures selected: %s and %s" % (rig.name, ob.name))
                    else:
                        rig = ob
                elif ob.type == 'MESH':
                    if plane:
                        raise MhxError("Two meshes selected: %s and %s" % (plane.name, ob.name))
                    else:
                        plane = ob
        if rig is None:
            raise MhxError("No rig selected")
        return rig,plane


    def getPlaneInfo(self):
        if self.plane is None:
            ez = Vector((0,0,1))
            origin = Vector((0,0,0))
            rot = Matrix()
        else:
            mat = self.plane.matrix_world.to_3x3().normalized()
            ez = mat.col[2]
            origin = self.plane.location
            rot = mat.to_4x4()
        return ez,origin,rot


    def addOffset(self, pb, offset, ez):
        gmat = pb.matrix.copy()
        x,y,z = offset*ez
        gmat.col[3] += Vector((x,y,z,0))
        pmat = self.getPoseMatrix(gmat, pb)
        self.insertLocation(pb, pmat)


class MHX_OT_OffsetToes(FeetOperator, FrameRange, Snapper):
    bl_idname = "mhx.offset_toes"
    bl_label = "Offset Toes"
    bl_description = "Keep toes below the ball of the feet"
    bl_options = {'UNDO'}

    def draw(self, context):
        FrameRange.draw(self, context)

    def run(self, context):
        self.auto = True
        self.rig, self.plane = self.getRigAndPlane(context)
        try:
            useIk = self.rig["MhaLegIk_L"] or self.rig["MhaLegIk_R"]
        except KeyError:
            useIk = False
        if useIk:
            raise MhxError("Toe Below Ball only for FK feet")

        startProgress("Keep toes down")
        frames = self.getActiveFrames()
        print("Left toe")
        self.toeBelowBall(context, frames, ".L")
        print("Right toe")
        self.toeBelowBall(context, frames, ".R")
        raise MhxMessage("Toes kept down")


    def toeBelowBall(self, context, frames, suffix):
        scn = context.scene
        foot,toe,mBall,mToe,mHeel = self.getFkFeetBones(suffix)
        ez,origin,rot = self.getPlaneInfo()
        nFrames = len(frames)
        if mBall:
            for n,frame in enumerate(frames):
                self.setFrame(scn, frame)
                showProgress(n, frame, nFrames)
                zToe = getProjection(mToe.matrix.col[3], ez)
                zBall = getProjection(mBall.matrix.col[3], ez)
                if zToe > zBall:
                    gmat = self.offsetToeRotation(toe, ez)
                else:
                    gmat = toe.matrix
                pmat = self.getPoseMatrix(gmat, toe)
                pmat = self.keepToeRotationNegative(pmat, toe)
                self.insertRotation(toe, pmat)
        else:
            for n,frame in enumerate(frames):
                self.setFrame(scn, frame)
                showProgress(n, frame, nFrames)
                dzToe = getProjection(toe.matrix.col[1], ez)
                if dzToe > 0:
                    gmat = self.offsetToeRotation(toe, ez)
                else:
                    gmat = toe.matrix
                pmat = self.getPoseMatrix(gmat, toe)
                pmat = self.keepToeRotationNegative(pmat, toe)
                self.insertRotation(toe, pmat)


    def offsetToeRotation(self, toe, ez):
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
        return self.getPoseMatrix(gmat, toe)


    def keepToeRotationNegative(self, pmat, toe):
        euler = pmat.to_3x3().to_euler(toe.rotation_mode)
        if euler.x > 0:
            pmat0 = pmat
            euler.x = 0
            pmat = euler.to_matrix().to_4x4()
            pmat.col[3] = pmat0.col[3]
        return pmat


def getProjection(vec, ez):
    return ez.dot(Vector(vec[:3]))


def getOffset(point, ez, origin):
    vec = Vector(point[:3]) - origin
    offset = -ez.dot(vec)
    return offset


def getHeadOffset(pb, ez, origin):
    head = pb.matrix.col[3]
    return getOffset(head, ez, origin)


def getTailOffset(pb, ez, origin):
    head = pb.matrix.col[3]
    y = pb.matrix.col[1]
    tail = head + y*pb.length
    return getOffset(tail, ez, origin)

#-------------------------------------------------------------
#   Floor
#-------------------------------------------------------------

class MHX_OT_FloorFoot(FeetOperator, FrameRange, Updater):
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
        self.auto = True
        scn = context.scene
        self.rig, self.plane = self.getRigAndPlane(context)
        try:
            useIk = (self.amt["MhaLegIk_L"] or self.amt["MhaLegIk_R"])
        except KeyError:
            useIk = False
        frames = self.getActiveFrames()
        print("UIK", useIk)
        if useIk:
            self.floorIkFoot(scn, frames)
        else:
            self.floorFkFoot(scn, frames)
        raise MhxMessage("Feet kept above floor")


    def floorFkFoot(self, scn, frames):
        hip = self.getBone("hip")
        lFoot,lToe,lmBall,lmToe,lmHeel = self.getFkFeetBones(".L")
        rFoot,rToe,rmBall,rmToe,rmHeel = self.getFkFeetBones(".R")
        ez,origin,rot = self.getPlaneInfo()

        nFrames = len(frames)
        for n,frame in enumerate(frames):
            self.setFrame(scn, frame)
            offset = 0
            if self.useLeft:
                offset = self.getFkOffset(ez, origin, lFoot, lToe, lmBall, lmToe, lmHeel)
            if self.useRight:
                rOffset = self.getFkOffset(ez, origin, rFoot, rToe, rmBall, rmToe, rmHeel)
                if rOffset > offset:
                    offset = rOffset
            showProgress(n, frame, nFrames)
            if offset > 0:
                self.addOffset(hip, offset, ez)


    def getFkOffset(self, ez, origin, foot, toe, mBall, mToe, mHeel):
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


    def floorIkFoot(self, scn, frames):
        hip = self.rig.pose.bones["hip"]
        lleg = self.rig.pose.bones["foot.ik.L"]
        rleg = self.rig.pose.bones["foot.ik.R"]
        ez,origin,rot = self.getPlaneInfo()

        self.fillKeyFrames(lleg, frames, 3, mode='location')
        self.fillKeyFrames(rleg, frames, 3, mode='location')
        if self.useHips:
            self.fillKeyFrames(hip, frames, 3, mode='location')

        nFrames = len(frames)
        for n,frame in enumerate(frames):
            self.setFrame(scn, frame)
            showProgress(n, frame, nFrames)

            if self.useLeft:
                lOffset = self.getIkOffset(ez, origin, lleg)
                if lOffset > 0:
                    self.addOffset(lleg, lOffset, ez)
            else:
                lOffset = 0
            if self.useRight:
                rOffset = self.getIkOffset(ez, origin, rleg)
                if rOffset > 0:
                    self.addOffset(rleg, rOffset, ez)
            else:
                rOffset = 0

            hOffset = min(lOffset,rOffset)
            if hOffset > 0 and self.useHips:
                self.addOffset(hip, hOffset, ez)


    def fillKeyFrames(self, pb, frames, nIndices, mode='rotation'):
        for idx in range(nIndices):
            fcu = self.findBoneFCurve(pb, idx, mode)
            if fcu is None:
                return
            for frame in frames:
                y = fcu.evaluate(frame)
                fcu.keyframe_points.insert(frame, y, options={'FAST'})


    def getIkOffset(self, ez, origin, leg):
        offset = getHeadOffset(leg, ez, origin)
        tailOffset = getTailOffset(leg, ez, origin)
        if tailOffset > offset:
            offset = tailOffset
        return offset

        foot = self.rig.pose.bones["foot.rev" + suffix]
        toe = self.rig.pose.bones["toe.rev" + suffix]

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
#   Initialize
#----------------------------------------------------------

classes = [
    MHX_OT_EnforceConstraints,
    MHX_OT_LimbsBendPositive,
    MHX_OT_TransferToFk,
    MHX_OT_TransferToIk,
    MHX_OT_ClearAnimation,
    MHX_OT_OffsetToes,
    MHX_OT_FloorFoot,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

