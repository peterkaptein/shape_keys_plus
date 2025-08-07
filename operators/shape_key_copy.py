import bpy

from .. import core
from .. import memory
from ..memory import *

class OBJECT_OT_skp_shape_key_copy(bpy.types.Operator):
    bl_idname = 'object.skp_shape_key_copy'
    bl_label = core.strings['operators.ShapeKeyCopy.bl_label']
    bl_description = core.strings['operators.ShapeKeyCopy.bl_description']
    bl_options = {'REGISTER', 'UNDO'}
    
    mirror: bpy.props.IntProperty(options={'HIDDEN'})
    select: bpy.props.BoolProperty(options={'HIDDEN'})
    custom: bpy.props.BoolProperty(options={'HIDDEN'})
    
    @classmethod
    def poll(cls, context):
        return context.object and context.object.data.shape_keys and context.object.mode != 'EDIT'
    
    def execute(self, context):
        obj = context.object
        shape_keys = obj.data.shape_keys
        key_blocks = shape_keys.key_blocks
        hidden = core.utils.hide(obj)
        tree:PkTree = memory.tree

        if self.select:
            # Handle list of selected shape keys, including folders
            selectedIndices = core.key.get_selected_indices()
            skip = []

            if not selectedIndices:
                return {'CANCELLED'}
            
            core.key.deselect()
            
            active_name = obj.active_shape_key.name
            selectedKeys = []
            createdCopiesToSelect = []
            
            for selectedKeyIndex in selectedIndices:
                if selectedKeyIndex in skip:
                    continue
                
                shapeKey=key_blocks[selectedKeyIndex] 
                selectedKeys.append(shapeKey)
                node:TreeNode=tree.getNodeByName(shapeKey.name)

                for shapeKey in node.getAllShapeKeys():
                    index = key_blocks.find(shapeKey.name)

                    # placement = core.settings.shape_key_add_placement
                    # if placement == 'BOTTOM' or (placement == 'TOP' and (len(ancestryNames) > 1 or tree.locate(copyName)[1] > 1)):
                    #     tree.move(copyName, placement)
                    # elif placement == 'BELOW':
                    #     tree.move(copyName, 'DOWN')
                    sourceNode:TreeNode=tree.getNodeByName(shapeKey.name)

                    newShapeKey = core.key.copy(shapeKey, self.mirror, self.custom)  
                    sourceNode.addShapeKeyAsSibling(newShapeKey)
                    
                    if index in selectedIndices:
                        createdCopiesToSelect.append(newShapeKey)
                        # Don't allow children to be copied multiple times.
                        # It may be useful sometimes, but it's not worth the hassle to implement properly.
                        if shapeKey != key_blocks[selectedKeyIndex]:
                            skip.append(index)
            
            tree.update(clearSelections=True)
            
            for newKey in createdCopiesToSelect:
                core.key.select(newKey.name, True)
            
            obj.active_shape_key_index = key_blocks.find(active_name)
        else:
            active_key = obj.active_shape_key
            active_name = active_key.name
            active_copy = None

            shapeKey=active_key
            node:TreeNode=tree.getNodeByName(shapeKey.name)

            for shapeKey in node.getAllShapeKeys():
                sourceNode:TreeNode=tree.getNodeByName(shapeKey.name)
                copy = core.key.copy(shapeKey, self.mirror, self.custom)
               
                if not active_copy:
                    active_copy = copy.name

                sourceNode.addShapeKeyAsSibling(copy)
            
            # Update flatlist, etcetera
            tree.update(clearSelections=True)
            
            obj.active_shape_key_index = key_blocks.find(active_copy)
        
        core.utils.show(hidden)
        
        return {'FINISHED'}
