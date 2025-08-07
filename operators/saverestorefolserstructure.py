import bpy

from .. import memory
from ..memory import PkTree

TREE_STORE_NAME_COPY = "pk_shape_keys_tree_copy"
TREE_STORE_NAME = "pk_shape_keys_tree"

def saveShapekeyFolderStructure():
    import bpy

    active = bpy.context.active_object

    active[TREE_STORE_NAME_COPY] = active[TREE_STORE_NAME]
    
def restoreShapekeyFolderStructure():
    import bpy

    active = bpy.context.active_object

    saved=active[TREE_STORE_NAME_COPY]

    if saved:
        active[TREE_STORE_NAME] = active[TREE_STORE_NAME_COPY]
        return

    print("Not restored. No tree saved")

class SaveFolderStrue(bpy.types.Operator):
    bl_idname = "wm.sk_savestru"
    bl_label = "Save folder structure"
    bl_description="Make a backup of the folder structure in case of failure"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        saveShapekeyFolderStructure()
        
        return {'FINISHED'}

class RestoreFolderStrue(bpy.types.Operator):
    bl_idname = "wm.sk_restorestru"
    bl_label = "Restore folder structure"
    bl_description="Restore backup of the folder structure in case of failure"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        restoreShapekeyFolderStructure()

        
        return {'FINISHED'}

class FixFolderStrue(bpy.types.Operator):
    bl_idname = "wm.sk_fixstru"
    bl_label = "Fix folder structure"
    bl_description="Fix the folder structure in case something went wrong"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        tree:PkTree = memory.tree

        tree.updateAndSanitizeFlatTree(fixDirectories=True)
        return {'FINISHED'}
        