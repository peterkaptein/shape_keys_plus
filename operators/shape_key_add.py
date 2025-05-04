import bpy

from .. import core
from .. import memory
from ..memory import *


class OBJECT_OT_skp_shape_key_add(bpy.types.Operator):
    bl_idname = 'object.skp_shape_key_add'
    bl_label = core.strings['operators.ShapeKeyAdd.bl_label']
    bl_description = core.strings['operators.ShapeKeyAdd.bl_description']
    bl_options = {'REGISTER', 'UNDO'}
    
    type: bpy.props.EnumProperty(
        items=(
            ('DEFAULT', "", ""),
            ('FROM_MIX', "", ""),
            ('FROM_MIX_SELECTED', "", ""),
            ('FOLDER', "", "")
        ),
        default='DEFAULT',
        options={'HIDDEN'})
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        valid_types = {'MESH', 'LATTICE', 'CURVE', 'SURFACE'}
        
        return obj and obj.mode != 'EDIT' and obj.type in valid_types
    
    def execute(self, context):
        obj = context.object
        activeShapeKeyName = getattr(obj.active_shape_key, 'name', None)
        hidden = core.utils.hide(obj)
        newShapeKey = core.key.add(self.type)
        key_blocks = obj.data.shape_keys.key_blocks
        
        if activeShapeKeyName:
            tree:PkTree = memory.tree
            activeNode:TreeNode=tree.getNodeByName(activeShapeKeyName)

            
            
            if core.settings.shape_key_auto_parent:
                if activeNode.isFolder:
                    activeNode.addShapeKeyAsChild(newShapeKey)
                    # tree.move(newShapeKey.name, core.settings.shape_key_parent_placement)
                else:
                    placement = core.settings.shape_key_add_placement
                    activeNode.addShapeKeyAsSibling(newShapeKey)
            
                    #tree.reinsert(newShapeKey.name, activeShapeKeyName)
                    
                    # if placement == 'BOTTOM' or (placement == 'TOP' and (len(ancestry) > 1 or tree.locate(newShapeKey.name)[1] > 1)):
                    #     tree.move(newShapeKey.name, placement)
                    # elif placement == 'BELOW':
                    #     tree.move(newShapeKey.name, 'DOWN')
            else:
                placement = core.settings.shape_key_add_placement
                activeNode.addShapeKeyAsSibling(newShapeKey)
                # tree.reinsert(newShapeKey.name, ancestry[1][0] if len(ancestry) > 1 else activeShapeKeyName)
                
                # if placement == 'BOTTOM' or (placement == 'TOP' and tree.locate(newShapeKey.name)[1] > 1):
                #     tree.move(newShapeKey.name, placement)
                # elif placement == 'BELOW':
                #     tree.move(newShapeKey.name, 'DOWN')
            
            tree.update()
        
        obj.active_shape_key_index = key_blocks.find(newShapeKey.name)
        core.utils.show(hidden)
        
        return {'FINISHED'}
