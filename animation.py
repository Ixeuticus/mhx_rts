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
from mathutils import Vector, Matrix, Euler, Quaternion
from bpy.props import *
from .utils import *
from .layers import *
from .fkik import Snapper, Basic, Updater, FootSnapper

#-------------------------------------------------------------
#   Frame range
#-------------------------------------------------------------

class FrameRange(Updater):
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
        if not frames:
            return frames
        frames.sort()
        while frames[0] < self.startFrame:
            frames = frames[1:]
        frames.reverse()
        while frames[0] > self.endFrame:
            frames = frames[1:]
        frames.reverse()
        return frames


    def setInterpolation(self):
        if not self.rig.animation_data:
            return
        act = self.rig.animation_data.action
        if not act:
            return
        for fcu in act.fcurves:
            for pt in fcu.keyframe_points:
                pt.interpolation = 'LINEAR'
            fcu.extrapolation = 'CONSTANT'

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
        checkVisible(context.object)
        frames = self.getActiveFrames()
        self.limbsBendPositive(frames)
        print("Limbs bent positive")

#-------------------------------------------------------------
#   Remove keyframes from frame 0
#-------------------------------------------------------------

class MHX_OT_RemoveFrameZero(MhxOperator):
    bl_idname = "mhx.remove_frame_zero"
    bl_label = "Remove Frame Zero"
    bl_description = "Remove all keys from frame 0"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        checkVisible(rig)
        if rig.animation_data is None:
            return None
        act = rig.animation_data.action
        if act is None:
            return None
        for fcu in act.fcurves:
            kps = [kp for kp in fcu.keyframe_points if kp.co[0] == 0.0]
            for kp in kps:
                fcu.keyframe_points.remove(kp, fast=True)

#-------------------------------------------------------------
#   Remove unused F-curves
#-------------------------------------------------------------

class MHX_OT_RemoveUnusedFcurves(MhxOperator):
    bl_idname = "mhx.remove_unused_fcurves"
    bl_label = "Remove Unused F-curves"
    bl_description = "Remove unused f-curves"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        checkVisible(rig)
        if rig.animation_data is None:
            return None
        act = rig.animation_data.action
        if act is None:
            return None
        deletes = []
        for fcu in act.fcurves:
            channel = fcu.data_path.rsplit(".")[-1]
            if channel == "rotation_euler":
                if self.trivial(fcu, 0.0):
                    deletes.append(fcu)
            elif channel == "rotation_quaternion":
                if fcu.array_index == 0 and self.trivial(fcu, 1.0):
                    deletes.append(fcu)
                elif self.trivial(fcu, 0.0):
                    deletes.append(fcu)
        for fcu in deletes:
            act.fcurves.remove(fcu)


    def trivial(self, fcu, default):
        for kp in fcu.keyframe_points:
            if abs(kp.co[1] - default) > 1e-6:
                return False
        return True

#-------------------------------------------------------------
#
#-------------------------------------------------------------

class LimitEnforcer:
    def run(self, context):
        checkVisible(self.rig)
        self.initSettings(context)
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
            for idx in range(3):
                if pb.lock_rotation[idx]:
                    self.constrainFCurve(pb, idx, 0.0, 0.0, frames)
        extraLocks = {
            "toe.fk.L" : (1, 2),
            "toe.fk.R" : (1, 2),
        }
        for bname, locks in extraLocks.items():
            pb = self.getBone(bname)
            for idx in locks:
                self.constrainFCurve(pb, idx, 0.0, 0.0, frames)
        self.setInterpolation()
        print("Limits enforced")


    def getLimitRotConstraint(self, pb):
        for cns in pb.constraints:
            if cns.type == 'LIMIT_ROTATION':
                return cns
        return None


class MHX_OT_EnforceLimits(LimitEnforcer, HideOperator, Basic):
    bl_idname = "mhx.enforce_limits"
    bl_label = "Enforce Limits"
    bl_description = "Keep all rotations within limits"
    bl_options = {'UNDO'}

    def getActiveFrames(self):
        return None

    def initSettings(self, context):
        scn = context.scene
        self.auto = scn.tool_settings.use_keyframe_insert_auto
        self.frame = scn.frame_current

    def constrainFCurve(self, pb, idx, ymin, ymax, frames):
        value = pb.rotation_euler[idx]
        pb.rotation_euler[idx] = min(ymax, max(ymin, value))
        if self.auto or isKeyed(self.rig, pb, "rotation_euler"):
            pb.keyframe_insert("rotation_euler", frame=self.frame, group=pb.name)

    def setInterpolation(self):
        pass


class MHX_OT_EnforceAllLimits(LimitEnforcer, HidePropsOperator, Basic, FrameRange):
    bl_idname = "mhx.enforce_all_limits"
    bl_label = "Enforce All Limits"
    bl_description = "Keep all rotations within limits for active action"
    bl_options = {'UNDO'}

    def draw(self, context):
        FrameRange.draw(self, context)

    def initSettings(self, context):
        pass

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
#   Transfer FK - IK
#-------------------------------------------------------------

class Transferer:
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
            self.rig.MhaArmIk_L = value
            self.rig.MhaArmIk_R = value
            ikLayers += [L_LARMIK, L_RARMIK]
            fkLayers += [L_LARMFK, L_RARMFK]
        if self.useLegs:
            self.rig.MhaLegIk_L = value
            self.rig.MhaLegIk_R = value
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
#   Transfer to FK
#------------------------------------------------------------------------

class MHX_OT_TransferToFk(Transferer, FootSnapper, HidePropsOperator, Bender, FrameRange):
    bl_idname = "mhx.transfer_to_fk"
    bl_label = "Transfer IK => FK"
    bl_description = "Transfer IK animation to FK bones"
    bl_options = {'UNDO'}

    def draw(self, context):
        Transferer.draw(self, context)
        FrameRange.draw(self, context)

    def run(self, context):
        checkVisible(context.object)
        startProgress("Transfer to FK")
        time1 = time.perf_counter()
        self.transferMhxToFk(context)
        self.setInterpolation()
        time2 = time.perf_counter()
        displayMessage("Transfer to FK completed\nin %1f seconds" % (time2-time1))


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
        lLegIkToAnkle = self.rig.MhaLegIkToAnkle_L
        rLegIkToAnkle = self.rig.MhaLegIkToAnkle_R
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

#------------------------------------------------------------------------
#   Transfer to IK
#------------------------------------------------------------------------

class MHX_OT_TransferToIk(Transferer, FootSnapper, HidePropsOperator, FrameRange):
    bl_idname = "mhx.transfer_to_ik"
    bl_label = "Transfer FK => IK"
    bl_description = "Transfer FK animation to IK bones"
    bl_options = {'UNDO'}

    def draw(self, context):
        Transferer.draw(self, context)
        FootSnapper.draw(self, context)
        FrameRange.draw(self, context)

    def run(self, context):
        checkVisible(context.object)
        startProgress("Transfer to IK")
        time1 = time.perf_counter()
        self.transferMhxToIk(context)
        self.setInterpolation()
        time2 = time.perf_counter()
        displayMessage("Transfer to IK completed\nin %1f seconds" % (time2-time1))


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
        lLegIkToAnkle = self.rig.MhaLegIkToAnkle_L
        rLegIkToAnkle = self.rig.MhaLegIkToAnkle_R
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
        rig = context.object
        checkVisible(rig)
        startProgress("Clear animation")
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
        displayMessage(msg)

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
#   Feet operations
#-------------------------------------------------------------

class Footer(Basic):

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

    useMarkers : BoolProperty(
        name = "Markers",
        description = "Use markers to determine foot location",
        default = True)

    def draw(self, context):
        self.layout.prop(self, "useLeft")
        self.layout.prop(self, "useRight")
        self.layout.prop(self, "useHips")
        self.layout.prop(self, "useMarkers")
        FrameRange.draw(self, context)


    def getMarkers(self, suffix):
        try:
            mBall = self.getBone("ball.marker.%s" % suffix)
            mToe = self.getBone("toe.marker.%s" % suffix)
            mHeel = self.getBone("heel.marker.%s" % suffix)
            return mBall,mToe,mHeel
        except KeyError:
            return None


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

#-------------------------------------------------------------
#   Offset toes
#-------------------------------------------------------------

class MHX_OT_SetConstraints(MhxOperator):
    bl_idname = "mhx.set_constraints"
    bl_label = "Set Constraints"
    bl_description = "Add aggressive constraints to the feet"
    bl_options = {'UNDO'}

    def run(self, context):
        locks = {
            "toe.fk" : [1, 2],
            "foot.fk" : [1],
            "foot.rev" : [1, 2],
        }
        limits = {
            "toe.fk" : { "max_x" : 0, "min_y" : 0, "max_y" : 0, "min_z" : 0, "max_z" : 0 }
        }

        rig = context.object
        checkVisible(rig)
        for suffix in ["L", "R"]:
            for bname,lock in locks.items():
                pb = rig.pose.bones["%s.%s" % (bname % suffix)]
                for idx in lock:
                    pb.lock_rotation[idx] = True
            for bname,limit in limits.items():
                pb = rig.pose.bones["%s.%s" % (bname % suffix)]
                for cns in pb.constraints:
                    if cns.type == 'LIMIT_ROTATION':
                        for attr,val in limit.items():
                            setattr(cns, attr, val)

#-------------------------------------------------------------
#   Utilities
#-------------------------------------------------------------


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

class MHX_OT_ShiftBoneFCurves(HidePropsOperator, FrameRange, Basic):
    bl_idname = "mhx.shift_animation"
    bl_label = "Shift Animation"
    bl_description = "Shift the animation globally for selected boens"
    bl_options = {'UNDO'}

    def run(self, context):
        checkVisible(self.rig)
        startProgress("Shift animation")
        self.auto = True
        scn = context.scene
        frames = [scn.frame_current] + self.getActiveFrames()
        nFrames = len(frames)
        if not self.rig.animation_data:
            return
        act = self.rig.animation_data.action
        if not act:
            return
        basemats, useLoc = self.getBaseMatrices(act, frames, False)

        deltaMat = {}
        orders = {}
        locks = {}
        for bname,bmats in basemats.items():
            pb = self.rig.pose.bones[bname]
            bmat = bmats[0]
            deltaMat[pb.name] = pb.matrix_basis @ bmat.inverted()

        for n,frame in enumerate(frames):
            self.setFrame(scn, frame)
            showProgress(n, frame, nFrames)
            for bname,bmats in basemats.items():
                pb = self.rig.pose.bones[bname]
                mat = deltaMat[pb.name] @ bmats[n]
                if useLoc[bname]:
                    self.insertLocation(pb, mat)
                self.insertRotation(pb, mat)

        displayMessage("Animation shifted")


    def getBaseMatrices(self, act, frames, useAll):
        fcurves = { "location" : {}, "rotation_euler" : {}, "rotation_quaternion" : {} }
        nidxs = { "location" : 3, "rotation_euler" : 3, "rotation_quaternion" : 4 }
        for fcu in act.fcurves:
            words = fcu.data_path.split('"')
            if words[0] != "pose.bones[":
                continue
            bname = words[1]
            channel = words[2].rsplit(".")[-1]
            if (channel in fcurves.keys() and
                bname in self.rig.pose.bones.keys()):
                pb = self.rig.pose.bones[bname]
            else:
                continue
            if pb.bone.select:
                if bname not in fcurves[channel].keys():
                    fcurves[channel][bname] = nidxs[channel]*[None]
                fcurves[channel][bname][fcu.array_index] = fcu

        basemats = {}
        useLoc = {}
        for bname,fcus in fcurves["rotation_euler"].items():
            useLoc[bname] = False
            order = self.rig.pose.bones[bname].rotation_mode
            fcu0,fcu1,fcu2 = fcus
            rmats = basemats[bname] = []
            for frame in frames:
                euler = Euler((self.getValue(fcu0, frame, 0),self.getValue(fcu1, frame, 0), self.getValue(fcu2, frame, 0)), order)
                rmats.append(euler.to_matrix().to_4x4())

        for bname,fcus in fcurves["rotation_quaternion"].items():
            useLoc[bname] = False
            fcu0,fcu1,fcu2,fcu3 = fcus
            rmats = basemats[bname] = []
            for frame in frames:
                quat = Quaternion((self.getValue(fcu0, frame, 1), self.getValue(fcu1, frame, 0), self.getValue(fcu2, frame, 0), self.getValue(fcu3, frame, 0)))
                rmats.append(quat.to_matrix().to_4x4())

        for bname,fcus in fcurves["location"].items():
            useLoc[bname] = True
            fcu0,fcu1,fcu2 = fcus
            tmats = []
            for frame in frames:
                loc = (self.getValue(fcu0, frame, 0),self.getValue(fcu1, frame, 0), self.getValue(fcu2, frame, 0))
                tmats.append(Matrix.Translation(loc))
            if bname in basemats.keys():
                rmats = basemats[bname]
                mats = []
                for tmat,rmat in zip(tmats, rmats):
                    mats.append( tmat @ rmat )
                basemats[bname] = mats
            else:
                basemats[bname] = tmats

        return basemats, useLoc


    def getValue(self, fcu, frame, default):
        return (fcu.evaluate(frame) if fcu else default)

#-------------------------------------------------------------
#   Floor FK foot
#-------------------------------------------------------------

class MHX_OT_FloorFkFoot(HidePropsOperator, Footer, FrameRange):
    bl_idname = "mhx.floor_fk_feet"
    bl_label = "Keep FK Feet Above Floor"
    bl_description = "Keep FK Feet Above Zero Plane"
    bl_options = {'UNDO'}

    def run(self, context):
        startProgress("Keep feet above floor")
        self.auto = True
        scn = context.scene
        self.rig, self.plane = self.getRigAndPlane(context)
        checkVisible(self.rig)
        frames = self.getActiveFrames()
        self.floorFkFoot(scn, frames)
        self.setInterpolation()
        displayMessage("FK Feet kept above floor")


    def floorFkFoot(self, scn, frames):
        hip = self.getBone("hip")
        lFoot,lToe = self.getFkFeetBones("L")
        rFoot,rToe = self.getFkFeetBones("R")
        if self.useMarkers:
            lMarkers = self.getMarkers("L")
            rMarkers = self.getMarkers("R")
        else:
            lMarkers = rMarkers = None
        ez,origin,rot = self.getPlaneInfo()

        nFrames = len(frames)
        for n,frame in enumerate(frames):
            self.setFrame(scn, frame)
            offset = 0
            if self.useLeft:
                offset = self.getFkOffset(ez, origin, lFoot, lToe, lMarkers)
            if self.useRight:
                rOffset = self.getFkOffset(ez, origin, rFoot, rToe, rMarkers)
                if rOffset > offset:
                    offset = rOffset
            showProgress(n, frame, nFrames)
            if offset > 0:
                self.addOffset(hip, offset, ez)


    def getFkFeetBones(self, suffix):
        foot = self.getBone("foot.fk.%s" % suffix)
        toe = self.getBone("toe.fk.%s" % suffix)
        return foot,toe


    def getFkOffset(self, ez, origin, foot, toe, markers):
        if markers:
            mToe,mBall,mHeel = markers
            toeOffset = getHeadOffset(mToe, ez, origin)
            ballOffset = getHeadOffset(mBall, ez, origin)
            heelOffset = getHeadOffset(mHeel, ez, origin)
            return max([toeOffset, ballOffset, heelOffset])
        elif toe:
            toeOffset = getTailOffset(toe, ez, origin)
            ballOffset = getHeadOffset(toe, ez, origin)
            ball = toe.matrix.col[3]
            y = toe.matrix.col[1]
            heel = ball - y*foot.length
            heelOffset = getOffset(heel, ez, origin)
            return max([toeOffset, ballOffset, heelOffset])
        else:
            return 0

#-------------------------------------------------------------
#   Floor IK foot
#-------------------------------------------------------------

class MHX_OT_FloorIkFoot(HidePropsOperator, Footer, FrameRange):
    bl_idname = "mhx.floor_ik_feet"
    bl_label = "Keep IK Feet Above Floor"
    bl_description = "Keep IK Feet Above Zero Plane"
    bl_options = {'UNDO'}

    useGlue : BoolProperty(
        name = "Glue Feet",
        description = "Remove movement of IK effector on shifted frames",
        default = True)

    easeInOut : IntProperty(
        name = "Ease In/Out",
        description = "",
        min = 0, max = 5,
        default = 3)

    def draw(self, context):
        Footer.draw(self, context)
        self.layout.prop(self, "useGlue")
        self.layout.prop(self, "easeInOut")


    def run(self, context):
        startProgress("Keep feet above floor")
        self.auto = True
        scn = context.scene
        self.rig, self.plane = self.getRigAndPlane(context)
        checkVisible(self.rig)
        frames = self.getActiveFrames()
        self.floorIkFoot(scn, frames)
        self.setInterpolation()
        displayMessage("FK Feet kept above floor")


    def floorIkFoot(self, scn, frames):
        hip = self.rig.pose.bones["hip"]
        lleg = self.rig.pose.bones["foot.ik.L"]
        rleg = self.rig.pose.bones["foot.ik.R"]
        ez,origin,rot = self.getPlaneInfo()
        if self.useMarkers:
            lMarkers = self.getMarkers("L")
            rMarkers = self.getMarkers("R")
        else:
            lMarkers = rMarkers = None

        self.fillKeyFrames(lleg, frames, 3, mode='location')
        self.fillKeyFrames(rleg, frames, 3, mode='location')
        if self.useHips:
            self.fillKeyFrames(hip, frames, 3, mode='location')

        nFrames = len(frames)
        left = []
        right = []
        for n,frame in enumerate(frames):
            self.setFrame(scn, frame)
            showProgress(n, frame, nFrames)
            if self.useLeft:
                lOffset = self.getIkOffset(ez, origin, lleg, lMarkers)
                if lOffset > 0:
                    self.addOffset(lleg, lOffset, ez)
                    left.append(frame)
            else:
                lOffset = 0
            if self.useRight:
                rOffset = self.getIkOffset(ez, origin, rleg, rMarkers)
                if rOffset > 0:
                    self.addOffset(rleg, rOffset, ez)
                    right.append(frame)
            else:
                rOffset = 0
            hOffset = min(lOffset,rOffset)
            if hOffset > 0 and self.useHips:
                self.addOffset(hip, hOffset, ez)

        if self.useGlue and left:
            self.glueFoot(lleg, left)
        if self.useGlue and right:
            self.glueFoot(rleg, right)


    def fillKeyFrames(self, pb, frames, nIndices, mode='rotation'):
        for idx in range(nIndices):
            fcu = self.findBoneFCurve(pb, idx, mode)
            if fcu is None:
                return
            for frame in frames:
                y = fcu.evaluate(frame)
                fcu.keyframe_points.insert(frame, y, options={'FAST'})


    def getIkOffset(self, ez, origin, leg, markers):
        if markers:
            mToe,mBall,mHeel = markers
            toeOffset = getHeadOffset(mToe, ez, origin)
            ballOffset = getHeadOffset(mBall, ez, origin)
            heelOffset = getHeadOffset(mHeel, ez, origin)
            return max([toeOffset, ballOffset, heelOffset])
        elif True:
            headOffset = getHeadOffset(leg, ez, origin)
            tailOffset = getTailOffset(leg, ez, origin)
            return max([headOffset, tailOffset])
        else:
            foot = self.rig.pose.bones["foot.rev.%s" % suffix]
            toe = self.rig.pose.bones["toe.rev.%s" % suffix]
            toeOffset = getHeadOffset(toe, ez, origin)
            ballOffset = getTailOffset(toe, ez, origin)
            ball = foot.matrix.col[3]
            heel = ball + y*foot.length
            heelOffset = getOffset(heel, ez, origin)
            return max([toeOffset, ballOffset, heelOffset])


    def glueFoot(self, leg, frames):
        if len(frames) == 0:
            return
        fcus = self.findBoneFCurves(leg, "rotation")
        fcus += self.findBoneFCurves(leg, "location")
        groups = self.getGroups(frames)
        for frame0,frame1 in groups:
            for fcu in fcus:
                self.average(fcu, frame0, frame1)


    def getGroups(self, frames):
        groups = []
        frame0 = frame1 = frames[0]
        n1 = 1
        while frames:
            frame0 = frame1 = frames[0]
            for n,frame in enumerate(frames[1:]):
                n1 = n+1
                if frame == frame1+1:
                    frame1 = frame
                else:
                    break
            if frame1 != frame0:
                groups.append((frame0, frame1))
            frames = frames[n1:]
        return groups


    def average(self, fcu, frame0, frame1):
        kps = [kp for kp in fcu.keyframe_points
               if kp.co[0] >= frame0 and kp.co[0] <= frame1]
        yvals = [kp.co[1] for kp in kps]
        if len(yvals) == 0:
            return
        n = min(self.easeInOut, len(kps)-2)
        if len(kps) < 2*n:
            y0 = kps[0].co[1]
            y1 = kps[-1].co[1]
            for j in range(n):
                w = j/n
                kp = kps[j]
                kp.co[1] = w*y1 + (1-w)*y0
        else:
            y = sum(yvals)/len(yvals)
            for j in range(n):
                w = j/n
                kp = kps[j]
                kp.co[1] = w*y + (1-w)*kp.co[1]
                kp = kps[-1-j]
                kp.co[1] = w*y + (1-w)*kp.co[1]
            for kp in kps[n:-1-n]:
                kp.co[1] = y

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MHX_OT_RemoveFrameZero,
    MHX_OT_RemoveUnusedFcurves,
    MHX_OT_SetConstraints,
    MHX_OT_EnforceLimits,
    MHX_OT_EnforceAllLimits,
    MHX_OT_LimbsBendPositive,
    MHX_OT_ShiftBoneFCurves,
    MHX_OT_TransferToFk,
    MHX_OT_TransferToIk,
    MHX_OT_ClearAnimation,
    MHX_OT_FloorFkFoot,
    MHX_OT_FloorIkFoot,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

