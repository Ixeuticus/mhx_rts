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

#-------------------------------------------------------------
#   Utility functions
#-------------------------------------------------------------

def propRef(prop):
    return '["%s"]' % prop


def isKeyed(rig, pb, path):
    if rig.animation_data:
        act = rig.animation_data.action
        if act:
            if pb:
                path = ('pose.bones["%s"].%s' % (pb.name, path))
            for fcu in act.fcurves:
                if fcu.data_path == path:
                    return True
    return False

#-------------------------------------------------------------
#   Overridable properties
#-------------------------------------------------------------

if bpy.app.version < (2,90,0):
    def BoolPropOVR(default, description=""):
        return bpy.props.BoolProperty(default=default, description=description)

    def FloatPropOVR(default, description="", precision=2, min=0, max=1):
        return bpy.props.FloatProperty(default=default, description=description, precision=precision, min=min, max=max)

    def setOverridable(rna, attr):
        pass
else:
    def BoolPropOVR(default, description=""):
        return bpy.props.BoolProperty(default=default, description=description, override={'LIBRARY_OVERRIDABLE'})

    def FloatPropOVR(default, description="", precision=2, min=0, max=1):
        return bpy.props.FloatProperty(default=default, description=description, precision=precision, min=min, max=max, override={'LIBRARY_OVERRIDABLE'})

    def setOverridable(rna, attr):
        rna.property_overridable_library_set(propRef(attr), True)


def setattrOVR(rna, attr, value):
    setattr(rna, attr, value)
    rna[attr] = value
    setOverridable(rna, attr)

#-------------------------------------------------------------
#   Progress
#-------------------------------------------------------------

def startProgress(string):
    print(string + " (0%)")
    wm = bpy.context.window_manager
    wm.progress_begin(0, 100)

def endProgress(string):
    print(string + " (100%)")
    wm = bpy.context.window_manager
    wm.progress_end()

def showProgress(n, frame, nFrames, step=20):
    pct = (100.0*n)/nFrames
    if n % step == 0:
        print("%d (%.1f " % (int(frame), pct) + "%)")
    wm = bpy.context.window_manager
    wm.progress_update(int(pct))

#-------------------------------------------------------------
#   Error handling
#-------------------------------------------------------------

def clearErrorMessage():
    global theMessage, theErrorLines
    theMessage = ""
    theErrorLines = []

clearErrorMessage()

def getErrorMessage():
    """getErrorMessage()

    Returns:
    The error message from previous operator invokation if it raised
    an error, or the empty string if the operator exited without errors.
    """
    global theMessage
    return theMessage


def getSilentMode():
    global theSilentMode
    return theSilentMode

def setSilentMode(value):
    """setSilentMode(value)

    In silent mode, operators fail silently if they encounters an error.
    This is useful for scripting.

    value: True turns silent mode on, False turns it off.
    """
    global theSilentMode
    theSilentMode = value

setSilentMode(False)


class MhxError(Exception):
    def __init__(self, value):
        global theErrorLines, theMessage
        theMessage = value
        theErrorLines = (
            theMessage.split("\n")
            )
        print("*** MHX Error ***")
        for line in theErrorLines:
            print(line)

    def __str__(self):
        return repr(theMessage)


class MhxMessage(Exception):
    def __init__(self, value):
        global theErrorLines, theMessage
        theMessage = value
        theErrorLines = theMessage.split("\n")
        print(theMessage)


class MhxPopup(bpy.types.Operator):
    def execute(self, context):
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.progress_end()
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        global theErrorLines
        for line in theErrorLines:
            self.layout.label(text=line)


class ErrorOperator(MhxPopup):
    bl_idname = "mhx.error"
    bl_label = "MHX Error"


class MessageOperator(MhxPopup):
    bl_idname = "mhx.message"
    bl_label = "MHX"

#-------------------------------------------------------------
#   Execute
#-------------------------------------------------------------

class MhxOperator(bpy.types.Operator):
    def execute(self, context):
        clearErrorMessage()
        self.prequel(context)
        try:
            self.run(context)
        except MhxError:
            if getSilentMode():
                print(theMessage)
            else:
                bpy.ops.mhx.error('INVOKE_DEFAULT')
        except MhxMessage:
            if getSilentMode():
                print(theMessage)
            else:
                bpy.ops.mhx.message('INVOKE_DEFAULT')
        except KeyboardInterrupt:
            global theErrorLines
            theErrorLines = ["Keyboard interrupt"]
            bpy.ops.mhx.error('INVOKE_DEFAULT')
        finally:
            self.sequel(context)
        return{'FINISHED'}

    def prequel(self, context):
        return None

    def sequel(self, context):
        pass

    def run(self, context):
        pass



class MhxPropsOperator(MhxOperator):
    def invoke(self, context, event):
        clearErrorMessage()
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

#-------------------------------------------------------------
#   HideOperator class
#-------------------------------------------------------------

class HideOperator(MhxOperator):

    def prequel(self, context):
        self.rig = context.object
        self.amt = self.rig.data
        scn = context.scene
        self.frame = scn.frame_current
        self.state = list(self.rig.data.layers)
        self.rig.data.layers = 32*[True]
        self.hideStatus = [(ob, ob.hide_get(), ob.hide_viewport, ob.hide_render) for ob in bpy.data.objects]
        self.layerColls = []
        self.hideLayerColls(context.view_layer.layer_collection)


    def sequel(self, context):
        self.rig.data.layers = self.state
        for layer in self.layerColls:
            layer.exclude = False
        for ob,hide,viewport,render in self.hideStatus:
            ob.hide_set(hide)
            ob.hide_viewport = viewport
            ob.hide_render = render


    def hideLayerColls(self, layer):
        if layer.exclude:
            return True
        ok = True
        for ob in layer.collection.objects:
            if ob == self.rig:
                ok = False
        for child in layer.children:
            ok = (self.hideLayerColls(child) and ok)
        if ok:
            self.layerColls.append(layer)
            layer.exclude = True
        return ok


class HidePropsOperator(HideOperator):
    def invoke(self, context, event):
        clearErrorMessage()
        wm = context.window_manager
        return wm.invoke_props_dialog(self)