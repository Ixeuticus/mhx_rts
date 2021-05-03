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
from bpy.props import StringProperty, BoolProperty
from mathutils import *
from .utils import *
from .layers import *

#------------------------------------------------------------------
#   Updater
#------------------------------------------------------------------

class Updater:
    def updatePose(self):
        bpy.context.view_layer.update()

    def updateScene(self):
        deps = bpy.context.evaluated_depsgraph_get()
        deps.update()

    def setFrame(self, scn, frame):
        scn.frame_set(frame)
        self.frame = frame
        self.updateScene()

#----------------------------------------------------------
#   Basic utilities
#----------------------------------------------------------

class Basic:

    def getBone(self, bname):
        try:
            return self.rig.pose.bones[bname]
        except KeyError:
            pass
        raise MhxError("What? Bone %s not found" % bname)


    def getPoseMatrix(self, gmat, pb):
        restInv = pb.bone.matrix_local.inverted()
        if pb.parent:
            parInv = pb.parent.matrix.inverted()
            parRest = pb.parent.bone.matrix_local
            return restInv @ parRest @ parInv @ gmat
        else:
            return restInv @ gmat


    def insertLocation(self, pb, mat):
        pb.location = mat.to_translation()
        if self.auto or isKeyed(self.rig, pb, "location"):
            pb.keyframe_insert("location", frame=self.frame, group=pb.name)


    def insertRotation(self, pb, mat):
        quat = mat.to_quaternion()
        if pb.rotation_mode == 'QUATERNION':
            pb.rotation_quaternion = quat
            if self.auto or isKeyed(self.rig, pb, "rotation_quaternion"):
                pb.keyframe_insert("rotation_quaternion", frame=self.frame, group=pb.name)
        else:
            pb.rotation_euler = quat.to_euler(pb.rotation_mode)
            if self.auto or isKeyed(self.rig, pb, "rotation_euler"):
                pb.keyframe_insert("rotation_euler", frame=self.frame, group=pb.name)


    def findBoneFCurves(self, pb, mode):
        if self.rig.animation_data is None:
            return None
        act = self.rig.animation_data.action
        if act is None:
            return None
        if mode == 'rotation':
            if pb.rotation_mode == 'QUATERNION':
                mode = "rotation_quaternion"
            else:
                mode = "rotation_euler"
        path = 'pose.bones["%s"].%s' % (pb.name, mode)
        return [fcu for fcu in act.fcurves if fcu.data_path == path]


    def findBoneFCurve(self, pb, idx, mode='rotation'):
        for fcu in self.findBoneFCurves(pb, mode):
            if fcu.array_index == idx:
                return fcu
        print('F-curve %d for "%s" not found.' % (idx, pb.name))
        return None

#------------------------------------------------------------------
#   Snapper class
#------------------------------------------------------------------

SnapBones = {
    "Arm"   : ["upper_arm", "forearm", "hand"],
    "ArmFK" : ["upper_arm.fk", "forearm.fk", "hand.fk"],
    "ArmIK" : ["upper_arm.ik", "forearm.ik", "elbow.pt.ik", "elbowPoleA", "hand.ik"],
    "Leg"   : ["thigh", "shin", "foot", "toe"],
    "LegFK" : ["thigh.fk", "shin.fk", "foot.fk", "toe.fk"],
    "LegIK" : ["thigh.ik", "shin.ik", "knee.pt.ik", "kneePoleA", "ankle", "ankle.ik", "foot.ik", "foot.rev", "toe.rev", "foot.inv.fk", "toe.inv.fk", "foot.inv.ik", "toe.inv.ik"],
}

class Snapper(Updater, Basic):

    def prequel(self, context):
        HideOperator.prequel(self, context)
        self.muteAllConstraints(True)


    def sequel(self, context):
        HideOperator.sequel(self, context)
        self.muteAllConstraints(False)


    def muteAllConstraints(self, value):
        for part in ["ArmIK", "ArmFK", "LegIK", "LegFK"]:
            for suffix in ["L", "R"]:
                _snap,constraints = self.getSnapBones(part, suffix)
                for cns in constraints:
                    cns.mute = value


    def setup(self, context, value):
        bpy.ops.object.mode_set(mode='POSE')
        self.oldvalue = value
        self.amt[self.prop] = value
        self.auto = context.scene.tool_settings.use_keyframe_insert_auto
        self.updatePose()


    def restore(self, context, value, fk, ik):
        if context.scene.MhxUseSwitch:
            self.amt[self.prop] = value
            self.state[self.fk] = fk
            self.state[self.ik] = ik
        else:
            self.amt[self.prop] = self.oldvalue
        self.updatePose()


    def matchPoseTranslation(self, pb, src):
        pmat = self.getPoseMatrix(src.matrix, pb)
        self.insertLocation(pb, pmat)


    def matchPoseLocRot(self, pb, src):
        pmat = self.getPoseMatrix(src.matrix, pb)
        self.insertLocation(pb, pmat)
        self.insertRotation(pb, pmat)


    def matchPoseTransform(self, pb, src):
        pmat = self.getPoseMatrix(src.matrix, pb)
        self.insertRotation(pb, pmat)


    def matchPoseTwist(self, pb, src):
        pmat0 = src.matrix_basis
        euler = pmat0.to_3x3().to_euler('YZX')
        euler.z = 0
        pmat = euler.to_matrix().to_4x4()
        pmat.col[3] = pmat0.col[3]
        self.insertRotation(pb, pmat)


    def matchIkLeg(self, legIk, toeFk):
        # No x and y rotation for Leg IK target
        tHead = toeFk.matrix.decompose()[0]
        tmat = toeFk.matrix.to_3x3()
        ty = tmat.col[1]
        tTail = tHead + ty * toeFk.bone.length
        if self.useRotation:
            y = tTail - tHead
            y.normalize()
            z = tmat.col[2]
            x = y.cross(z)
            gmat = Matrix((x,y,z))
            gmat.transpose()
        else:
            gmat = legIk.bone.matrix_local.to_3x3()
            y = gmat.col[1]
        head = tTail - y * legIk.bone.length
        gmat = gmat.to_4x4()
        gmat.col[3][:3] = head
        pmat = self.getPoseMatrix(gmat, legIk)
        self.insertLocation(legIk, pmat)
        self.insertRotation(legIk, pmat)


    def zeroPoleA(self, poleA):
        if poleA:
            self.insertRotation(poleA, Matrix())
            self.updatePose()


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
        pmat = self.getPoseMatrix(gmat, pb)
        self.insertLocation(pb, pmat)


    def matchPoseReverse(self, pb, src):
        gmat = src.matrix
        tail = gmat.col[3] + src.length * gmat.col[1]
        rmat = Matrix((gmat.col[0], -gmat.col[1], -gmat.col[2], tail))
        rmat.transpose()
        pmat = self.getPoseMatrix(rmat, pb)
        pb.matrix_basis = pmat
        self.insertRotation(pb, pmat)


    def matchPoseScale(self, pb, src):
        pmat = self.getPoseMatrix(src.matrix, pb)
        pb.scale = pmat.to_scale()
        if self.auto or isKeyed(self.rig, pb, "scale"):
            pb.keyframe_insert("scale", frame=self.frame, group=pb.name)


    def getSnapBones(self, key, suffix):
        pbones = []
        constraints = []
        for name in SnapBones[key]:
            bname = "%s.%s" % (name, suffix)
            if bname in self.rig.pose.bones.keys():
                pb = self.rig.pose.bones[bname]
            elif "PoleA" in bname or "inv.fk" in bname:
                pbones.append(None)
                continue
            else:
                raise MhxError("Bone %s was not found" % bname)
            pbones.append(pb)
            for cns in pb.constraints:
                if cns.type == 'LIMIT_ROTATION' and not cns.mute:
                    constraints.append(cns)
        return tuple(pbones),constraints


    def snapFkArm(self, snapFk, snapIk):
        (uparmFk, loarmFk, handFk) = snapFk
        (uparmIk, loarmIk, elbowPt, elbowPoleA, handIk) = snapIk

        self.matchPoseTransform(uparmFk, uparmIk)
        self.updatePose()
        self.matchPoseTransform(loarmFk, loarmIk)
        self.updatePose()
        self.matchPoseTransform(handFk, handIk)


    def snapIkArm(self, snapFk, snapIk):
        (uparmFk, loarmFk, handFk) = snapFk
        (uparmIk, loarmIk, elbowPt, elbowPoleA, handIk) = snapIk

        self.zeroPoleA(elbowPoleA)
        self.matchPoseLocRot(handIk, handFk)
        self.updatePose()
        self.matchPoleTarget(elbowPt, uparmFk, loarmFk)


    def snapFkLeg(self, snapFk, snapIk, legIkToAnkle):
        (uplegFk, lolegFk, footFk, toeFk) = snapFk
        (uplegIk, lolegIk, kneePt, kneePoleA, ankle, ankleIk, legIk, footRev, toeRev, footInvFk, toeInvFk, footInvIk, toeInvIk) = snapIk

        self.matchPoseTransform(uplegFk, uplegIk)
        self.updatePose()
        self.matchPoseTransform(lolegFk, lolegIk)
        if not legIkToAnkle:
            self.updatePose()
            self.matchPoseTransform(footFk, footInvIk)
            self.updatePose()
            self.matchPoseTransform(toeFk, toeInvIk)


    def snapIkLeg(self, snapFk, snapIk, legIkToAnkle):
        (uplegFk, lolegFk, footFk, toeFk) = snapFk
        (uplegIk, lolegIk, kneePt, kneePoleA, ankle, ankleIk, legIk, footRev, toeRev, footInvFk, toeInvFk, footInvIk, toeInvIk) = snapIk

        self.zeroPoleA(kneePoleA)
        if legIkToAnkle:
            self.matchPoseTranslation(ankle, footFk)
        else:
            self.matchIkLeg(legIk, toeFk)
            self.updatePose()
            if toeInvFk:
                self.matchPoseTransform(toeRev, toeInvFk)
                self.updatePose()
                self.matchPoseTransform(footRev, footInvFk)
            else:
                self.matchPoseReverse(toeRev, toeFk)
                self.updatePose()
                self.matchPoseReverse(footRev, footFk)
            self.updatePose()
            self.matchPoseTranslation(ankleIk, footFk)
        self.updatePose()
        self.matchPoleTarget(kneePt, uplegFk, lolegFk)


class FootSnapper(Snapper):
    useRotation: BoolProperty(
        name = "Rotate IK Foot",
        description = "Also match IK effector rotation.\nSuitable for hand animation",
        default = True)

    def draw(self, context):
        self.layout.prop(self, "useRotation")



class MHX_OT_MhxSnapFkLeftArm(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_left_arm"
    bl_label = "Snap L FK Arm"
    bl_description = "Snap the left FK arm to the pose of the left IK arm"
    bl_options = {'UNDO'}

    suffix = ".L"
    prop = "MhaArmIk_L"
    ik = L_LARMIK
    fk = L_LARMFK

    def run(self, context):
        print("Snap Left FK Arm")
        self.setup(context, 1.0)
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "L")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "L")
        self.snapFkArm(snapFk, snapIk)
        self.restore(context, 0.0, True, False)


class MHX_OT_MhxSnapFkRightArm(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_right_arm"
    bl_label = "Snap R FK Arm"
    bl_description = "Snap the right FK arm to the pose of the right IK arm"
    bl_options = {'UNDO'}

    suffix = ".R"
    prop = "MhaArmIk_R"
    ik = L_RARMIK
    fk = L_RARMFK

    def run(self, context):
        print("Snap Right FK Arm")
        self.setup(context, 1.0)
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "R")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "R")
        self.snapFkArm(snapFk, snapIk)
        self.restore(context, 0.0, True, False)


class MHX_OT_MhxSnapFkLeftLeg(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_left_leg"
    bl_label = "Snap L FK Leg"
    bl_description = "Snap the left FK leg to the pose of the left IK leg"
    bl_options = {'UNDO'}

    suffix = ".L"
    prop = "MhaLegIk_L"
    ik = L_LLEGIK
    fk = L_LLEGFK

    def run(self, context):
        print("Snap Left FK Leg")
        self.setup(context, 1.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "L")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "L")
        self.snapFkLeg(snapFk, snapIk, self.amt["MhaLegIkToAnkle_L"])
        self.restore(context, 0.0, True, False)


class MHX_OT_MhxSnapFkRightLeg(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_right_leg"
    bl_label = "Snap R FK Leg"
    bl_description = "Snap the right FK leg to the pose of the right IK leg"
    bl_options = {'UNDO'}

    suffix = ".R"
    prop = "MhaLegIk_R"
    ik = L_RLEGIK
    fk = L_RLEGFK

    def run(self, context):
        print("Snap Right FK Leg")
        self.setup(context, 1.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "R")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "R")
        self.snapFkLeg(snapFk, snapIk, self.amt["MhaLegIkToAnkle_R"])
        self.restore(context, 0.0, True, False)


class MHX_OT_MhxSnapIkLeftArm(Snapper, HideOperator):
    bl_idname = "mhx.snap_ik_left_arm"
    bl_label = "Snap L IK Arm"
    bl_description = "Snap the left IK arm to the pose of the left FK arm"
    bl_options = {'UNDO'}

    suffix = ".L"
    prop = "MhaArmIk_L"
    ik = L_LARMIK
    fk = L_LARMFK

    def run(self, context):
        print("Snap Left IK Arm")
        self.setup(context, 0.0)
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "L")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "L")
        self.snapIkArm(snapFk, snapIk)
        self.restore(context, 1.0, False, True)


class MHX_OT_MhxSnapIkRightArm(Snapper, HideOperator):
    bl_idname = "mhx.snap_ik_right_arm"
    bl_label = "Snap R IK Arm"
    bl_description = "Snap the right IK arm to the pose of the right FK arm"
    bl_options = {'UNDO'}

    suffix = ".R"
    prop = "MhaArmIk_R"
    ik = L_RARMIK
    fk = L_RARMFK

    def run(self, context):
        print("Snap Right IK Arm")
        self.setup(context, 0.0)
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "R")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "R")
        self.snapIkArm(snapFk, snapIk)
        self.restore(context, 1.0, False, True)


class MHX_OT_MhxSnapIkLeftLeg(FootSnapper, HideOperator):
    bl_idname = "mhx.snap_ik_left_leg"
    bl_label = "Snap L IK Leg"
    bl_description = "Snap the left IK leg to the pose of the left FK leg"
    bl_options = {'UNDO'}

    suffix = ".L"
    prop = "MhaLegIk_L"
    ik = L_LLEGIK
    fk = L_LLEGFK

    def run(self, context):
        print("Snap Left IK Leg")
        self.useRotation = context.scene.MhxUseSnapRotation
        self.setup(context, 0.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "L")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "L")
        self.snapIkLeg(snapFk, snapIk, self.amt["MhaLegIkToAnkle_L"])
        self.restore(context, 1.0, False, True)


class MHX_OT_MhxSnapIkRightLeg(FootSnapper, HideOperator):
    bl_idname = "mhx.snap_ik_right_leg"
    bl_label = "Snap R IK Leg"
    bl_description = "Snap the right IK leg to the pose of the right FK leg"
    bl_options = {'UNDO'}

    suffix = ".R"
    prop = "MhaLegIk_R"
    ik = L_RLEGIK
    fk = L_RLEGFK

    def run(self, context):
        print("Snap Right IK Leg")
        self.useRotation = context.scene.MhxUseSnapRotation
        self.setup(context, 0.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "R")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "R")
        self.snapIkLeg(snapFk, snapIk, self.amt["MhaLegIkToAnkle_R"])
        self.restore(context, 1.0, False, True)

#----------------------------------------------------------
#   Toggle FK - IK
#----------------------------------------------------------

class Toggler(Updater):
    def toggle(self, context, prop, fklayer, iklayer):
        rig = context.object
        scn = context.scene
        value = rig.data[prop]
        if value > 0.5:
            value = 0.0
            fk = True
            ik = False
        else:
            value = 1.0
            fk = False
            ik = True
        rig.data[prop] = value
        rig.data.layers[fklayer] = fk
        rig.data.layers[iklayer] = ik
        path = (propRef(prop))
        if isKeyed(rig, None, path):
            rig.data.keyframe_insert(path, frame=scn.frame_current)
        self.updatePose()


class MHX_OT_MhxToggleLeftArm(MhxOperator, Toggler):
    bl_idname = "mhx.toggle_left_arm"
    bl_label = ""
    bl_description = "Toggle left arm FK - IK"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaArmIk_L", L_LARMFK, L_LARMIK)


class MHX_OT_MhxToggleRightArm(MhxOperator, Toggler):
    bl_idname = "mhx.toggle_right_arm"
    bl_label = ""
    bl_description = "Toggle right arm FK - IK"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaArmIk_R", L_RARMFK, L_RARMIK)


class MHX_OT_MhxToggleLeftLeg(MhxOperator, Toggler):
    bl_idname = "mhx.toggle_left_leg"
    bl_label = ""
    bl_description = "Toggle left leg FK - IK"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaLegIk_L", L_LLEGFK, L_LLEGIK)


class MHX_OT_MhxToggleRightLeg(MhxOperator, Toggler):
    bl_idname = "mhx.toggle_right_leg"
    bl_label = ""
    bl_description = "Toggle right leg FK - IK"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaLegIk_R", L_RLEGFK, L_RLEGIK)

#----------------------------------------------------------
#   Toggle hints
#----------------------------------------------------------

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
        rig.data.MhaHintsOn = not rig.data.MhaHintsOn

#----------------------------------------------------------
#   Toggle limits
#----------------------------------------------------------

class MHX_OT_MhxToggleLimits(MhxOperator):
    bl_idname = "mhx.toggle_limits"
    bl_label = "Rotation Limits"
    bl_description = "Toggle FK and IK rotation limits.\nIt may be necessary to turn these off for correct FK->IK snapping."

    def run(self, context):
        rig = context.object
        on = rig.data.MhaLimitsOn = not rig.data.MhaLimitsOn
        for pb in rig.pose.bones:
            for cns in pb.constraints:
                if cns.type == 'LIMIT_ROTATION' and cns.name != "Hint":
                    cns.mute = (not on)
        for suffix in [".L", ".R"]:
            for bname in ["upper_arm", "forearm", "thigh", "shin"]:
                pb = rig.pose.bones["%s.ik%s" % (bname, suffix)]
                pb.use_ik_limit_x = pb.use_ik_limit_y = pb.use_ik_limit_z = on

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
    MHX_OT_MhxToggleLeftArm,
    MHX_OT_MhxToggleRightArm,
    MHX_OT_MhxToggleLeftLeg,
    MHX_OT_MhxToggleRightLeg,
    MHX_OT_MhxToggleHints,
    MHX_OT_MhxToggleLimits,
]

def register():
    bpy.types.Scene.MhxUseSwitch = BoolProperty(
        name = "Switch Mode And Layers",
        description = "Also switch the FK/IK mode and bone layers",
        default = True)

    bpy.types.Scene.MhxUseSnapRotation = BoolProperty(
        name = "Rotate IK Foot",
        description = "Also match IK effector rotation.\nSuitable for hand animation",
        default = True)


    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

