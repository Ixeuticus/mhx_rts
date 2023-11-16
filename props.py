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
from .utils import *
from .layers import *
from .runtime.properties import initMhxProps

# ---------------------------------------------------------------------
#   Convert MHX actions from legacy to modern
# ---------------------------------------------------------------------

class MHX_OT_UpdateMhxBlender4(MhxOperator):
    bl_idname = "mhx.update_mhx_blender4"
    bl_label = "Update MHX To Blender 4"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        for coll in list(rig.data.collections):
            if not coll.name.startswith("Layer "):
                rig.data.collections.remove(coll)
        for idx,cname in MhxLayers.items():
            coll = rig.data.collections.get("Layer %d" % (idx+1))
            if coll:
                coll.name = cname
        for cname in MhxLayers.values():
            if cname not in rig.data.collections.keys():
                coll = rig.data.collections.new(cname)

# ---------------------------------------------------------------------
#   Convert MHX actions from legacy to modern
# ---------------------------------------------------------------------

class MHX_OT_ConvertMhxActions(MhxOperator):
    bl_idname = "mhx.convert_mhx_actions"
    bl_label = "Convert MHX Actions"
    bl_description = "Convert actions between legacy MHX (root/hips) and modern MHX (hip/pelvis)"
    bl_options = {'UNDO'}

    direction : bpy.props.EnumProperty(
        items = [
            ('MODERN', "Legacy => Modern", "Convert from legacy MHX (root/hips) to modern MHX (hip/pelvis)"),
            ('LEGACY', "Modern => Legacy", "Convert from modern MHX (hip/pelvis) to legacy MHX (root/hips)"),
        ],
        name = "Direction",
        default = 'MODERN'
    )

    def draw(self, context):
        self.layout.prop(self, "direction")


    def run(self, context):
        if self.direction == 'MODERN':
            replace = {
                '"root"' : '"hip"',
                '"hips"' : '"pelvis"',
            }
        else:
            replace = {
                '"hip"' : '"root"',
                '"pelvis"' : '"hips"',
            }
        for item in self.getSelectedItems():
            act = bpy.data.actions[item.name]
            for fcu in act.fcurves:
                for old,new in replace.items():
                    if old in fcu.data_path:
                        fcu.data_path = fcu.data_path.replace(old, new)


    def invoke(self, context, event):
        self.selection.clear()
        for act in bpy.data.actions:
            item = self.selection.add()
            item.name = act.name
            item.text = act.name
            item.select = False
        return self.invokeDialog(context)

#-------------------------------------------------------------
#   Enable and disable layers
#-------------------------------------------------------------

def setRigLayer(rig, idx, value):
    if bpy.app.version < (4,0,0):
        rig.data.layers[idx] = value
    else:
        coll = rig.data.collections.get(MhxLayers[idx])
        if coll:
            coll.is_visible = value


class MHX_OT_EnableAllLayers(MhxOperator):
    bl_idname = "mhx.enable_all_layers"
    bl_label = "Enable all layers"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        for idx in MhxLayers.keys():
            if idx not in [L_HELP, L_HELP2, L_FIN, L_DEF]:
                setRigLayer(rig, idx, True)



class MHX_OT_DisableAllLayers(MhxOperator):
    bl_idname = "mhx.disable_all_layers"
    bl_label = "Disable all layers"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        if bpy.app.version < (4,0,0):
            layers = 32*[False]
            pb = context.active_pose_bone
            if pb:
                for n in range(32):
                    if pb.bone.layers[n]:
                        layers[n] = True
                        break
            else:
                layers[0] = True
            rig.data.layers = layers
        else:
            for coll in rig.data.collections:
                coll.is_visible = False

#-------------------------------------------------------------
#   Update MHX
#-------------------------------------------------------------

class MHX_OT_UpdateMhx(MhxOperator):
    bl_idname = "mhx.update_mhx"
    bl_label = "Update MHX"
    bl_options = {'UNDO'}

    def run(self, context):
        def fixFcurve(fcu, rig):
            for var in list(fcu.driver.variables):
                trg = var.targets[0]
                prop = baseRef(trg.data_path)
                if trg.id == rig.data and prop[0:3] == "Mha" and prop in rig.data.keys():
                    value = getValue(prop, rig.data[prop])
                    if hasattr(rig, prop):
                        setattr(rig, prop, value)
                        nvar = fcu.driver.variables.new()
                        varname = var.name
                        ntrg = nvar.targets[0]
                        ntrg.id_type == 'OBJECT'
                        ntrg.id = rig
                        ntrg.data_path = propRef(prop)
                        fcu.driver.variables.remove(var)
                        nvar.name = varname
                    else:
                        rig[prop] = value
                elif trg.id == rig and prop[0:3] == "Mha" and hasattr(rig, prop):
                    value = getValue(prop, getattr(rig, prop))
                    if hasattr(rig, prop):
                        for trg in var.targets:
                            trg.data_path = propRef(prop)
                    else:
                        rig[prop] = value

        def getValue(key, value):
            if key.startswith("MhaElbowParent") and isinstance(value, int):
                return {0: 'HAND', 1: 'SHOULDER', 2: 'MASTER'}[value]
            elif key.startswith("MhaKneeParent") and isinstance(value, int):
                return {0: 'FOOT', 1: 'HIP', 2: 'MASTER'}[value]
            elif isinstance(value, bool):
                return bool(value)
            else:
                return value

        def updateCollections(rig):
            if "Layer 1" not in rig.data.collections.keys():
                for cname in MhxLayers.values():
                    if cname not in rig.data.collections.keys():
                        rig.data.collections.new(cname)
                return
            for coll in list(rig.data.collections):
                if not coll.name.startswith("Layer "):
                    rig.data.collections.remove(coll)
            for idx,cname in MhxLayers.items():
                coll = rig.data.collections.get("Layer %d" % (idx+1))
                if coll:
                    coll.name = cname
                else:
                    rig.data.collections.new(cname)

        rig = context.object
        for key in list(rig.data.keys()):
            if key[0:3] == "Mha":
                value = getValue(key, rig.data[key])
                if hasattr(rig, key):
                    setattr(rig, key, value)
                else:
                    rig[key] = value
        if rig.animation_data:
            for fcu in rig.animation_data.drivers:
                fixFcurve(fcu, rig)
        if rig.data.animation_data:
            for fcu in rig.data.animation_data.drivers:
                fixFcurve(fcu, rig)
        for key in list(rig.data.keys()):
            if key[0:3] == "Mha" and hasattr(rig, key):
                del rig.data[key]

        def addStretchDrivers():
            for suffix in ["L", "R"]:
                useStretch = False
                for bname,prop in [
                    ("shin", "MhaLegStretch"),
                    ("shin.bend", "MhaLegStretch"),
                    ("shin.twist", "MhaLegStretch"),
                    ("forearm.bend", "MhaArmStretch"),
                    ("forearm.twist", "MhaArmStretch"),
                ]:
                    pb = rig.pose.bones.get("%s.%s" % (bname, suffix))
                    prop2 = "%s_%s" % (prop, suffix)
                    if pb:
                        cns = getConstraint(pb, 'STRETCH_TO')
                        if cns:
                            cns.driver_remove("influence")
                            addDriver(cns, "influence", rig, propRef(prop2), "x")
                for bname,prop in [
                    ("foot.fk", "MhaLegStretch"),
                    ("hand.fk", "MhaArmStretch"),
                ]:
                    pb = rig.pose.bones["%s.%s" % (bname, suffix)]
                    prop2 = "%s_%s" % (prop, suffix)
                    cns = getConstraint(pb, 'COPY_LOCATION')
                    if cns:
                        cns.driver_remove("influence")
                        addDriver(cns, "influence", rig, propRef(prop2), "1-x")
                    else:
                        cns = copyLocation(pb, pb.parent, rig, prop2, "1-x")
                        cns.head_tail = 1.0

        addStretchDrivers()
        setMode('EDIT')
        for suffix in ["L", "R"]:
            for bname,conn in [
                ("hand", False),
                ("hand.fk", False),
                ("foot", False),
                ("foot.fk", False),
                ("toe", True),
                ("toe.fk", True),
            ]:
                eb = rig.data.edit_bones.get("%s.%s" % (bname, suffix))
                if eb:
                    eb.use_connect = conn

        setMode('POSE')
        if bpy.app.version >= (4,0,0):
            updateCollections(rig)
        rig.data.MhaFeatures |= F_IDPROPS


def getConstraint(pb, ctype):
    for cns in pb.constraints:
        if cns.type == ctype:
            return cns
    return None

#-------------------------------------------------------------
#   Utilities from import_daz, to avoid addon interdependence
#-------------------------------------------------------------

def addDriver(rna, channel, rig, prop, expr, index=-1):
    fcu = rna.driver_add(channel, index)
    fcu.driver.type = 'SCRIPTED'
    if isinstance(prop, str):
        fcu.driver.expression = expr
        addDriverVar(fcu, "x", prop, rig)
    else:
        prop1,prop2 = prop
        fcu.driver.expression = expr
        addDriverVar(fcu, "x1", prop1, rig)
        addDriverVar(fcu, "x2", prop2, rig)


def addDriverVar(fcu, vname, path, rna, vartype='SINGLE_PROP'):
    var = fcu.driver.variables.get(vname)
    if var is None:
        var = fcu.driver.variables.new()
    var.name = vname
    var.type = vartype
    trg = var.targets[0]
    trg.id_type = getIdType(rna)
    trg.id = rna
    trg.data_path = path
    return trg


def getIdType(rna):
    if isinstance(rna, bpy.types.Armature):
        return 'ARMATURE'
    elif isinstance(rna, bpy.types.Object):
        return 'OBJECT'
    elif isinstance(rna, bpy.types.Mesh):
        return 'MESH'
    elif isinstance(rna, bpy.types.Key):
        return 'KEY'
    else:
        raise RuntimeError("BUG addDriverVar", rna)


def copyLocation(bone, target, rig, prop=None, expr="x", space='WORLD'):
    cns = bone.constraints.new('COPY_LOCATION')
    cns.name = "Copy Location %s" % target.name
    cns.target = rig
    cns.subtarget = target.name
    if prop is not None:
        addDriver(cns, "influence", rig, propRef(prop), expr)
    cns.owner_space = space
    cns.target_space = space
    return cns

#-------------------------------------------------------------
#   Bake MHX
#-------------------------------------------------------------

def getProp(string):
    if string[0:2] == '["' and string[-2:] == '"]':
        return string[2:-2]
    return None

class MhxBaker:
    def run(self, context):
        rig = context.object
        props = []
        for prop in dir(rig):
            if prop.startswith(("Mha", "Mhx")):
                props.append(prop)
        self.setProps(rig, props)
        if rig.animation_data:
            self.changeDrivers(rig, props)
        if rig.data.animation_data:
            self.changeDrivers(rig.data, props)
        rig.DazRig = self.rigtype


class MHX_OT_BakeMhx(MhxBaker, MhxOperator):
    bl_idname = "mhx.bake_mhx"
    bl_label = "Bake MHX"
    bl_description = "Bake MHX properties to make MHX animations work\nalso if the MHX RTS add-on is disabled"
    bl_options = {'UNDO'}

    rigtype = "baked-mhx"

    def setProps(self, rig, props):
        for prop in props:
            x = getattr(rig, prop)
            rig[prop] = x

    def changeDrivers(self, rna, props):
        for fcu in list(rna.animation_data.drivers):
            for var in fcu.driver.variables:
                for trg in var.targets:
                    prop = trg.data_path
                    if prop in props:
                        trg.data_path = '["%s"]' % prop


class MHX_OT_UnbakeMhx(MhxBaker, MhxOperator):
    bl_idname = "mhx.unbake_mhx"
    bl_label = "Unbake MHX"
    bl_description = "Remove baked MHX properties to use the MHX RTS add-on"
    bl_options = {'UNDO'}

    rigtype = "mhx"

    def setProps(self, rig, props):
        return

    def changeDrivers(self, rna, props):
        for fcu in list(rna.animation_data.drivers):
            for var in fcu.driver.variables:
                for trg in var.targets:
                    prop = getProp(trg.data_path)
                    if prop and prop in props:
                        trg.data_path = prop

#----------------------------------------------------------
#
#----------------------------------------------------------

classes = [
    MHX_OT_EnableAllLayers,
    MHX_OT_DisableAllLayers,
    MHX_OT_ConvertMhxActions,
    MHX_OT_UpdateMhxBlender4,
    MHX_OT_UpdateMhx,
    MHX_OT_BakeMhx,
    MHX_OT_UnbakeMhx,
]

def register():
    bpy.types.Object.MhxLegacy = bpy.props.BoolProperty(default = True)
    bpy.types.Object.MhxRig = bpy.props.BoolProperty(default = False)
    bpy.types.Object.DazRig = bpy.props.StringProperty(
        name = "Rig Type",
        default = "")
    initMhxProps()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
