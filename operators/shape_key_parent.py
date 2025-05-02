import bpy

from .. import core
from .. import memory
from ..memory import *

class OBJECT_OT_skp_shape_key_parent(bpy.types.Operator):
    bl_idname = 'object.skp_shape_key_parent'
    bl_label = core.strings['operators.ShapeKeyParent.bl_label']
    bl_description = core.strings['operators.ShapeKeyParent.bl_description']
    bl_options = {'REGISTER', 'UNDO'}
    
    type: bpy.props.EnumProperty(
        items=(
            ('PARENT', "", core.strings['operators.ShapeKeyParent.type.items[PARENT].description']),
            ('UNPARENT', "", core.strings['operators.ShapeKeyParent.type.items[UNPARENT].description']),
            ('CLEAR', "", core.strings['operators.ShapeKeyParent.type.items[CLEAR].description']),
            ('NEW', "", core.strings['operators.ShapeKeyParent.type.items[NEW].description']),
            ('PARENT_SELECTED', "", core.strings['operators.ShapeKeyParent.type.items[PARENT_SELECTED].description']),
            ('UNPARENT_SELECTED', "", core.strings['operators.ShapeKeyParent.type.items[UNPARENT_SELECTED].description']),
            ('CLEAR_SELECTED', "", core.strings['operators.ShapeKeyParent.type.items[CLEAR_SELECTED].description']),
            ('NEW_SELECTED', "", core.strings['operators.ShapeKeyParent.type.items[NEW_SELECTED].description'])
        ),
        default='PARENT',
        options={'HIDDEN'})
    
    child: bpy.props.StringProperty(options={'HIDDEN'})
    parent: bpy.props.StringProperty(options={'HIDDEN'})
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.active_shape_key and obj.active_shape_key_index >= 0 and obj.mode != 'EDIT'
    
    def execute(self, context):
        obj = context.object
        shape_keys = obj.data.shape_keys
        key_blocks = shape_keys.key_blocks
        active_key_name = obj.active_shape_key.name
        hidden = core.utils.hide(obj)
        selectedKeyNames = core.key.deselect()

        tree = memory.tree

        parentNode=tree.getNodeByName(self.parent) if self.parent else None
        childNode=tree.getNodeByName(self.child) if self.child else None
        
        if self.type == 'PARENT':
            placement = core.settings.shape_key_parent_placement
            
            parentNode.addChild(childNode)
            tree.update()
            
            # Highlight Original Key
            obj.active_shape_key_index = key_blocks.find(active_key_name)
            
            core.key.reselect(selectedKeyNames)
        elif self.type == 'UNPARENT':
            # Move to the root of the tree
            placement = core.settings.shape_key_unparent_placement
            
            if parentNode.hasParents():
                tree.rootNode.addChild(childNode)
                tree.update()
                
                # TODO: placement
                # if placement in ('TOP', 'BOTTOM'):
                #     tree.move(self.child, placement)
                # elif placement == 'BELOW':
                #     tree.move(self.child, 'DOWN')
            
            
            # Highlight Original Key
            obj.active_shape_key_index = key_blocks.find(active_key_name)
            core.key.reselect(selectedKeyNames)

        elif self.type == 'CLEAR':
            # Omitted now, see if statement above
            # This seems to do the same as UNPARENT
            placement = core.settings.shape_key_unparent_placement

            if parentNode.hasParents():
                parentNode.parent.addChild(childNode)
                tree.update()
            
            
            # if len(ancestry) > 1:
            #     tree.reinsert(self.child, ancestry[1][0])
                
            #     if placement in ('TOP', 'BOTTOM'):
            #         tree.move(self.child, placement)
            #     elif placement == 'BELOW':
            #         tree.move(self.child, 'DOWN')
                

            
            # Highlight Original Key
            obj.active_shape_key_index = key_blocks.find(active_key_name)
            
            core.key.reselect(selectedKeyNames)
        elif self.type == 'NEW':
            # Here, the new key is being added as the parent to the active key.
            # The new key's own parenting works even when Auto Parent is turned off.
            active_key_name = obj.active_shape_key.name
            
            # Create new folder
            parentShapeKey = core.key.add(type='FOLDER')

            # Addn ew folder to parent, add selected node as child
            newNode=parentNode.addShapeKeyAsChild(parentShapeKey)
            newNode.addChild(childNode)

            tree.update()
            
            # Highlight Original Key
            obj.active_shape_key_index = key_blocks.find(active_key_name)
            
            core.key.reselect(selectedKeyNames)
            
        elif self.type == 'PARENT_SELECTED':
            placement = core.settings.shape_key_parent_placement
   
            # List of children to move
            for name in selectedKeyNames[::{'TOP': -1, 'BOTTOM': 1}[placement]]:
                nodeToMove=tree.getNodeByName(name)
                parentNode.addChild(nodeToMove)
            
            tree.update()
            
            # Highlight Original Key
            obj.active_shape_key_index = key_blocks.find(active_key_name)
            
            core.key.reselect(selectedKeyNames)
        elif self.type == 'UNPARENT_SELECTED':
            placement = core.settings.shape_key_unparent_placement
            
            outward = sorted(core.utils.flatten(selectedKeyNames), key=lambda name: -len(tree.ancestry(name)))
            
            for name in outward[::{'TOP': -1, 'BELOW': -1, 'BOTTOM': 1, 'ABOVE': 1}[placement]]:
                selectedNode=tree.getNodeByName(name)
                tree.rootNode.addChild(selectedNode)
                
                # if len(ancestry) > 1:
                #     tree.reinsert(name, ancestry[-1][0])
                    
                #     if placement in ('TOP', 'BOTTOM'):
                #         tree.move(name, placement)
                #     elif placement == 'BELOW' and len(ancestry) > 1:
                #         tree.move(name, 'DOWN')
            
            tree.update()
            
            # Highlight Original Key
            obj.active_shape_key_index = key_blocks.find(active_key_name)
            
            core.key.reselect(selectedKeyNames)
        elif self.type == 'CLEAR_SELECTED':
            placement = core.settings.shape_key_unparent_placement
            
            if parentNode.hasParents():
                parentParentNode:TreeNode=parentNode.parent
            
                for name in selectedKeyNames[::{'TOP': -1, 'BELOW': -1, 'BOTTOM': 1, 'ABOVE': 1}[placement]]:
                    selectedNode=tree.getNodeByName(name)
                    parentParentNode.addChild(selectedNode)
                
                # if len(ancestry) > 1:
                #     tree.reinsert(name, ancestry[1][0])
                
                # if placement in ('TOP', 'BOTTOM'):
                #     tree.move(name, placement)
                # elif placement == 'BELOW' and len(ancestry) > 1:
                #     tree.move(name, 'DOWN')
            
            tree.update()
            
            # Highlight Original Key
            obj.active_shape_key_index = key_blocks.find(active_key_name)
            
            core.key.reselect(selectedKeyNames)
        elif self.type == 'NEW_SELECTED':
            tree = memory.tree()
            
            # Here, the new key is being added as the parent to the selected key(s).
            # The new key's own parenting works even when Auto Parent is turned off.
            active_key_name = obj.active_shape_key.name
            
            parentShapeKey = core.key.add(type='FOLDER')
            
            # Create new folder and add to parent
            newFolder=parentNode.addShapeKeyAsChild(parentShapeKey)
            parentNode.addChild(newFolder)
 
            # Add selected to new folder
            for name in selectedKeyNames:
                selectedNode=tree.getNodeByName(name)
                newFolder.addChild(selectedNode)
            
            tree.apply()
            
            # Highlight Parent Folder
            obj.active_shape_key_index = key_blocks.find(parentShapeKey.name)
            
            # Select (Only) Parent Folder
            core.key.select(parentShapeKey, True)
        
        core.utils.show(hidden)
        
        return {'FINISHED'}
