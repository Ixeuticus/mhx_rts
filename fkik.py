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
        if bname in self.rig.pose.bones.keys():
            return self.rig.pose.bones[bname]
        else:
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


    def insertScale(self, pb, mat=None):
        if mat:
            pb.location = mat.to_scale()
        if self.auto or isKeyed(self.rig, pb, "scale"):
            pb.keyframe_insert("scale", frame=self.frame, group=pb.name)


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
    "LegIK" : ["thigh.ik", "shin.ik", "thigh.ik.twist", "shin.ik.twist", "knee.pt.ik", "kneePoleA", "foot.2", "ankle.ik", "foot.ik", "foot.rev", "toe.rev", "foot.inv.fk", "toe.inv.fk", "foot.inv.ik", "toe.inv.ik"],
}

class Snapper(Updater, Basic):
    prop2 = None

    def prequel(self, context):
        HideOperator.prequel(self, context)


    def sequel(self, context):
        HideOperator.sequel(self, context)


    def setup(self, context, value, change=True):
        checkVisible(context.object)
        setMode('POSE')
        self.oldvalue = value
        self.auto = context.scene.tool_settings.use_keyframe_insert_auto
        if change:
            setattr(self.rig, self.prop, value)
            if self.prop2:
                setattr(self.rig, self.prop2, 0)
            self.updatePose()


    def setupAll(self, context, value):
        checkVisible(context.object)
        setMode('POSE')
        self.oldvalues = [self.rig.MhaArmIk_L, self.rig.MhaArmIk_R, self.rig.MhaLegIk_L, self.rig.MhaLegIk_R]
        self.rig.MhaArmIk_L = self.rig.MhaArmIk_R = self.rig.MhaLegIk_L = self.rig.MhaLegIk_R = value
        self.auto = context.scene.tool_settings.use_keyframe_insert_auto
        self.updatePose()


    def restore(self, context, value, fk, ik):
        scn = context.scene
        if scn.MhxUseSwitch:
            self.state[self.fk] = fk
            self.state[self.ik] = ik
            if self.prop:
                setattr(self.rig, self.prop, value)
                if self.auto:
                    self.rig.keyframe_insert(self.prop, frame=scn.frame_current)
        elif self.prop:
            setattr(self.rig, self.prop, self.oldvalue)
        self.updatePose()


    def restoreAll(self, context, value, fk, ik):
        scn = context.scene
        if scn.MhxUseSwitch:
            self.rig.MhaArmIk_L = self.rig.MhaArmIk_R = self.rig.MhaLegIk_L = self.rig.MhaLegIk_R = value
            self.state[L_LARMFK] = self.state[L_RARMFK] = self.state[L_LLEGFK] = self.state[L_RLEGFK] = fk
            self.state[L_LARMIK] = self.state[L_RARMIK] = self.state[L_LLEGIK] = self.state[L_RLEGIK] = ik
            if self.auto:
                self.rig.keyframe_insert("MhaArmIk_L", frame=scn.frame_current)
                self.rig.keyframe_insert("MhaArmIk_R", frame=scn.frame_current)
                self.rig.keyframe_insert("MhaLegIk_L", frame=scn.frame_current)
                self.rig.keyframe_insert("MhaLegIk_R", frame=scn.frame_current)
        else:
            self.rig.MhaArmIk_L = self.oldvalues[0]
            self.rig.MhaArmIk_R = self.oldvalues[1]
            self.rig.MhaLegIk_L = self.oldvalues[2]
            self.rig.MhaLegIk_R = self.oldvalues[3]
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
        self.imposeLocks(pb)


    def matchPoseTransform(self, pb, src):
        pb.matrix = src.matrix
        self.updatePose()
        self.imposeLocks(pb)
        self.insertRotation(pb)


    def imposeLocks(self, pb):
        return
        if pb.rotation_mode == 'QUATERNION':
            for idx in range(4):
                if pb.lock_rotation[idx]:
                    pb.rotation_quaternion[idx] = 0
        else:
            for idx in range(3):
                if pb.lock_rotation[idx]:
                    pb.rotation_euler[idx] = 0


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
                  "foot.2" in bname or
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


    def getFingers(self, suffix):
        fkbones = []
        ikbones = []
        for n in range(1,4):
            fklinks = []
            iklinks = []
            for fing in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]:
                fkname = "%s.0%d.%s" % (fing, n, suffix)
                fklinks.append(self.rig.pose.bones[fkname])
                ikname = "ik_%s" % fkname
                iklinks.append(self.rig.pose.bones[ikname])
            fkbones.append(fklinks)
            ikbones.append(iklinks)
        longnames = ["%s.%s" % (fing, suffix) for fing in ["thumb", "index", "middle", "ring", "pinky"]]
        longbones = [self.rig.pose.bones[bname] for bname in longnames]
        return longbones, fkbones, ikbones


    def getTongue(self):
        bnames = [bone.name for bone in self.rig.data.bones if bone.name.startswith("tongue")]
        bnames.sort()
        fkbones = [[self.rig.pose.bones[bname]] for bname in bnames]
        ikbones = [[self.rig.pose.bones["ik_%s" % bname]] for bname in bnames]
        return fkbones, ikbones


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
        self.setChildofInverse(elbowPt)
        if uparmIkTwist:
            self.matchPoseTransform(uparmIkTwist, uparmFk)
            self.matchPoseTransform(forearmIkTwist, forearmFk)


    def setChildofInverse(self, pb):
        for cns in pb.constraints:
            if cns.type == 'CHILD_OF':
                self.rig.data.bones.active = pb.bone
                print("SET INV", pb.name, self.rig.data.bones.active, cns.name)
                bpy.ops.constraint.childof_set_inverse(constraint=cns.name, owner='BONE')
                print("DONE")


    def snapFkLeg(self, snapFk, snapIk, legIkToAnkle):
        (thighFk, shinFk, footFk, toeFk) = snapFk
        (thighIk, shinIk, thighIkTwist, shinIkTwist, kneePt, kneePoleA, foot2, ankleIk, legIk, footRev, toeRev, footInvFk, toeInvFk, footInvIk, toeInvIk) = snapIk

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
        (thighIk, shinIk, thighIkTwist, shinIkTwist, kneePt, kneePoleA, foot2, ankleIk, legIk, footRev, toeRev, footInvFk, toeInvFk, footInvIk, toeInvIk) = snapIk

        footFk.location = (0,0,0)
        if legIkToAnkle and foot2:
            self.matchPoseTransform(foot2, footFk)
            self.matchPoseTransform(toe2, toeFk)
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
        self.setChildofInverse(kneePt)
        if shinIkTwist:
            self.matchPoseTransform(thighIkTwist, thighFk)
            self.matchPoseTransform(shinIkTwist, shinFk)


    def snapFkFingers(self, longbones, fkbones):
        mats = []
        for fklinks in fkbones:
            matlinks = [pb.matrix.copy() for pb in fklinks]
            mats.append(matlinks)
        for pb in longbones:
            pb.rotation_euler = (0,0,0)
        self.updatePose()
        for pb in longbones:
            self.insertRotation(pb)
        for fklinks,matlinks in zip(fkbones, mats):
            for pb,mat in zip(fklinks, matlinks):
                pb.matrix = mat
            self.updatePose()
            for pb in fklinks:
                self.imposeLocks(pb)
                self.insertRotation(pb)
                self.insertScale(pb)


    def snapIkFingers(self, longbones, fkbones, ikbones):
        for fklinks, iklinks in zip(fkbones, ikbones):
            for fkb, ikb in zip(fklinks, iklinks):
                ikb.matrix.col[3][0:3] = fkb.tail
            self.updatePose()
            for ikb in iklinks:
                self.insertLocation(ikb)


class FootSnapper(Snapper):
    useRotation: BoolProperty(
        name = "Rotate IK Foot",
        description = "Also match IK effector rotation.\nSuitable for hand animation",
        default = True)

    def draw(self, context):
        self.layout.prop(self, "useRotation")


#-------------------------------------------------------------
#  Snap FK
#-------------------------------------------------------------

class MHX_OT_MhxSnapFkLeftArm(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_left_arm"
    bl_label = "Snap Left"
    bl_description = "Snap the left FK arm to the pose of the left IK arm"
    bl_options = {'UNDO'}

    suffix = "L"
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

    suffix = "R"
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

    suffix = "L"
    prop = "MhaLegIk_L"
    ik = L_LLEGIK
    fk = L_LLEGFK

    def run(self, context):
        print("Snap Left FK Leg")
        self.setup(context, 1.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "L")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "L")
        self.snapFkLeg(snapFk, snapIk, self.rig.MhaLegIkToAnkle_L)
        self.restore(context, 0.0, True, False)


class MHX_OT_MhxSnapFkRightLeg(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_right_leg"
    bl_label = "Snap Right"
    bl_description = "Snap the right FK leg to the pose of the right IK leg"
    bl_options = {'UNDO'}

    suffix = "R"
    prop = "MhaLegIk_R"
    ik = L_RLEGIK
    fk = L_RLEGFK

    def run(self, context):
        print("Snap Right FK Leg")
        self.setup(context, 1.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "R")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "R")
        self.snapFkLeg(snapFk, snapIk, self.rig.MhaLegIkToAnkle_R)
        self.restore(context, 0.0, True, False)


class MHX_OT_MhxSnapFkAll(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_all"
    bl_label = "Snap FK All"
    bl_description = "Snap all FK limbs to the pose of IK limbs"
    bl_options = {'UNDO'}

    def run(self, context):
        print("Snap FK All")
        self.setupAll(context, 1.0)

        self.prop = "MhaArmIk_L"
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "L")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "L")
        self.snapFkArm(snapFk, snapIk)

        self.prop = "MhaArmIk_R"
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "R")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "R")
        self.snapFkArm(snapFk, snapIk)

        self.prop = "MhaLegIk_L"
        snapFk,_cnsFk = self.getSnapBones("LegFK", "L")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "L")
        self.snapFkLeg(snapFk, snapIk, self.rig.MhaLegIkToAnkle_L)

        self.prop = "MhaLegIk_R"
        snapFk,_cnsFk = self.getSnapBones("LegFK", "R")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "R")
        self.snapFkLeg(snapFk, snapIk, self.rig.MhaLegIkToAnkle_R)

        self.restoreAll(context, 0.0, True, False)

#-------------------------------------------------------------
#  Snap IK
#-------------------------------------------------------------

class MHX_OT_MhxSnapIkLeftArm(Snapper, HideOperator):
    bl_idname = "mhx.snap_ik_left_arm"
    bl_label = "Snap Left"
    bl_description = "Snap the left IK arm to the pose of the left FK arm"
    bl_options = {'UNDO'}

    suffix = "L"
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

    suffix = "R"
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

    suffix = "L"
    prop = "MhaLegIk_L"
    prop2 = "MhaLegIkToAnkle_L"
    ik = L_LLEGIK
    fk = L_LLEGFK

    def run(self, context):
        print("Snap Left IK Leg")
        self.useRotation = context.scene.MhxUseSnapRotation
        self.setup(context, 0.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "L")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "L")
        self.snapIkLeg(snapFk, snapIk, self.rig.MhaLegIkToAnkle_L)
        self.restore(context, 1.0, False, True)


class MHX_OT_MhxSnapIkRightLeg(FootSnapper, HideOperator):
    bl_idname = "mhx.snap_ik_right_leg"
    bl_label = "Snap Right"
    bl_description = "Snap the right IK leg to the pose of the right FK leg"
    bl_options = {'UNDO'}

    suffix = "R"
    prop = "MhaLegIk_R"
    prop2 = "MhaLegIkToAnkle_R"
    ik = L_RLEGIK
    fk = L_RLEGFK

    def run(self, context):
        print("Snap Right IK Leg")
        self.useRotation = context.scene.MhxUseSnapRotation
        self.setup(context, 0.0)
        snapFk,_cnsFk = self.getSnapBones("LegFK", "R")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "R")
        self.snapIkLeg(snapFk, snapIk, self.rig.MhaLegIkToAnkle_R)
        self.restore(context, 1.0, False, True)


class MHX_OT_MhxSnapIkAll(FootSnapper, HideOperator):
    bl_idname = "mhx.snap_ik_all"
    bl_label = "Snap IK All"
    bl_description = "Snap all IK limbs to the pose of FK limbs"
    bl_options = {'UNDO'}

    def run(self, context):
        print("Snap IK All")
        self.setupAll(context, 0.0)

        self.prop = "MhaArmIk_L"
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "L")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "L")
        self.snapIkArm(snapFk, snapIk)

        self.prop = "MhaArmIk_R"
        snapFk,_cnsFk = self.getSnapBones("ArmFK", "R")
        snapIk,_cnsIk = self.getSnapBones("ArmIK", "R")
        self.snapIkArm(snapFk, snapIk)

        self.useRotation = context.scene.MhxUseSnapRotation
        self.prop = "MhaLegIk_L"
        snapFk,_cnsFk = self.getSnapBones("LegFK", "L")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "L")
        self.snapIkLeg(snapFk, snapIk, self.rig.MhaLegIkToAnkle_L)

        self.prop = "MhaLegIk_R"
        snapFk,_cnsFk = self.getSnapBones("LegFK", "R")
        snapIk,_cnsIk = self.getSnapBones("LegIK", "R")
        self.snapIkLeg(snapFk, snapIk, self.rig.MhaLegIkToAnkle_R)

        self.restoreAll(context, 1.0, False, True)

#-------------------------------------------------------------
#  Snap fingers
#-------------------------------------------------------------

class MHX_OT_MhxSnapFkLeftFingers(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_left_fingers"
    bl_label = "Snap Left"
    bl_description = "Snap the left FK fingers to the pose of the left FK fingers"
    bl_options = {'UNDO'}

    suffix = "L"
    prop = "MhaFingerIk_L"
    fk = L_LHAND
    ik = L_LHAND

    def run(self, context):
        print("Snap Left FK Fingers")
        self.setup(context, 1.0, change=False)
        longbones, fkbones,ikbones = self.getFingers("L")
        self.snapFkFingers(longbones, fkbones)
        self.restore(context, 0.0, True, True)


class MHX_OT_MhxSnapFkRightFingers(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_right_fingers"
    bl_label = "Snap Right"
    bl_description = "Snap the right FK fingers to the pose of the right FK fingers"
    bl_options = {'UNDO'}

    suffix = "R"
    prop = "MhaFingerIk_R"
    fk = L_RHAND
    ik = L_RHAND

    def run(self, context):
        print("Snap Right FK Fingers")
        self.setup(context, 1.0, change=False)
        longbones, fkbones,ikbones = self.getFingers("R")
        self.snapFkFingers(longbones, fkbones)
        self.restore(context, 0.0, True, True)


class MHX_OT_MhxSnapIkLeftFingers(Snapper, HideOperator):
    bl_idname = "mhx.snap_ik_left_fingers"
    bl_label = "Snap Left"
    bl_description = "Snap the left IK fingers to the pose of the left FK fingers"
    bl_options = {'UNDO'}

    suffix = "L"
    prop = "MhaFingerIk_L"
    ik = L_LHAND
    fk = L_LHAND

    def run(self, context):
        print("Snap Left IK Fingers")
        self.setup(context, 0.0, change=False)
        longbones, fkbones,ikbones = self.getFingers("L")
        self.snapIkFingers(longbones, fkbones, ikbones)
        self.restore(context, 1.0, True, True)


class MHX_OT_MhxSnapIkRightFingers(Snapper, HideOperator):
    bl_idname = "mhx.snap_ik_right_fingers"
    bl_label = "Snap Right"
    bl_description = "Snap the right IK fingers to the pose of the right FK fingers"
    bl_options = {'UNDO'}

    suffix = "R"
    prop = "MhaFingerIk_R"
    ik = L_RHAND
    fk = L_RHAND

    def run(self, context):
        print("Snap Right IK Fingers")
        self.setup(context, 0.0, change=False)
        longbones, fkbones,ikbones = self.getFingers("R")
        self.snapIkFingers(longbones, fkbones, ikbones)
        self.restore(context, 1.0, True, True)

#-------------------------------------------------------------
#  Snap tongues
#-------------------------------------------------------------

class MHX_OT_MhxSnapFkTongue(Snapper, HideOperator):
    bl_idname = "mhx.snap_fk_tongue"
    bl_label = "Snap FK Tongue"
    bl_description = "Snap the FK tongue to the pose of the IK tongue"
    bl_options = {'UNDO'}

    suffix = ""
    prop = "MhaTongueIk"
    fk = L_FACE
    ik = L_HEAD

    def run(self, context):
        print("Snap FK Tongue")
        self.setup(context, 1.0, change=False)
        fkbones,ikbones = self.getTongue()
        self.snapFkFingers([], fkbones)
        self.restore(context, 0.0, True, True)


class MHX_OT_MhxSnapIkTongue(Snapper, HideOperator):
    bl_idname = "mhx.snap_ik_tongue"
    bl_label = "Snap IK Tongue"
    bl_description = "Snap the IK tongue to the pose of the FK tongue"
    bl_options = {'UNDO'}

    suffix = ""
    prop = "MhaTongueIk"
    fk = L_FACE
    ik = L_HEAD

    def run(self, context):
        print("Snap FK Tongue")
        self.setup(context, 0.0, change=False)
        fkbones,ikbones = self.getTongue()
        self.snapIkFingers([], fkbones, ikbones)
        self.restore(context, 1.0, True, True)

#-------------------------------------------------------------
#  Snap back and neck-head
#-------------------------------------------------------------

class MHX_OT_MhxSnapSpine(Snapper, HideOperator):
    bl_idname = "mhx.snap_spine"
    bl_label = "Snap Spine"
    bl_description = "Snap the spine bones and clear the back bone"
    bl_options = {'UNDO'}

    suffix = ""
    prop = ""
    fk = L_SPINE
    ik = L_MAIN

    def run(self, context):
        print("Snap spine")
        self.setup(context, 1.0, change=False)
        bnames = ["spine", "spine-1", "chest", "chest-1"]
        bones = [self.rig.pose.bones.get(bname) for bname in bnames]
        bones = [[bone] for bone in bones if bone]
        back = self.rig.pose.bones["back"]
        self.snapFkFingers([back], bones)
        self.restore(context, 0.0, True, True)


class MHX_OT_MhxSnapNeckHead(Snapper, HideOperator):
    bl_idname = "mhx.snap_neck_head"
    bl_label = "Snap Neck Head"
    bl_description = "Snap the neck and head bones and clear the neckhead bone"
    bl_options = {'UNDO'}

    suffix = ""
    prop = ""
    fk = L_SPINE
    ik = L_MAIN

    def run(self, context):
        print("Snap neck and head")
        self.setup(context, 1.0, change=False)
        bnames = ["neck", "neck-1", "head"]
        bones = [self.rig.pose.bones.get(bname) for bname in bnames]
        bones = [[bone] for bone in bones if bone]
        neckhead = self.rig.pose.bones["neckhead"]
        self.snapFkFingers([neckhead], bones)
        self.restore(context, 0.0, True, True)

#----------------------------------------------------------
#   Toggle FK - IK
#----------------------------------------------------------

class ToggleFkIk(Updater):
    def toggle(self, context, prop, fklayer, iklayer):
        rig = context.object
        checkVisible(rig)
        scn = context.scene
        value = getattr(rig, prop)
        if value > 0.5:
            value = 0.0
            fk = True
            ik = False
        else:
            value = 1.0
            fk = False
            ik = True
        setattr(rig, prop, value)
        rig.data.layers[fklayer] = fk
        rig.data.layers[iklayer] = ik
        if (scn.tool_settings.use_keyframe_insert_auto or
            isKeyed(rig, None, prop)):
            rig.keyframe_insert(prop, frame=scn.frame_current)
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
        self.toggle(context, "MhaKneeParent_L", "knee.pt.ik.L", "kneePoleP.L",  "hip")
        self.toggle(context, "MhaKneeParent_R", "knee.pt.ik.R", "kneePoleP.R",  "hip")

    def toggle(self, context, prop, bname, polep, limbpar):
        rig = context.object
        pb = rig.pose.bones[bname]
        wmat = pb.matrix.copy()
        setMode('EDIT', "Cannot set elbow and knee parents for this armature")
        partype = getattr(rig, prop)
        if partype in ['HAND', 'FOOT']:
            parname = polep
        elif partype in ['SHOULDER', 'HIP']:
            parname = limbpar
        elif partype == 'MASTER':
            parname = 'master'
        eb = rig.data.edit_bones[bname]
        eb.parent = rig.data.edit_bones[parname]
        bpy.ops.object.mode_set(mode='POSE')
        pb = rig.pose.bones[bname]
        pb.matrix = wmat

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
        toename = "toe.%s" % suffix
        tarsalname = "tarsal.%s" % suffix
        if (toename not in rig.data.bones.keys() or
            tarsalname not in rig.data.bones.keys()):
            msg = ("Missing bones: %s or %s" % (toename, tarsalname))
            raise MhxError(msg)
        wason = getattr(rig, prop)
        for smallname in ["big_toe", "small_toe_1", "small_toe_2", "small_toe_3", "small_toe_4"]:
            setConstraint(rig, "%s.01.%s" % (smallname, suffix), toename, wason)
        setMode('EDIT', "Cannot toggle toe tarsal parents for this armature")
        toe = rig.data.edit_bones[toename]
        tarsal = rig.data.edit_bones[tarsalname]
        for smallname in ["big_toe", "small_toe_1", "small_toe_2", "small_toe_3", "small_toe_4"]:
            setParent(rig, "%s.01.%s" % (smallname, suffix), toe, tarsal, wason)
        setMode('POSE')
        setattr(rig, prop, (not wason))


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
#   Toggle limits
#----------------------------------------------------------

class MHX_OT_MhxToggleLimits(MhxOperator):
    bl_idname = "mhx.toggle_limits"
    bl_label = "Limits"
    bl_description = "Toggle limit constraints (location, rotation, scale)"

    def run(self, context):
        rig = context.object
        rig.MhaLimitsOn = (not rig.MhaLimitsOn)
        for pb in rig.pose.bones:
            for cns in pb.constraints:
                if cns.type[0:6] == 'LIMIT_' and cns.name != "Hint":
                    cns.mute = (not rig.MhaLimitsOn)
        for suffix in ["L", "R"]:
            for bname in ["upper_arm", "forearm", "thigh", "shin"]:
                pb = rig.pose.bones["%s.ik.%s" % (bname, suffix)]
                pb.use_ik_limit_x = pb.use_ik_limit_y = pb.use_ik_limit_z = rig.MhaLimitsOn

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MHX_OT_MhxSnapFkLeftArm,
    MHX_OT_MhxSnapFkRightArm,
    MHX_OT_MhxSnapFkLeftLeg,
    MHX_OT_MhxSnapFkRightLeg,
    MHX_OT_MhxSnapFkAll,
    MHX_OT_MhxSnapIkLeftArm,
    MHX_OT_MhxSnapIkRightArm,
    MHX_OT_MhxSnapIkLeftLeg,
    MHX_OT_MhxSnapIkRightLeg,
    MHX_OT_MhxSnapIkAll,
    MHX_OT_MhxSnapFkLeftFingers,
    MHX_OT_MhxSnapFkRightFingers,
    MHX_OT_MhxSnapIkLeftFingers,
    MHX_OT_MhxSnapIkRightFingers,
    MHX_OT_MhxSnapFkTongue,
    MHX_OT_MhxSnapIkTongue,
    MHX_OT_MhxSnapSpine,
    MHX_OT_MhxSnapNeckHead,
    MHX_OT_MhxToggleFkIkLeftArm,
    MHX_OT_MhxToggleFkIkRightArm,
    MHX_OT_MhxToggleFkIkLeftLeg,
    MHX_OT_MhxToggleFkIkRightLeg,
    MHX_OT_MhxUpdateElbowKneeParents,
    MHX_OT_MhxToggleLeftToeTarsal,
    MHX_OT_MhxToggleRightToeTarsal,
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

