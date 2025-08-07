import bpy

from .. import core
from .. import memory
from ..memory import TreeNode, PkTree

class OBJECT_OT_skp_shape_key_remove(bpy.types.Operator):
    bl_idname = 'object.skp_shape_key_remove'
    bl_label = core.strings['operators.ShapeKeyRemove.bl_label']
    bl_description = core.strings['operators.ShapeKeyRemove.bl_description']
    bl_options = {'REGISTER', 'UNDO'}
    
    type: bpy.props.EnumProperty(
        items=(
            ('DEFAULT', "", ""),
            ('CLEAR', "", ""),
            ('DEFAULT_SELECTED', "", "")
        ),
        default='DEFAULT',
        options={'HIDDEN'})
    
    @classmethod
    def poll(cls, context):
        return context.object.mode != 'EDIT' and context.object.data.shape_keys
    
    def execute(self, context):
        obj = bpy.context.active_object
        shape_keys = obj.data.shape_keys
        key_blocks = shape_keys.key_blocks
        anim = shape_keys.animation_data
        
        if self.type == 'CLEAR':
            bpy.ops.object.shape_key_remove(all=True)
        elif self.type == 'DEFAULT':
            tree = memory.tree
            treeNode:TreeNode=tree.getNodeByName(obj.active_shape_key.name)

            allChildrenKeys=treeNode.getChildrenShapeKeys(recursive=True)
            ancestry = tree.getAncestryNames(obj.active_shape_key.name)
            
            #if treeNode.hasParents():
            # Legacy: number of children is mutated, for reconstruction of folder structure.
            #   core.folder.shift_block_value(key_blocks[ancestry[-1][0]], 'children', -1)
            
            active_key = obj.active_shape_key
            
            for key in reversed([active_key] + allChildrenKeys):
                keyIndex=key_blocks.find(key.name)

                if keyIndex==0:
                    # skip this shape key
                    continue

                # Remove the driver first.
                if anim and anim.drivers:
                    for fc in anim.drivers:
                        if fc.data_path == "key_blocks[\"%s\"].value" % key.name:
                            anim.drivers.remove(fc)
                
                # Remove this shape key
                obj.active_shape_key_index = keyIndex
                bpy.ops.object.shape_key_remove()
            
            nextShapeKey = treeNode.remove()

            if nextShapeKey and False:
                obj.active_shape_key_index=shape_keys.index(nextShapeKey)
            
            # Done removing
            # TODO: set higlight to item before or removed one, if not a folder

        elif self.type == 'DEFAULT_SELECTED':
            selections = core.key.deselect()
            
            for name in selections:
                index = key_blocks.find(name)
                
                if index == -1:
                    continue

                obj.active_shape_key_index = key_blocks.find(name) + core.folder.get_capacity(key_blocks[name])
                
                for key in reversed([key_blocks[index]] + core.folder.get_children(key_blocks[index])):
                    # Remove the driver first.
                    if anim and anim.drivers:
                        for fc in anim.drivers:
                            if fc.data_path == "key_blocks[\"%s\"].value" % key.name:
                                anim.drivers.remove(fc)
                    
                    bpy.ops.object.shape_key_remove()
        memory.tree.update(clearSelections=True)
        return {'FINISHED'}
