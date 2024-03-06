# Copyright (c) 2016-2024, Thomas Larsson
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
from bpy.props import *
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
            pb.scale = mat.to_scale()
        if self.auto or isKeyed(self.rig, pb, "scale"):
            pb.keyframe_insert("scale", frame=self.frame, group=pb.name)


    def insertRotation(self, pb, mat=None):
        if mat:
            if pb.rotation_mode == 'QUATERNION':
                pb.rotation_quaternion = mat.to_quaternion()
            else:
                pb.rotation_euler = mat.to_euler(pb.rotation_mode)
        channel = self.getTrueChannel(pb, "rotation")
        if self.auto or isKeyed(self.rig, pb, channel):
            pb.keyframe_insert(channel, frame=self.frame, group=pb.name)


    def findBoneFCurves(self, pb, channel):
        if self.rig.animation_data is None:
            return []
        act = self.rig.animation_data.action
        if act is None:
            return []
        path = 'pose.bones["%s"].%s' % (pb.name, self.getTrueChannel(pb, channel))
        return [fcu for fcu in act.fcurves if fcu.data_path == path]


    def getTrueChannel(self, pb, channel):
        if channel == "rotation":
            if pb.rotation_mode == 'QUATERNION':
                return "rotation_quaternion"
            else:
                return "rotation_euler"
        else:
            return channel


    def findBoneFCurve(self, pb, channel, idx):
        for fcu in self.findBoneFCurves(pb, channel):
            if fcu.array_index == idx:
                return fcu
        #print('F-curve %s[%d] for "%s" not found.' % (channel, idx, pb.name))
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
        rig = context.object
        scn = context.scene
        checkVisible(rig)
        setMode('OBJECT')
        self.oldvalue = value
        self.auto = scn.tool_settings.use_keyframe_insert_auto
        if change:
            setattr(self.rig, self.prop, value)
            if self.prop2:
                setattr(self.rig, self.prop2, 0)
            self.updatePose()


    def setupAll(self, context, value):
        checkVisible(context.object)
        setMode('OBJECT')
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


    def setWorldMatrix(self, gmat, pb, useLoc=False, useRot=False):
        pb.matrix = gmat
        self.updatePose()
        if useLoc:
            self.insertLocation(pb)
        if useRot:
            self.insertRotation(pb)


    def setLocalMatrix(self, lmat, pb, useLoc=False, useRot=False):
        pb.matrix_basis = lmat
        if useLoc:
            self.insertLocation(pb)
        if useRot:
            self.insertRotation(pb)
        self.updatePose()


    def matchRotation(self, pb, src):
        if pb is None:
            return
        self.setWorldMatrix(src.matrix, pb, False, True)


    def imposeLocks(self, pb):
        return
        for idx in range(3):
            if pb.lock_location[idx]:
                pb.location[idx] = 0
        if pb.rotation_mode != 'QUATERNION':
            for idx in range(3):
                if pb.lock_rotation[idx]:
                    pb.rotation_euler[idx] = 0
        for idx in range(3):
            if pb.lock_scale[idx]:
                pb.scale[idx] = 1


    def matchIkLeg(self, legIk, toeFk):
        # No x and y rotation for Leg IK target
        tHead = toeFk.matrix.to_translation()
        tTail = tHead + toeFk.y_axis * toeFk.bone.length
        if self.useRotation:
            y = tTail - tHead
            y.normalize()
            z = toeFk.z_axis
            x = y.cross(z)
            gmat = Matrix((x,y,z))
            gmat.transpose()
        else:
            gmat = legIk.bone.matrix_local.to_3x3()
            y = gmat.col[1]
        head = tTail - y * legIk.bone.length
        gmat = gmat.to_4x4()
        gmat.col[3][:3] = head
        self.setWorldMatrix(gmat, legIk, True, True)


    def matchPoleTarget(self, pb, above, below):
        ay = above.y_axis
        by = below.y_axis
        az = above.z_axis
        bz = below.z_axis
        p0 = below.matrix.to_translation()
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
        self.setWorldMatrix(Matrix.Translation(p), pb, True, False)

    #
    # https://bitbucket.org/Diffeomorphic/import_daz/issues/528/mhx-snap-ik-to-fk-can-set-pole-more
    #
    def setPoleTarget(self, hand, poleTrg, poleA, forearm):
        self.setLocalMatrix(Matrix(), poleA, False, True)
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
        pos = Matrix.Translation(pole_vec) @ poleA.matrix
        self.setWorldMatrix(pos, poleTrg, True, False)
        poleTrg.rotation_euler = (0.0, 0.0, 0.0)


    def matchPoseReverse(self, pb, src):
        gmat = src.matrix
        tail = gmat.col[3] + src.length * gmat.col[1]
        rmat = Matrix((gmat.col[0], -gmat.col[1], -gmat.col[2], tail))
        rmat.transpose()
        self.setWorldMatrix(rmat, pb, False, True)


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
                  "ik.twist" in bname or
                  "pt.ik" in bname):
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
            self.matchRotation(uparmFk, uparmIkTwist)
        else:
            self.matchRotation(uparmFk, uparmIk)
        if forearmIkTwist:
            self.matchRotation(forearmFk, forearmIkTwist)
        else:
            self.matchRotation(forearmFk, forearmIk)
        self.matchRotation(handFk, handIk)


    def snapIkArm(self, snapFk, snapIk):
        (uparmFk, forearmFk, handFk) = snapFk
        (uparmIk, forearmIk, uparmIkTwist, forearmIkTwist, elbowPt, elbowPoleA, handIk) = snapIk

        handFk.location = (0,0,0)
        self.setWorldMatrix(handFk.matrix, handIk, True, True)
        if elbowPt:
            if False and elbowPoleA:
                self.setPoleTarget(handIk, elbowPt, elbowPoleA, forearmFk)
            else:
                self.matchPoleTarget(elbowPt, uparmFk, forearmFk)
        self.matchRotation(uparmIkTwist, uparmFk)
        self.matchRotation(forearmIkTwist, forearmFk)


    def snapFkLeg(self, snapFk, snapIk, legIkToAnkle):
        (thighFk, shinFk, footFk, toeFk) = snapFk
        (thighIk, shinIk, thighIkTwist, shinIkTwist, kneePt, kneePoleA, foot2, ankleIk, legIk, footRev, toeRev, footInvFk, toeInvFk, footInvIk, toeInvIk) = snapIk

        if thighIkTwist:
            self.matchRotation(thighFk, thighIkTwist)
        else:
            self.matchRotation(thighFk, thighIk)
        if shinIkTwist:
            self.matchRotation(shinFk, shinIkTwist)
        else:
            self.matchRotation(shinFk, shinIk)
        if not legIkToAnkle:
            self.matchRotation(footFk, footInvIk)
            self.matchRotation(toeFk, toeInvIk)


    def snapIkLeg(self, snapFk, snapIk, legIkToAnkle):
        (thighFk, shinFk, footFk, toeFk) = snapFk
        (thighIk, shinIk, thighIkTwist, shinIkTwist, kneePt, kneePoleA, foot2, ankleIk, legIk, footRev, toeRev, footInvFk, toeInvFk, footInvIk, toeInvIk) = snapIk

        footFk.location = (0,0,0)
        if legIkToAnkle and foot2:
            self.matchRotation(foot2, footFk)
            self.matchRotation(toe2, toeFk)
        else:
            self.matchIkLeg(legIk, toeFk)
            if toeInvFk:
                self.matchRotation(toeRev, toeInvFk)
                self.matchRotation(footRev, footInvFk)
            else:
                self.matchPoseReverse(toeRev, toeFk)
                self.matchPoseReverse(footRev, footFk)
            self.setWorldMatrix(footFk.matrix, ankleIk, True, False)
        if kneePt:
            if kneePoleA:
                self.setPoleTarget(footInvIk, kneePt, kneePoleA, shinFk)
            else:
                self.matchPoleTarget(kneePt, thighFk, shinFk)
        self.matchRotation(thighIkTwist, thighFk)
        self.matchRotation(shinIkTwist, shinFk)


    Fingers = ["thumb", "index", "middle", "ring", "pinky"]
    F_Fingers = ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]

    def snapLinks(self, context, info, prop):
        self.setup(context, 0, change=False)
        fkbones, pboness, matss = self.getBonesMatrices(info)
        self.updatePose()
        self.clearFkIkBones(info, fkbones)
        setattr(self.rig, prop, False)
        self.updatePose()
        self.setLinkBones(pboness, matss)


    def getBonesMatrices(self, info):
        fknames, iknames, bnamess = info
        pboness = []
        matss = []
        fkbones = []
        for fkname,bnames in zip(fknames, bnamess):
            pbones = [self.rig.pose.bones.get(bname) for bname in bnames]
            pbones = [pb for pb in pbones if pb]
            defbones = [self.rig.pose.bones.get("DEF-%s" % pb.name) for pb in pbones]
            if not defbones:
                continue
            elif defbones[0]:
                mats = [pb.matrix.copy() for pb in defbones]
            else:
                mats = [pb.matrix.copy() for pb in pbones]
            fkbone = self.rig.pose.bones.get(fkname)
            if fkbone is None:
                continue
            pboness.append(pbones)
            matss.append(mats)
            fkbones.append(fkbone)
        return fkbones, pboness, matss


    def clearFkIkBones(self, info, fkbones):
        fknames, iknames, bnamess = info
        for fkname,ikname,fkbone in zip(fknames,iknames,fkbones):
            fkbone.matrix_basis = Matrix()
            self.insertLocation(fkbone)
            self.insertRotation(fkbone)
            self.insertScale(fkbone)
            ikbone = self.rig.pose.bones.get(ikname)
            if ikbone:
                ikbone.matrix_basis = Matrix()
                self.insertLocation(ikbone)
                self.insertRotation(ikbone)
                self.insertScale(ikbone)


    def setLinkBones(self, pboness, matss):
        if not pboness:
            return
        nlinks = len(pboness[0])
        for n in range(nlinks):
            for pbones,mats in zip(pboness, matss):
                self.setWorldMatrix(mats[n], pbones[n])
        for pbones in pboness:
            for pb in pbones:
                self.imposeLocks(pb)
                self.insertLocation(pb)
                self.insertRotation(pb)
                self.insertScale(pb)


    def snapReverse(self, bone, revbone):
        bone.matrix = revbone.matrix
        self.insertLocation(bone)
        self.insertRotation(bone)
        self.insertScale(bone)


    def getFingerInfo(self, suffix):
        fknames = []
        iknames = []
        pboness = []
        for fing,ffing in zip(self.Fingers, self.F_Fingers):
            fknames.append( "%s.%s" % (fing, suffix) )
            iknames.append( "%s.ik.%s" % (fing, suffix))
            pboness.append( ["%s.0%d.%s" % (ffing, n, suffix) for n in range(1,4)] )
        return fknames, iknames, pboness


    def getNeckHeadInfo(self):
        return ["neckhead"], ["ik_neck"], [["neck", "neck-1", "head"]]


    def getSpineInfo(self):
        return ["back"], ["ik_back"], [["spine", "spine-1", "chest", "chest-1"]]


    def getTongueInfo(self, rig):
        def isTongue(bname):
            return (bname.lower()[0:6] == "tongue" and bname[6:].isdigit())

        tonguebones = [bone.name for bone in rig.data.bones if isTongue(bone.name)]
        tonguebones.sort()
        return ["tongue"], ["ik_tongue"], [tonguebones]


    def getShaftInfo(self, rig):
        def isShaft(bname):
            return (bname.lower()[0:5] == "shaft" and bname[5:].isdigit())

        shaftbones = [bone.name for bone in rig.data.bones if isShaft(bone.name)]
        shaftbones.sort()
        return ["shaft"], ["ik_shaft"], [shaftbones]



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
    bl_label = "Snap FK"
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
    bl_label = "Snap FK"
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
    bl_label = "Snap FK"
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
    bl_label = "Snap FK"
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
    bl_label = "Snap IK"
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
    bl_label = "Snap IK"
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
    bl_label = "Snap IK"
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
    bl_label = "Snap IK"
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
#  Snap back and neck-head
#-------------------------------------------------------------

class MHX_OT_MhxSnapReverse(Snapper, HideOperator):
    bl_idname = "mhx.snap_reverse"
    bl_label = "Snap Reverse"
    bl_description = "Snap bone to reversed bone"
    bl_options = {'UNDO'}

    prop : StringProperty()
    value : FloatProperty()
    bonename : StringProperty()
    revname : StringProperty()
    fk : IntProperty()
    ik : IntProperty()

    def run(self, context):
        print("Snap %s to %s" % (self.bonename, self.revname))
        self.setup(context, 1-self.value, change=False)
        bone = self.rig.pose.bones[self.bonename]
        revbone = self.rig.pose.bones[self.revname]
        self.snapReverse(bone, revbone)
        self.restore(context, self.value, True, True)


class MHX_OT_MhxSnapFingers(Snapper, HideOperator):
    bl_idname = "mhx.snap_fingers"
    bl_label = "Snap Fingers"
    bl_description = "Snap finger links"
    bl_options = {'UNDO'}

    suffix : StringProperty()

    def run(self, context):
        prop = "MhaFingerControl_%s" % self.suffix
        self.snapLinks(context, self.getFingerInfo(self.suffix), prop)


class MHX_OT_MhxSnapSpine(Snapper, HideOperator):
    bl_idname = "mhx.snap_spine"
    bl_label = "Snap Spine"
    bl_description = "Snap the spine bones and clear the back bone"
    bl_options = {'UNDO'}

    def run(self, context):
        print("Snap neck and head")
        self.snapLinks(context, self.getNeckHeadInfo(), "MhaNeckControl")
        print("Snap spine")
        self.snapLinks(context, self.getSpineInfo(), "MhaSpineControl")


class MHX_OT_MhxSnapTongue(Snapper, HideOperator):
    bl_idname = "mhx.snap_tongue"
    bl_label = "Snap Tongue"
    bl_description = "Snap the tongue links and clear the tongue bone"
    bl_options = {'UNDO'}

    def run(self, context):
        print("Snap tongue")
        self.snapLinks(context, self.getTongueInfo(context.object), "MhaTongueControl")


class MHX_OT_MhxSnapShaft(Snapper, HideOperator):
    bl_idname = "mhx.snap_shaft"
    bl_label = "Snap Shaft"
    bl_description = "Snap the shaft links and clear the shaft bone"
    bl_options = {'UNDO'}

    def run(self, context):
        print("Snap shaft")
        self.snapLinks(context, self.getShaftInfo(context.object), "MhaShaftControl")

#----------------------------------------------------------
#   Clear Fingers and Feet
#----------------------------------------------------------

class FootClearer:
    def run(self, context):
        rig = context.object
        scn = context.scene
        auto = scn.tool_settings.use_keyframe_insert_auto
        frame = scn.frame_current
        unit = Matrix()
        for pb in rig.pose.bones:
            if (pb.name.startswith(self.clearBones) and
                not pb.name.startswith(self.skipBones)):
                pb.matrix_basis = unit
                if auto or isKeyed(rig, pb, "location"):
                    pb.keyframe_insert("location", frame=frame, group=pb.name)
                if auto or isKeyed(rig, pb, "scale"):
                    pb.keyframe_insert("scale", frame=frame, group=pb.name)
                if pb.rotation_mode == 'QUATERNION':
                    if auto or isKeyed(rig, pb, "rotation_quaternion"):
                        pb.keyframe_insert("rotation_quaternion", frame=frame, group=pb.name)
                else:
                    if auto or isKeyed(rig, pb, "rotation_euler"):
                       pb.keyframe_insert("rotation_euler", frame=frame, group=pb.name)


class MHX_OT_MhxClearFeet(FootClearer, HideOperator):
    bl_idname = "mhx.clear_feet"
    bl_label = "Clear Feet"
    bl_description = "Clear pose for feet and toes"
    bl_options = {'UNDO'}

    clearBones = ("foot", "toe", "tarsal", "big_toe", "small_toe", "reverse")
    skipBones = ("foot.ik")


class MHX_OT_MhxClearFingers(FootClearer, HideOperator):
    bl_idname = "mhx.clear_fingers"
    bl_label = "Clear Fingers"
    bl_description = "Clear pose for fingers"
    bl_options = {'UNDO'}

    clearBones = ("fingers", "thumb", "index", "middle", "ring", "pinky",
                  "f_index", "f_middle", "f_ring", "f_pinky")
    skipBones = ("hand.ik")

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
        if fklayer != iklayer:
            setRigLayer(rig, fklayer, fk)
            setRigLayer(rig, iklayer, ik)
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
        pb = rig.pose.bones.get(bname)
        msg = "Cannot set elbow and knee parents for this armature"
        if pb is None:
            raise MhxError(msg)
        wmat = pb.matrix.copy()
        setMode('EDIT', msg)
        partype = getattr(rig, prop)
        if partype in ['HAND', 'FOOT']:
            parname = polep
        elif partype in ['SHOULDER', 'HIP']:
            parname = limbpar
        elif partype == 'MASTER':
            parname = 'master'
        eb = rig.data.edit_bones[bname]
        eb.parent = rig.data.edit_bones[parname]
        bpy.ops.object.mode_set(mode='OBJECT')
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
        setMode('OBJECT')
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
    MHX_OT_MhxSnapReverse,
    MHX_OT_MhxSnapFingers,
    MHX_OT_MhxSnapSpine,
    MHX_OT_MhxSnapTongue,
    MHX_OT_MhxSnapShaft,
    MHX_OT_MhxClearFeet,
    MHX_OT_MhxClearFingers,
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

