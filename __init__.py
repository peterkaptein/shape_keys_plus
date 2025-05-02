import bpy
import bl_ui

from . import core

from . import operators
from . import menus
from . import panels
from . import properties
from .memory import *
from .views.shape_keys_ui_list import PK_MESH_UL_shape_keys_plus

bl_info = {
    "name": "Shape Keys++",
    "author": "Michael Glen Montague, Peter Kaptein",
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



classes = (    
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
    
    # views
    AddonPreferences,
    PK_MESH_UL_shape_keys_plus,
)


def register():
    
    for cls in classes:
        bpy.utils.register_class(cls)


    from bpy.props import (
                       PointerProperty,
                       )
    
    core.preferences = bpy.context.preferences.addons[__name__].preferences
    bpy.types.Scene.shape_keys_plus = PointerProperty(
        type=properties.SceneProperties, name=core.strings['Shape Keys+'])
    bpy.types.Key.shape_keys_plus = PointerProperty(
        type=properties.KeyProperties, name=core.strings['Shape Keys+'])
    
    default_panel_exists = hasattr(bpy.types, 'DATA_PT_shape_keys')
    
    if core.preferences.hide_default and default_panel_exists:
        try:
            bpy.utils.unregister_class(bl_ui.properties_data_mesh.DATA_PT_shape_keys)
        except RuntimeError:
            pass
    
    # Blender 2.79b, SKP v1.0.x
    if hasattr(bpy.types, 'OBJECT_PT_skp_shape_keys_plus'):
        bpy.utils.unregister_class(bpy.types.OBJECT_PT_skp_shape_keys_plus)
    
    # Blender 2.79b, SKP v1.1.x
    if hasattr(bpy.types, 'OBJECT_PT_shape_keys_plus'):
        bpy.utils.unregister_class(bpy.types.OBJECT_PT_shape_keys_plus)

def unregister():
    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)
    
    default_panel_exists = hasattr(bpy.types, 'DATA_PT_shape_keys')
    
    if not default_panel_exists:
        bpy.utils.register_class(bl_ui.properties_data_mesh.DATA_PT_shape_keys)
