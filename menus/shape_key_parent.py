import bpy

from .. import core
from .. import memory
from ..memory import PkTree


class OBJECT_MT_skp_shape_key_parent(bpy.types.Menu):
    bl_label = core.strings['menus.ShapeKeyParent.bl_label']
    
    
    def draw(self, context):
        layout = self.layout
        tree=memory.tree
        
        if core.key.get_selected_indices():
            layout.enabled = False
        
        active_key = context.object.active_shape_key
        
        if active_key:

            activeTreeNode=tree.getNodeByName(active_key.name)
            parents = activeTreeNode.getAncestryNames()
            folders=tree.getFlatlist(folderOnly=True)
            forbiddenFolders = [active_key.name]+activeTreeNode.getChildrenNames(folderOnly=True,recursive=True)
            if activeTreeNode.hasParents():
                parentName=activeTreeNode.parent.name
                forbiddenFolders+=[parentName]

                # New folder
                op = layout.operator(
                    operator='object.skp_shape_key_parent',
                    text=core.strings['menus.ShapeKeyParent.draw.operator[New Folder]'],
                    translate=False,
                    icon='NEWFOLDER')
                
                op.type = 'NEW'
                op.child = active_key.name
                op.parent = parentName

    
                # Remove from parent
                layout.separator()
                
                op = layout.operator(
                    operator='object.skp_shape_key_parent',
                    text=core.strings['menus.ShapeKeyParent.draw.operator[Unparent from "%s"]'] % parentName,
                    translate=False,
                    icon='X')
                
                op.type = 'UNPARENT'
                op.child = active_key.name
                op.parent = parentName
            
            if activeTreeNode.hasGrandParents():
                parentName=activeTreeNode.parent.name
                op = layout.operator(
                    operator='object.skp_shape_key_parent',
                    text=core.strings['menus.ShapeKeyParent.draw.operator[Unparent from "%s"]'] % parents[-1],
                    translate=False,
                    icon='CANCEL')
                
                op.type = 'CLEAR'
                op.child = active_key.name
                op.parent = parentName
            
            # Only allow parenting to a folder that this shape key isn't already related to.

            print("FOlders to display",len(folders))
            
            if len(folders)>0:
                layout.separator()
            
            for folder in folders:
                row = layout.row()
                
                if folder.name in forbiddenFolders:
                    row.enabled = False
                
                op = row.operator(
                    operator='object.skp_shape_key_parent',
                    text=("  " * folder.indent) + folder.name,
                    translate=False,
                    icon=core.folder.get_active_icon(folder.shapeKey))
                
                op.type = 'PARENT'
                op.child = active_key.name
                op.parent = folder.name


class OBJECT_MT_skp_shape_key_parent_selected(bpy.types.Menu):
    bl_label = core.strings['menus.ShapeKeyParent.bl_label']

    # This is for multi-selection
    
    def draw(self, context):
        tree:PkTree=memory.tree
        layout = self.layout
        active_key = context.object.active_shape_key
        
        if active_key:

            
            op = layout.operator(
                operator='object.skp_shape_key_parent',
                text=core.strings['menus.ShapeKeyParent.draw.operator[New Folder]'],
                translate=False,
                icon='NEWFOLDER')
            
            op.type = 'NEW_SELECTED'
            
            layout.separator()
            
            op = layout.operator(
                operator='object.skp_shape_key_parent',
                text=core.strings['menus.ShapeKeyParentSelected.draw.operator[Unparent from Parent]'],
                translate=False,
                icon='X')
            
            op.type = 'UNPARENT_SELECTED'
            
            op = layout.operator(
                operator='object.skp_shape_key_parent',
                text=core.strings['menus.ShapeKeyParentSelected.draw.operator[Unparent from Root]'],
                translate=False,
                icon='CANCEL')
            
            op.type = 'CLEAR_SELECTED'
               
            ###################

            folders=tree.getFlatlist(folderOnly=True)
            print("FOlders to display",len(folders))

            if len(folders)>0:
                layout.separator()

            # Selected foldes cannot be nested in children of any selected folder
            forbiddenFolders =[] 
            for folder in folders:
                if tree.keyIsSelected(folder.name):
                    forbiddenFolders+=[folder.name]+folder.getChildrenNames(recursive=True,folderOnly=True) 
            
            # Render list
            for folder in folders:
                row = layout.row()
                
                if folder.name in forbiddenFolders:
                    row.enabled = False
                
                op = row.operator(
                    operator='object.skp_shape_key_parent',
                    text=("  " * folder.indent) + folder.name,
                    translate=False,
                    icon=core.folder.get_active_icon(folder.shapeKey))
                
                op.type = 'PARENT_SELECTED'
                op.parent = folder.name
