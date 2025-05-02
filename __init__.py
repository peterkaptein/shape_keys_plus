import bpy
import bl_ui

from . import core
from . import memory
from . import operators
from . import menus
from . import panels
from . import properties
from .memory import *

bl_info = {
    "name": "Shape Keys+",
    "author": "Michael Glen Montague",
    "version": (2, 0, 7),
    "blender": (2, 93, 0),
    "location": "Properties > Object Data > Shape Keys+",
    "description": "Adds a panel with extra options for creating, sorting, viewing, and driving shape keys.",
    "warning": "",
    "doc_url": "https://github.com/MichaelGlenMontague/shape_keys_plus/wiki",
    "tracker_url": "https://github.com/MichaelGlenMontague/shape_keys_plus/issues",
    "category": "Object"
}

# bl_info is parsed before the add-on is loaded, so its translations have to be copied by hand or a script.

bl_info_en_US = {
    "name": "Shape Keys+",
    "author": "Michael Glen Montague",
    "version": (2, 0, 3),
    "blender": (2, 93, 0),
    "location": "Properties > Object Data > Shape Keys+",
    "description": "Adds a panel with extra options for creating, sorting, viewing, and driving shape keys.",
    "warning": "",
    "doc_url": "https://github.com/MichaelGlenMontague/shape_keys_plus/wiki",
    "tracker_url": "https://github.com/MichaelGlenMontague/shape_keys_plus/issues",
    "category": "Object"
}
bl_info_ja_JP = {
    "name": "シェイプキープラス (Shape Keys+)",
    "author": "Michael Glen Montague （マイケルグレンモンタギュー）",
    "version": (2, 0, 3),
    "blender": (2, 93, 0),
    "location": "プロパティ ⇒ オブジェクトデータ ⇒ シェイプキープラス",
    "description": "シェイプキーを作成したり整理したり見せたりドライブしたりのための余分設定を入っているパネルを追加します。",
    "warning": "",
    "doc_url": "https://github.com/MichaelGlenMontague/shape_keys_plus/wiki",
    "tracker_url": "https://github.com/MichaelGlenMontague/shape_keys_plus/issues",
    "category": "Object"
}


class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    def update_hide_default(self, context):
        if self.hide_default:
            bpy.utils.unregister_class(bl_ui.properties_data_mesh.DATA_PT_shape_keys)
        else:
            bpy.utils.register_class(bl_ui.properties_data_mesh.DATA_PT_shape_keys)
    
    def update_shape_key_icon(self, context):
        enum_items = bpy.types.UILayout.bl_rna.functions['prop'].parameters['icon'].enum_items
        self.shape_key_icon_page = enum_items.find(self.shape_key_icon) // 10 + 1
    
    hide_default: bpy.props.BoolProperty(
        name=core.strings['AddonPreferences.hide_default.name'],
        description=core.strings['AddonPreferences.hide_default.description'],
        default=True,
        update=update_hide_default)
    
    default_folder_icon_pair: bpy.props.IntProperty(
        name=core.strings['AddonPreferences.default_folder_icon_pair.name'],
        min=1,
        max=core.folder.icon_pairs[-1][-1],
        default=1)
    
    default_folder_swap_icons: bpy.props.BoolProperty(
        name=core.strings['AddonPreferences.default_folder_swap_icons.name'],
        default=False)
    
    shape_key_icon: bpy.props.EnumProperty(
        items=[
            (ei.identifier, ei.name, ei.description, ei.icon, ei.value) for
            ei in bpy.types.UILayout.bl_rna.functions['prop'].parameters['icon'].enum_items],
        default='NONE',
        update=update_shape_key_icon)
    
    shape_key_icon_page: bpy.props.IntProperty(
        min=1,
        max=len(range(0, len(bpy.types.UILayout.bl_rna.functions['prop'].parameters['icon'].enum_items), 10)),
        default=1)
    
    def draw(self, context):
        layout = self.layout
        icon_pair = core.folder.get_icon_pair(self.default_folder_icon_pair)
        
        row = layout.row()
        row.alignment = 'RIGHT'
        
        row.prop(
            data=self,
            property='hide_default',
            translate=False)
        
        row = layout.row()
        row.alignment = 'RIGHT'
        box = row.box()
        box.alignment = 'LEFT'
        box.label(
            text=core.strings['AddonPreferences.draw.label[Default Folder Icon]'],
            translate=False)
        
        box.menu(
            menu='OBJECT_MT_skp_folder_icon',
            text=icon_pair[2])
        
        box = box.box()
        row = box.row()
        row.alignment = 'CENTER'
        row.label(icon=icon_pair[self.default_folder_swap_icons])
        
        row.prop(
            data=self,
            property='default_folder_swap_icons',
            text="",
            icon='ARROW_LEFTRIGHT')
        
        row.label(icon=icon_pair[not self.default_folder_swap_icons])
        
        row = layout.row()
        row.alignment = 'RIGHT'
        box = row.box()
        box.alignment = 'CENTER'
        row = box.row(align=True)
        
        col = row.column()
        col.alignment = 'LEFT'
        col.label(
            text=core.strings['AddonPreferences.draw.label[Shape Key Icon]'],
            translate=False)
        
        col = row.column()
        col.popover(
            panel='DATA_PT_skp_shape_key_icon',
            text="",
            icon=self.shape_key_icon if self.shape_key_icon != 'NONE' else 'BLANK1')


class PK_MESH_UL_shape_keys_plus(bpy.types.UIList):
    # TODO: Use tree structure as main  to render list, insteas of shape key list
    # How it works now
    # Shape key items are manipulated to conform to the tree structure
    # Per shape key, the tree is queried to get info on placement and visibility
    # Then the ordered shape-key list is rendered based on this

    # SHOW/HIDE:
    # Items are filtered and shown based on that
    # If a folder is closed, sub-items are not shown due to that

    # New approach:
    # 1: Tree is leading and rendered
    # 2: Shape keys are part of tree-data, or queried via tree / Blender object model
    # 3: We render the tree, but use Shape keys as data for the rendered tree
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
        name_filters = [False] * len(key_blocks)
        

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
        
        if self.filter_name:
            filtering_by_name = True
            
            flt_flags = helper_funcs.filter_items_by_name(
                self.filter_name,
                self.bitflag_filter_item, key_blocks, 'name')

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
            
            if filtering_by_name and nodeHasParents:
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
        
        return flt_flags, flt_neworder


classes = (
    AddonPreferences,
    
    operators.DriverUpdate,
    operators.ActiveFolderIcon,
    operators.DefaultFolderIcon,
    operators.FolderMutate,
    operators.FolderToggle,
    operators.FolderUngroup,
    operators.ShapeKeyAdd,
    operators.ShapeKeyCopy,
    operators.ShapeKeyMirror,
    operators.ShapeKeyMove,
    operators.ShapeKeyParent,
    operators.ShapeKeyRemove,
    operators.ShapeKeySelect,
    operators.VariableAdd,
    operators.VariableCopy,
    operators.VariableMove,
    operators.VariableRemove,
    
    menus.ShapeKeyParent,
    menus.ShapeKeyParentSelected,
    menus.FolderIcon,
    menus.FolderIconStandard,
    menus.FolderIconSpecial,
    menus.FolderIconMiscellaneous,
    menus.ShapeKeyAddContextMenu,
    menus.ShapeKeyAddContextMenuSelected,
    menus.ShapeKeyCopyContextMenu,
    menus.ShapeKeyCopyContextMenuSelected,
    menus.ShapeKeyRemoveContextMenu,
    menus.ShapeKeyRemoveContextMenuSelected,
    menus.ShapeKeyOtherContextMenu,
    menus.ShapeKeyOtherContextMenuSelected,
    
    panels.ShapeKeysPlus,
    panels.ShapeKeyDriver,
    panels.ShapeKeyIcon,
    panels.CopyCustomization,
    
    properties.CopyCustomization,
    properties.KeyProperties,
    properties.SceneProperties,
    
    PK_MESH_UL_shape_keys_plus,
)


def register():
    for cls in classes:
        print("register xlass")
        bpy.utils.register_class(cls)


    from bpy.props import (
                       PointerProperty,
                       )

    bpy.types.Scene.shape_keys_plus = PointerProperty(
        type=properties.SceneProperties, name=core.strings['Shape Keys+'])
    bpy.types.Key.shape_keys_plus = PointerProperty(
        type=properties.KeyProperties, name=core.strings['Shape Keys+'])
    
    core.preferences = bpy.context.preferences.addons[__name__].preferences
    print("preferences")
    default_panel_exists = hasattr(bpy.types, 'DATA_PT_shape_keys')
    
    if core.preferences.hide_default and default_panel_exists:
        try:
            bpy.utils.unregister_class(bl_ui.properties_data_mesh.DATA_PT_shape_keys)
        except RuntimeError:
            pass
    
    # Blender 2.79b, SKP v1.0.x
    #if hasattr(bpy.types, 'OBJECT_PT_skp_shape_keys_plus'):
    #bpy.utils.unregister_class(bpy.types.OBJECT_PT_skp_shape_keys_plus)
    
    # Blender 2.79b, SKP v1.1.x
    #if hasattr(bpy.types, 'OBJECT_PT_shape_keys_plus'):
    #bpy.utils.unregister_class(bpy.types.OBJECT_PT_shape_keys_plus)
    print("done registering class")

def unregister():
    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)
    
    default_panel_exists = hasattr(bpy.types, 'DATA_PT_shape_keys')
    
    if not default_panel_exists:
        bpy.utils.register_class(bl_ui.properties_data_mesh.DATA_PT_shape_keys)
