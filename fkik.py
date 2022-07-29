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
        try:
            scn.frame_set(frame)
        except TypeError:
            frame = int(frame)
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


    def insertLocation(self, pb, mat=None):
        if mat:
            pb.location = mat.to_translation()
        if self.auto or isKeyed(self.rig, pb, "location"):
            pb.keyframe_insert("location", frame=self.frame, group=pb.name)


    def insertRotation(self, pb, mat=None):
        if mat:
            quat = mat.to_quaternion()
            if pb.rotation_mode == 'QUATERNION':
                pb.rotation_quaternion = quat
            else:
                pb.rotation_euler = quat.to_euler(pb.rotation_mode)
        if pb.rotation_mode == 'QUATERNION':
            if self.auto or isKeyed(self.rig, pb, "rotation_quaternion"):
                pb.keyframe_insert("rotation_quaternion", frame=self.frame, group=pb.name)
        else:
            if self.auto or isKeyed(self.rig, pb, "rotation_euler"):
                pb.keyframe_insert("rotation_euler", frame=self.frame, group=pb.name)


    def findBoneFCurves(self, pb, mode):
        if self.rig.animation_data is None:
            return []
        act = self.rig.animation_data.action
        if act is None:
            return []
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
    "ArmIK" : ["upper_arm.ik", "forearm.ik", "upper_arm.ik.twist", "forearm.ik.twist", "elbow.pt.ik", "elbowPoleA", "hand.ik"],
    "Leg"   : ["thigh", "shin", "foot", "toe"],
    "LegFK" : ["thigh.fk", "shin.fk", "foot.fk", "toe.fk"],
    "LegIK" : ["thigh.ik", "shin.ik", "thigh.ik.twist", "shin.ik.twist", "knee.pt.ik", "kneePoleA", "ankle", "ankle.ik", "foot.ik", "foot.rev", "toe.rev", "foot.inv.fk", "toe.inv.fk", "foot.inv.ik", "toe.inv.ik"],
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
        checkVisible(context.object)
        setMode('POSE')
        self.oldvalue = value
        self.amt[self.prop] = value
        self.auto = context.scene.tool_settings.use_keyframe_insert_auto
        self.updatePose()


    def restore(self, context, value, fk, ik):
        scn = context.scene
        if scn.MhxUseSwitch:
            self.amt[self.prop] = value
            self.state[self.fk] = fk
            self.state[self.ik] = ik
            if self.auto:
                self.amt.keyframe_insert(propRef(self.prop), frame=scn.frame_current)
        else:
            self.amt[self.prop] = self.oldvalue
        self.updatePose()


    def matchPoseTranslation(self, pb, src):
        pb.matrix = src.matrix
        self.updatePose()
        self.insertLocation(pb)


    def matchPoseLocRot(self, pb, src):
        pb.matrix = src.matrix
        self.updatePose()
        self.insertLocation(pb)
        self.insertRotation(pb)


    def matchPoseTransform(self, pb, src):
        pb.matrix = src.matrix
        self.updatePose()
        self.insertRotation(pb)


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
        #pmat = self.getPoseMatrix(gmat, legIk)
        legIk.matrix = gmat
        self.updatePose()
        self.insertLocation(legIk)
        self.insertRotation(legIk)


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
        pb.matrix = Matrix.Translation(p)
        self.updatePose()
        self.insertLocation(pb)

    #
    # https://bitbucket.org/Diffeomorphic/import_daz/issues/528/mhx-snap-ik-to-fk-can-set-pole-more
    #
    def setPoleTarget(self, hand, poleTrg, poleA, forearm):
        self.insertRotation(poleA, Matrix())
        self.updatePose()
        pf_rot_y = forearm.y_axis.normalized()
        pf_rot_z = forearm.z_axis.normalized()
        pf_pos = forearm.matrix.to_translation()
        pa_pos = poleA.matrix.to_translation()
        if (hand.head - forearm.tail).length < 0.001:
            #print("non stretch", hand.name)
            n_vec = (pf_pos - pa_pos).normalized()
        else:
            #print("stretch ", hand.name)
            n_vec = -pf_rot_z
        pole_vec = n_vec * (1.2 * forearm.length)
        #the multipled length should be set with forearm or upperarm)
        tr_mat = Matrix.Translation(pole_vec)
        pos = tr_mat @ poleA.matrix
        poleTrg.matrix = pos
        poleTrg.rotation_euler = (0.0, 0.0, 0.0)
        self.updatePose()
        self.insertLocation(poleTrg)


    def matchPoseReverse(self, pb, src):
        gmat = src.matrix
        tail = gmat.col[3] + src.length * gmat.col[1]
        rmat = Matrix((gmat.col[0], -gmat.col[1], -gmat.col[2], tail))
        rmat.transpose()
        pb.matrix = rmat
        self.updatePose()
        self.insertRotation(pb)


    def getSnapBones(self, key, suffix):
        pbones = []
        constraints = []
        for name in SnapBones[key]:
            bname = "%s.%s" % (name, suffix)
            if bname in self.rig.pose.bones.keys():
                pb = self.rig.pose.bones[bname]
            elif ("PoleA" in bname or
                  "inv.fk" in bname or
                  "inv.ik" in bname or
                  "ik.twist" in bname):
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
        (uparmFk, forearmFk, handFk) = snapFk
        (uparmIk, forearmIk, uparmIkTwist, forearmIkTwist, elbowPt, elbowPoleA, handIk) = snapIk

        if uparmIkTwist:
            self.matchPoseTransform(uparmFk, uparmIkTwist)
            self.matchPoseTransform(forearmFk, forearmIkTwist)
        else:
            self.matchPoseTransform(uparmFk, uparmIk)
            self.matchPoseTransform(forearmFk, forearmIk)
        self.matchPoseTransform(handFk, handIk)


    def snapIkArm(self, snapFk, snapIk):
        (uparmFk, forearmFk, handFk) = snapFk
        (uparmIk, forearmIk, uparmIkTwist, forearmIkTwist, elbowPt, elbowPoleA, handIk) = snapIk

        handFk.location = (0,0,0)
        self.matchPoseLocRot(handIk, handFk)
        if elbowPoleA:
            self.setPoleTarget(handIk, elbowPt, elbowPoleA, forearmFk)
        else:
            self.matchPoleTarget(elbowPt, uparmFk, forearmFk)
        if uparmIkTwist:
            self.matchPoseTransform(uparmIkTwist, uparmFk)
            self.matchPoseTransform(forearmIkTwist, forearmFk)


    def snapFkLeg(self, snapFk, snapIk, legIkToAnkle):
        (thighFk, shinFk, footFk, toeFk) = snapFk
        (thighIk, shinIk, thighIkTwist, shinIkTwist, kneePt, kneePoleA, ankle, ankleIk, legIk, footRev, toeRev, footInvFk, toeInvFk, footInvIk, toeInvIk) = snapIk

        if shinIkTwist:
            self.matchPoseTransform(thighFk, thighIkTwist)
            self.matchPoseTransform(shinFk, shinIkTwist)
        else:
            self.matchPoseTransform(thighFk, thighIk)
            self.matchPoseTransform(shinFk, shinIk)
        if not legIkToAnkle:
            self.matchPoseTransform(footFk, footInvIk)
            self.matchPoseTransform(toeFk, toeInvIk)


    def snapIkLeg(self, snapFk, snapIk, legIkToAnkle):
        (thighFk, shinFk, footFk, toeFk) = snapFk
        (thighIk, shinIk, thighIkTwist, shinIkTwist, kneePt, kneePoleA, ankle, ankleIk, legIk, footRev, toeRev, footInvFk, toeInvFk, footInvIk, toeInvIk) = snapIk

        footFk.location = (0,0,0)
        if legIkToAnkle:
            self.matchPoseTranslation(ankle, footFk)
        else:
            self.matchIkLeg(legIk, toeFk)
            if toeInvFk:
                self.matchPoseTransform(toeRev, toeInvFk)
                self.matchPoseTransform(footRev, footInvFk)
            else:
                self.matchPoseReverse(toeRev, toeFk)
                self.matchPoseReverse(footRev, footFk)
            self.matchPoseTranslation(ankleIk, footFk)
        if kneePoleA:
            self.setPoleTarget(footInvIk, kneePt, kneePoleA, shinFk)
        else:
            self.matchPoleTarget(kneePt, thighFk, shinFk)
        if shinIkTwist:
            self.matchPoseTransform(thighIkTwist, thighFk)
            self.matchPoseTransform(shinIkTwist, shinFk)


class FootSnapper(Snapper):
    useRotation: BoolProperty(
        name = "Rotate IK Foot",
        description = "Also match IK effector rotation.\nSuitable for hand animation",
        default = True)

    def draw(self, context):
        self.layout.prop(self, "useRotation")



class MHX_OT_MhxSnapFkLeftArm(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_left_arm"
    bl_label = "Snap Left"
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
    bl_label = "Snap Right"
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
    bl_label = "Snap Left"
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
    bl_label = "Snap Right"
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
    bl_label = "Snap Left"
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
    bl_label = "Snap Right"
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
    bl_label = "Snap Left"
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
    bl_label = "Snap Right"
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

class ToggleFkIk(Updater):
    def toggle(self, context, prop, fklayer, iklayer):
        rig = context.object
        checkVisible(rig)
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
        path = propRef(prop)
        if (scn.tool_settings.use_keyframe_insert_auto or
            isKeyed(rig, None, path)):
            rig.data.keyframe_insert(path, frame=scn.frame_current)
        self.updatePose()


class MHX_OT_MhxToggleFkIkLeftArm(MhxOperator, ToggleFkIk):
    bl_idname = "mhx.toggle_fkik_left_arm"
    bl_label = ""
    bl_description = "Toggle left arm FK - IK"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaArmIk_L", L_LARMFK, L_LARMIK)


class MHX_OT_MhxToggleFkIkRightArm(MhxOperator, ToggleFkIk):
    bl_idname = "mhx.toggle_fkik_right_arm"
    bl_label = ""
    bl_description = "Toggle right arm FK - IK"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaArmIk_R", L_RARMFK, L_RARMIK)


class MHX_OT_MhxToggleFkIkLeftLeg(MhxOperator, ToggleFkIk):
    bl_idname = "mhx.toggle_fkik_left_leg"
    bl_label = ""
    bl_description = "Toggle left leg FK - IK"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaLegIk_L", L_LLEGFK, L_LLEGIK)


class MHX_OT_MhxToggleFkIkRightLeg(MhxOperator, ToggleFkIk):
    bl_idname = "mhx.toggle_fkik_right_leg"
    bl_label = ""
    bl_description = "Toggle right leg FK - IK"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaLegIk_R", L_RLEGFK, L_RLEGIK)

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

class MHX_OT_MhxUpdateElbowKneeParents(MhxOperator, Updater):
    bl_idname = "mhx.update_elbow_knee_parents"
    bl_label = "Update Elbow And Knee Parents"
    bl_description = "Update parents of the elbow and knee pole targets"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaElbowParent_L", "elbow.pt.ik.L", "elbowPoleP.L",  "arm_parent.L")
        self.toggle(context, "MhaElbowParent_R", "elbow.pt.ik.R", "elbowPoleP.R",  "arm_parent.R")
        self.toggle(context, "MhaKneeParent_L", "knee.pt.ik.L", "kneePoleP.L",  "arm_parent.L")
        self.toggle(context, "MhaKneeParent_R", "knee.pt.ik.R", "kneePoleP.R",  "arm_parent.R")


    def toggle(self, context, prop, bname, polep, limbpar):
        def getChildOfConstraint(pb):
            for cns in pb.constraints:
                if cns.type == 'CHILD_OF':
                    return cns
            return None

        rig = context.object
        pb = rig.pose.bones[bname]
        wmat = pb.matrix.copy()
        partype = getattr(rig.data, prop)
        if partype in ['HAND', 'FOOT']:
            parname = polep
        elif partype in ['SHOULDER', 'HIP']:
            parname = limbpar
        elif partype == 'MASTER':
            parname = "master"
        cns = getChildOfConstraint(pb)
        if cns:
            rig.data.bones.active = pb.bone
            cns.subtarget = parname
            bpy.ops.constraint.childof_set_inverse(constraint=cns.name, owner='BONE')
        else:
            setMode('EDIT', "Cannot update parents for this armature")
            eb = rig.data.edit_bones[bname]
            eb.parent = rig.data.edit_bones[parname]
            setMode('POSE')
        pb = rig.pose.bones[bname]
        pb.matrix = wmat

#----------------------------------------------------------
#   Toggle Stretch
#----------------------------------------------------------
'''
class ToggleStretch(Updater):
    def toggle(self, context, prop, armname, handname, suffix):
        def getCopyLocConstraint(rig, bname):
            pb = rig.pose.bones[bname]
            for cns in pb.constraints:
                if (cns.type == 'COPY_LOCATION' and
                    cns.head_tail == 1.0):
                    return cns
            return None

        def getStretchToConstraint(rig, bname):
            if bname not in rig.pose.bones:
                return
            pb = rig.pose.bones[bname]
            for cns in pb.constraints:
                if cns.type == 'STRETCH_TO':
                    return cns

        def setConnected(rig, bname, value):
            if bname not in rig.data.edit_bones:
                return
            eb = rig.data.edit_bones[bname]
            if isDrvBone(eb.parent.name):
                eb.parent.use_connect = value
            else:
                eb.use_connect = value

        rig = context.object
        amt = rig.data
        if prop in amt.keys():
            wason = amt[prop]
        else:
            wason = True
        cns = getStretchToConstraint(rig, "%s.bend.%s" % (armname, suffix))
        cns.mute = wason
        cns = getStretchToConstraint(rig, "%s.twist.%s" % (armname, suffix))
        cns.mute = wason
        cns = getCopyLocConstraint(rig, "%s.%s" % (handname, suffix))
        if cns:
            cns.mute = (not wason)
            cns = getCopyLocConstraint(rig, "%s.fk.%s" % (handname, suffix))
            cns.mute = (not wason)
        else:
            setMode('EDIT', "Cannot toggle stretch for this armature")
            setConnected(rig, "%s.%s" % (handname, suffix), wason)
            setConnected(rig, "%s.fk.%s" % (handname, suffix), wason)
            setMode('POSE')
        bpy.context.view_layer.update()
        if wason:
            handFk = rig.pose.bones["%s.fk.%s" % (handname, suffix)]
            handFk.location = (0,0,0)
        amt[prop] = not wason


class MHX_OT_MhxToggleLeftArmStretch(MhxOperator, ToggleStretch):
    bl_idname = "mhx.toggle_left_arm_stretch"
    bl_label = "Left Arm"
    bl_description = "Toggle left arm stretchiness"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaArmStretch_L", "forearm", "hand", "L")

class MHX_OT_MhxToggleRightArmStretch(MhxOperator, ToggleStretch):
    bl_idname = "mhx.toggle_right_arm_stretch"
    bl_label = "Right Arm"
    bl_description = "Toggle right arm stretchiness"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaArmStretch_R", "forearm", "hand", "R")

class MHX_OT_MhxToggleLeftLegStretch(MhxOperator, ToggleStretch):
    bl_idname = "mhx.toggle_left_leg_stretch"
    bl_label = "Left Leg"
    bl_description = "Toggle left leg stretchiness"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaLegStretch_L", "shin", "foot", "L")

class MHX_OT_MhxToggleRightLegStretch(MhxOperator, ToggleStretch):
    bl_idname = "mhx.toggle_right_leg_stretch"
    bl_label = "Right Leg"
    bl_description = "Toggle right leg stretchiness"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaLegStretch_R", "shin", "foot", "R")
'''
#----------------------------------------------------------
#   Toggle Toe Tarsal parenting
#----------------------------------------------------------

class ToggleToeTarsal:
    def toggle(self, context, prop, suffix):
        def setConstraint(rig, bname, toename, mute):
            if bname not in rig.pose.bones.keys():
                return
            pb = rig.pose.bones[bname]
            for cns in pb.constraints:
                if (cns.type == 'COPY_ROTATION' and
                    cns.subtarget == toename):
                    cns.mute = mute
                    return
            raise MhxError("Cannot set toe tarsal parents for this rig")

        def setParent(rig, bname, toe, tarsal, wason):
            if bname not in rig.data.edit_bones:
                return
            eb = rig.data.edit_bones[bname]
            if isDrvBone(eb.parent.name):
                eb = eb.parent
            if wason:
                eb.parent = toe
            else:
                eb.parent = tarsal

        rig = context.object
        amt = rig.data
        toename = "toe.%s" % suffix
        tarsalname = "tarsal.%s" % suffix
        if (toename not in amt.bones.keys() or
            tarsalname not in amt.bones.keys()):
            msg = ("Missing bones: %s or %s" % (toename, tarsalname))
            raise MhxError(msg)
        if prop in amt.keys():
            wason = amt[prop]
        else:
            wason = True
        for smallname in ["big_toe", "small_toe_1", "small_toe_2", "small_toe_3", "small_toe_4"]:
            setConstraint(rig, "%s.01.%s" % (smallname, suffix), toename, wason)
        setMode('EDIT', "Cannot toggle toe tarsal parents for this armature")
        toe = amt.edit_bones[toename]
        tarsal = amt.edit_bones[tarsalname]
        for smallname in ["big_toe", "small_toe_1", "small_toe_2", "small_toe_3", "small_toe_4"]:
            setParent(rig, "%s.01.%s" % (smallname, suffix), toe, tarsal, wason)
        setMode('POSE')
        amt[prop] = not wason


class MHX_OT_MhxToggleLeftToeTarsal(MhxOperator, ToggleToeTarsal):
    bl_idname = "mhx.toggle_left_toe_tarsal"
    bl_label = "Left Toe"
    bl_description = "Toggle left small toes parent (toe or tarsal bone)"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaToeTarsal_L", "L")

class MHX_OT_MhxToggleRightToeTarsal(MhxOperator, ToggleToeTarsal):
    bl_idname = "mhx.toggle_right_toe_tarsal"
    bl_label = "Right Toe"
    bl_description = "Toggle right small toes parent (toe or tarsal bone)"
    bl_options = {'UNDO'}

    def run(self, context):
        self.toggle(context, "MhaToeTarsal_R", "R")

#----------------------------------------------------------
#   Toggle forearms follow
#----------------------------------------------------------

def setForearmFollow(amt, context, prop, suffix):
    rig = getMhxRig(amt, context)
    follows = getattr(amt, prop)
    pb = rig.pose.bones["forearm"+suffix]
    for cns in pb.constraints:
        if (cns.type == 'COPY_ROTATION' and
            cns.subtarget in ["hand.fk"+suffix, "hand0.ik"+suffix]):
            cns.mute = not follows
    hand = rig.pose.bones["hand.fk"+suffix]
    for cns in hand.constraints:
        if cns.type == 'LIMIT_ROTATION':
            cns.use_limit_y = not follows
            break
    forearm = rig.pose.bones["forearm.fk"+suffix]
    if follows:
        hand.rotation_euler[1] = forearm.rotation_euler[1]
        forearm.rotation_euler[1] = 0
    else:
        forearm.rotation_euler[1] = hand.rotation_euler[1]
        hand.rotation_euler[1] = 0


def setForearmFollowLeft(amt, context):
    setForearmFollow(amt, context, "MhaForearmFollow_L", ".L")

def setForearmFollowRight(amt, context):
    setForearmFollow(amt, context, "MhaForearmFollow_R", ".R")

#----------------------------------------------------------
#   Toggle limits
#----------------------------------------------------------

def toggleFkIkLimits(amt, context):
    rig = getMhxRig(amt, context)
    for pb in rig.pose.bones:
        for cns in pb.constraints:
            if cns.type == 'LIMIT_ROTATION' and cns.name != "Hint":
                cns.mute = (not amt.MhaLimitsOn)
    for suffix in [".L", ".R"]:
        for bname in ["upper_arm", "forearm", "thigh", "shin"]:
            pb = rig.pose.bones["%s.ik%s" % (bname, suffix)]
            pb.use_ik_limit_x = pb.use_ik_limit_y = pb.use_ik_limit_z = amt.MhaLimitsOn

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
    MHX_OT_MhxToggleFkIkLeftArm,
    MHX_OT_MhxToggleFkIkRightArm,
    MHX_OT_MhxToggleFkIkLeftLeg,
    MHX_OT_MhxToggleFkIkRightLeg,
    MHX_OT_MhxUpdateElbowKneeParents,
    #MHX_OT_MhxToggleLeftArmStretch,
    #MHX_OT_MhxToggleRightArmStretch,
    #MHX_OT_MhxToggleLeftLegStretch,
    #MHX_OT_MhxToggleRightLegStretch,
    MHX_OT_MhxToggleLeftToeTarsal,
    MHX_OT_MhxToggleRightToeTarsal,
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

