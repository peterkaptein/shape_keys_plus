import bpy
import bl_ui


from .. import memory,core
from ..memory import  PkTree, TreeNode

def update(self, context):
    memory.tree.update()

class PK_MESH_UL_shape_keys_plus(bpy.types.UIList):

    # New approach:
    # 1: Tree is leading and rendered
    # 2: Shape keys are part of tree-data, or queried via tree / Blender object model
    # 3: We render the shape keys, but use the tree from memory as data for the rendered tree
    # 4: No sorting and so on takes place for the shape keys. Why would you?


    def draw_item(self, context, layout, data, shapeKey, icon, sourceObject, active_propname, index=0, flt_flag=0):
        obj = sourceObject # The object with the parameter that the list is based on

        tree = memory.tree
        
        if not tree:
            # The active tree hasn't been created yet, for some reason.
            # Hopefully it will exist on the next call.
            return
        
        # Has it parents?
 
        # selected keys is updated by filter-function
        multipleKeysSelected=tree.getShapekeysAreSelected()
        # Is it selectend?
        # selections = [key.name for key in core.key.get_selected()]
        thisItemIsSelected = tree.keyIsSelected(shapeKey.name)
        # Show [o] as selector if parents are selected / in a selected folder
        parentIsSelected = tree.getAncesterIsSelected(shapeKey.name) # bool([p for p in parentNames if p in selections])
        
        treeNode:TreeNode=tree.getNodeByName(shapeKey.name)

        use_edit_mode = obj.use_shape_key_edit_mode and obj.type == 'MESH'
        
        frame = layout.row(align=True)

        # Disable if others are selected
        frame.active = thisItemIsSelected or not multipleKeysSelected
        
        # Indentation for folders
        # Check if this shape key belongs to a folder.
        if treeNode.hasParents():
            spacing = treeNode.indent * core.settings.shape_key_indent_scale

            # if not treeNode.isFolder:
            #     spacing+=4

            # Get the number of folders this shape key is stacked in.
            for _ in range(spacing - 1):
                # Use the customizable folder indentation.
                frame.separator(factor=1)
        
        if treeNode.isFolder:
            op = frame.operator(
                operator='object.skp_folder_toggle',
                text="",
                icon=core.folder.get_active_icon(shapeKey),
                emboss=False)

            op.index = index
            
            frame.prop(
                data=shapeKey,
                property='name',
                text="",
                emboss=False)
        else:
            frame.label(
                text="",
                icon="DOT")
            
            frame.prop(
                data=shapeKey,
                property='name',
                text="",
                emboss=False,
                icon=core.preferences.shape_key_icon)
        
        buttons = layout.row(align=True)
        buttons.alignment = 'RIGHT'
        
        if (shapeKey.mute and not thisItemIsSelected) or (obj.mode == 'EDIT' and not use_edit_mode):
            buttons.active = False
        
        if multipleKeysSelected and not thisItemIsSelected:
            buttons.active = False
        
        if treeNode.isFolder:
            op = buttons.operator(
                operator='object.skp_folder_ungroup',
                text="",
                icon='X',
                emboss=False)

            op.index = index
        else:
            if not shapeKey.id_data.use_relative:
                buttons.prop(
                    data=shapeKey,
                    property='frame',
                    text="",
                    emboss=False)
            elif index > 0:
                vrow = buttons.row()
                vrow.active = not multipleKeysSelected or multipleKeysSelected and thisItemIsSelected
                vrow.scale_x = 0.66
                
                if bpy.app.version < (2, 92):
                    vrow.prop(data=shapeKey, property='value', text="", emboss=False)
                else:
                    if bpy.app.version >= (3, 0):
                        vrow.emboss = 'NONE_OR_STATUS'
                    elif bpy.app.version >= (2, 92):
                        vrow.emboss = 'UI_EMBOSS_NONE_OR_STATUS'
                    
                    vrow.prop(data=shapeKey, property='value', text="")
            
            buttons.prop(
                data=shapeKey,
                property='mute',
                text="",
                icon='HIDE_OFF',
                emboss=False)
        
        if index > 0:
            if thisItemIsSelected:
                icon = 'CHECKBOX_HLT'
            elif parentIsSelected:
                icon = 'SNAP_FACE_CENTER'
            else:
                icon = 'CHECKBOX_DEHLT'
            
            op = buttons.operator(
                operator='object.skp_shape_key_select',
                text="",
                icon=icon,
                emboss=False)
            
            op.index = index
            op.mode = 'TOGGLE'
    
    def draw_filter(self, context, layout):
        row = layout.row()
        
        subrow = row.row(align=True)
        
        subrow.label(text="Find:")
        subrow.prop(
            data=self,
            property='filter_name',
            text="")
        
        icon = 'ZOOM_OUT' if self.use_filter_invert else 'ZOOM_IN'
        
        subrow.prop(
            data=self,
            property='use_filter_invert',
            text="",
            icon=icon)
        
        icon = 'FILE_FOLDER'
        
        subrow.prop(
            data=core.settings,
            property='show_filtered_folder_contents',
            text="",
            icon=icon)
        
        subrow = row.row(align=True)
        
        icon = 'HIDE_OFF'
        
        subrow.prop(
            data=core.settings,
            property='shape_key_limit_to_active',
            text="",
            icon=icon)
        
        if core.settings.shape_key_limit_to_active:
            subrow.prop(
                data=core.settings,
                property='filter_active_threshold',
                text="")
            
            icon = 'TRIA_LEFT' if core.settings.filter_active_below else 'TRIA_RIGHT'
            
            subrow.prop(
                data=core.settings,
                property='filter_active_below',
                text="",
                icon=icon)
    
    def filter_items(self, context, obj, propname):
        
        # Assure we are up to date
        tree:PkTree = memory.tree.checkStatus()
    
        # The list is based on data[propertyname]
        # The filter then builds an indexed list per item to state "show"/"hide"

        flt_flags = []
        flt_name_flags = []
        flt_neworder=[]


        key_blocks = obj.key_blocks
        helper_funcs = bpy.types.UI_UL_list
        filtering_by_name = False
        
        

        # Only if we have the same amount
        if len(key_blocks)==len(tree.shapeKeyTreeOrder):
            flt_neworder = tree.shapeKeyTreeOrder # This can be used to present the keys
        else:
            print("Items are missing in tree. Shape key tree and shape key list are not the same length")

        def filter_set(i, f):
            # self.bitflag_filter_item allows a shape key to be shown.
            # 0 will prevent a shape key from being shown.
            flt_flags[i] = self.bitflag_filter_item if f else 0
        
        def filter_get(i):
            return flt_flags[i] != 0
        

        renewSearch=False
        name_filters = [False] * len(key_blocks)

        if self.filter_name:
            filtering_by_name = True

            

            if tree.previousSearch!=self.filter_name or tree.previousItenCount!=len(key_blocks):
                tree.buffered_flt_flags=[]
                tree.previousSearch=self.filter_name
                tree.previousItenCount=len(key_blocks)
                renewSearch=True

                print("Renew search")
            
            if renewSearch:
                # This is expensive each draw cycle, so we use buffer
                flt_flags = helper_funcs.filter_items_by_name(
                    self.filter_name,
                    self.bitflag_filter_item, key_blocks, 'name')
                
            else:
                flt_flags=tree.buffered_flt_flags
                name_filters=tree.buffered_name_filters

            for i in range(len(flt_flags)):
                if flt_flags[i] == self.bitflag_filter_item:
                    name_filters[i] = True
        else:
            # Initialize every shape key as visible.
            flt_flags = [self.bitflag_filter_item] * len(key_blocks)
        
        for idx, shapeKey in enumerate(key_blocks):     
            
            hidden = False
            node=tree.getNodeByName(shapeKey.name)
            nodeHasParents=node.hasParents()
            
            if nodeHasParents:
                if node.parentIsCollapsed() and not filtering_by_name:
                    hidden = True
            
            if hidden:
                filter_set(idx, False) # Hide item
            
            if filtering_by_name and nodeHasParents and renewSearch:
                # This is expensive each draw cycle, so we skip and rely on buffer
                parents=node.getAncestryNames()
                for p in parents:
                    parent_index = key_blocks.find(p)
                    parent_hidden = not name_filters[parent_index]
                    
                    if name_filters[idx] and parent_hidden:
                        filter_set(parent_index, True) # Show item
            
            if core.settings.show_filtered_folder_contents:

                if node.hasChildren() and filter_get(idx):
                    for i in range(len(node.children)):
                        filter_set(idx + 1 + i, True)
            
            if core.settings.shape_key_limit_to_active:
                if node.hasChildren():
                    filter_set(idx, False)
                else:
                    val = core.settings.filter_active_threshold
                    below = core.settings.filter_active_below
                    
                    in_active_range = \
                        shapeKey.value <= val if \
                        below else \
                        shapeKey.value >= val
                    
                    filter_set(idx, in_active_range)
        
        tree.buffered_flt_flags=flt_flags
        tree.buffered_name_filters=name_filters

        return flt_flags, flt_neworder