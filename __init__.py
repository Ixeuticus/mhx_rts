# Copyright (c) 2016-2021, Thomas Larsson
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer
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


bl_info = {
    "name": "MHX Runtime System",
    "author": "Thomas Larsson",
    "version": (0,1,0),
    "blender": (2,91,0),
    "location": "UI > MHX RTS",
    "description": "MHX runtime system",
    "warning": "",
    "wiki_url": "http://diffeomorphic.blogspot.se/p/daz-importer-version-15.html",
    "tracker_url": "https://bitbucket.org/Diffeomorphic/import_daz/issues?status=new&status=open",
    "category": "Runtime"}

# To support reload properly, try to access a package var, if it's there, reload everything
if "bpy" in locals():
    print("Reloading MHX RTS")
    import imp
    imp.reload(utils)
    imp.reload(layers)
    imp.reload(fkik)
    imp.reload(mhx)
    imp.reload(animation)
    imp.reload(panel)

else:
    print("Loading MHX RTS")
    import bpy
    from . import utils
    from . import layers
    from . import fkik
    from . import mhx
    from . import animation
    from . import panel

import bpy

#----------------------------------------------------------
#   Register
#----------------------------------------------------------

def register():
    fkik.register()
    mhx.register()
    animation.register()
    panel.register()

def unregister():
    panel.unregister()
    animation.unregister()
    mhx.unregister()
    fkik.unregister()

if __name__ == "__main__":
    register()

print("MHX RTS loaded")
