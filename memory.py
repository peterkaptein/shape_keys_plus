import bpy

from . import core

import itertools

TREE_STORE_NAME = "pk_shape_keys_tree"

from bpy.props import (StringProperty,
                       PointerProperty,
                       CollectionProperty,
                       BoolProperty
                       )

from bpy.types import (Panel,
                       PropertyGroup,
                       )

class ShapeKeyInterface:
    mute:bool=False
    name:str=""
    slider_max:float=1.0
    slider_min:float=0.0
    value:float=0.0
    vertex_group:str="" # The identifier of the key


# Precompiles does not allow classes to reference themselves as type
# So we spliut the treenode into several classes
class BaseTreeNode:
    indent=0
    isFolder=False
    shapeKey:ShapeKeyInterface=None
    vertex_group:str="" # The identifier of the key
    name:str=""

    children:list=[]
    parent=None

    @property
    def name(self)->str:
        # Always present the correct name
        if self.shapeKey:
            return self.shapeKey.name
        
        # No shapekey, use given name
        return self._name
    
    # To be overridden
    def getAllShapeKeys()->list[ShapeKeyInterface]:
        return []
    def getAsLegacyArray():
        # Returns the node as a tree structure
        # [key, key, [foldername, childNodes,[foldername,chilsnondes]]]
        return []

# Precompiles does not allow classes to reference themselves as type
# So we spliut the treenode into several classes
class TreeNodeWithChildren(BaseTreeNode):    
    children:list[BaseTreeNode]=[]

    # Here we can implemnt all actions involving child nodes

    # Actions
    def addChildren(self, children:list[BaseTreeNode]):
        # Children is a list of nodes
        for child in children:
            self.addChild(child)

    def addChild(self, child:BaseTreeNode):
        """Add child to node, re-parents the child so the structure is correct"""
        # Child is a node
        parent:TreeNodeWithChildren = child.parent
        # Remove child from current position
        if parent and (child in parent.children):
            # Remove child from parent
            parent.children.remove(child)

        # Add to self, and make self the new parent of the child
        self.children.append(child)
        child.parent = self

        # print("Add ", child.name, "as child to",self.name)
    
    def putFoldersOnTop(self):
        # Organize folders and nodes in the tree
        # Folders first, then nodes
        # Sort children by isFolder 
        self.children.sort(key=lambda x: (x.isFolder))

    def getChildrenNames(self,folderOnly=False,recursive=False)->list[str]:
        result=[]
        children:list[TreeNode] = self.children
        for child in children:
            if (folderOnly and child.isFolder) or folderOnly==False:
                result.append(child.name)

            if recursive and child.isFolder:
                result += child.getChildrenNames(folderOnly,recursive)
        return result
    def getChildrenShapeKeys(self,recursive=False)->list[str]:
        result=[]
        children:list[TreeNode] = self.children
        for child in children:
            result.append(child.shapeKey)
            if recursive and child.isFolder:
                result += child.getChildrenShapeKeys(recursive)
        return result
    
    # Checks
    def hasChildren(self):
        return len(self.children)>0
    

class TreeNodeWithParent(TreeNodeWithChildren):
    parent:TreeNodeWithChildren=None

    def hasParents(self):
        # Check if node has parents
        return self.parent != None
    
    def isRootNode(self):
        return self.parent==None

    def hasGrandParents(self):
        if self.hasParents():
            parent:TreeNodeWithParent=self.parent
            if parent.hasParents():
                return True
        
        # No grandparent
        return False

    def parentIsCollapsed(self):

        if self.parent:
            parent:TreeNodeWithParent = self.parent
            # Check if parent is collapsed
            isClosed = parent.isOpen() == False
            return isClosed or parent.parentIsCollapsed()
        
        return False
    
    def moveMe(self, type="DOWN"):
        # Move child up in the list of children
        if not self.parent:
            print("No parent found, nothing to move")
            return
        
        index=self.parent.children.index(self)

        if type == "UP":
            self.parent.children.remove(self)
            self.parent.children.insert(index-1, self)
        elif type == "DOWN":
            self.parent.children.remove(self)
            self.parent.children.insert(index+1, self)
        elif type == "TOP":
            self.parent.children.remove(self)
            self.parent.children.insert(0, self)
        elif type == "BOTTOM":
            self.parent.children.remove(self)
            self.parent.children.append(self)

        self.parent.putFoldersOnTop()

    def remove(self):
        # Remove node from parent
        if self.parent and self in self.parent.children:
            parentChildren:list[TreeNode] = self.parent.children
            parentChildren.remove(self)

        # Also remove all children from the node
        if len(self.children)>0:
            # Remove all children from the parent
            for child in self.children:
                child.remove()
                child.parent=None

        # Remove all references to other objects
        self.shapeKey=None
        self.children=None
        self.parent=None
    

    # Shape key actions
    def addShapeKeyAsChild(self, shapeKey):
        node=TreeNode(shapeKey.name, shapeKey)
        self.addChild(node)

        return node
    
    def addShapeKeyAsSibling(self, shapeKey:ShapeKeyInterface):
        node=TreeNode(shapeKey.name, shapeKey)
        if self.hasParents():
            # Add to parent
            self.parent.addChild(node)
        else:
            print("Not added, No parent found")

    def getAllShapeKeys(self):
        keys=[self.shapeKey] if self.shapeKey else []

        for child in self.children:
            if child.isFolder:
                keys += child.getAllShapeKeys()
            else:
                keys.append(child.shapeKey) 

        return keys
    

class TreeNode(TreeNodeWithParent):

    def __init__(self, name, shapeKey:ShapeKeyInterface=None, children=[]):
        self._name = name
        self.shapeKey = shapeKey
        self.children = []

        # No shapekey: node is folder and open
        self.isFolder=core.key.is_folder(shapeKey) if shapeKey else True

    def isOpen(self):
        if self.isFolder:
            return core.folder.get_block_value(self.shapeKey, 'expand') if self.shapeKey else True
    
        return True

    def __repr__(self):
        return f"Node(name={self.name}, index={self.index}, children={self.children})"

    # Transformations
    def getAsFlatList(self,visited:list[str],level=0, recursive=True)->list[BaseTreeNode]:
        """The flatlist is used to get all required data to display the treestructure of ShapeKeys properly in the UI"""
        # Get a flat list of all children and their children

        flatList=[self]

        self.indent=level

        # Skip root node
        if self.isRootNode():
            flatList = []

        visited.append(self.name)

        if self.hasChildren() and (self.isOpen() or recursive):
            children:list[TreeNode] = self.children
            for child in children:
                if child.name not in visited:
                    visited.append(child.name)
                    flatList += child.getAsFlatList(visited,level+1,recursive)
                else:
                    print("Already visited ",child.name, ". Is recurring as a child in",self.name)
        return flatList
    
    # Legacy
    def getAsLegacyArray(self)->list[str]|str:
        """Used to store the tree-structure in the object with the shape keys\n
        This keeps the stored tree clean from object references and will prevent potential memory leaks"""
        if self.hasChildren():
            childNodesArray= [child.getAsLegacyArray() for child in self.children]

            if self.isRootNode():
                # Root node does not include itself
                return childNodesArray

            # Node is folder and first in array
            return [self.name]+childNodesArray

        # Retrurn string value of name
        return self.name
    
    # Legacy
    def getAncestryNames(self)->list[str]:
        # Oldest ancestors first
        parent:TreeNode=self.parent

        if parent:
            return  self.parent.getAncestryNames() + [self.parent.name] if self.parent else []
        
        # No parent, no ancestors
        return []

    def getAncestryShapeKeys(self)->list[ShapeKeyInterface]:
        # Oldest ancestors first
        parent:TreeNode=self.parent

        if parent:
            return  self.parent.getAncestryShapeKeys() + [self.parent.shapeKey] if self.parent else []
        
        return [self.parent.shapeKey]

class LegacyTreeStructureParser:

    def isFolder(self, node)->bool:
        # check if node is of type string
        isString=type(node) is str

        return not isString

    def getNewShapeKeyNode(self,shapeKeyName:str)->TreeNode|None:
        if bpy.context.active_object and bpy.context.active_object.data.shape_keys:
            shapeKey = bpy.context.active_object.data.shape_keys.key_blocks[shapeKeyName]
            return TreeNode(shapeKeyName,shapeKey)
        
        # Not found
        return None
    
    def getTreeFromShapeKeys(self, shapeKeys:ShapeKeyInterface)->list[str|list[str]]:
        # Uses key.vertex_group to identify if it is a folder or not
        # then collects the children of the key
        # ShapeKeys need to be organized in order of tree structure for this
        # This can only be done by moving the shapekeys in the list of shapekeys
        # - Either to the bottom, in order of appearance in the floder structure
        # - Or step by step, as is done in the original code
        #
        # Moving shape keys in the old code becomes more and more expensive as the ShapeKey list grows
        # Inthe new code, we create a separate tree structure as an organized view on the unorganized shape key list
        # And we leave the shape-key list as is
        
        branch = []
        
        stop = len(shapeKeys)
        
        i = 0
        
        while i < stop:
            key = shapeKeys[i]
            # Legacy
            children = core.folder.get_children(key)
            
            if core.key.is_folder(key):
                branch.append([key.name] + list(itertools.chain(self.getTreeFromShapeKeys(children))))
            else:
                branch.append(key.name)
            
            # Skip children we found
            i += 1 + len(children)
        
        return branch
    
    def parseArrayNode(self,nodeNameArray,parentNode:TreeNodeWithParent=None)->TreeNodeWithParent:
        # Self-iterating loop to parse treestructure from named vars
        # Node contains [key, key, [foldername, childNodes,[foldername,chilsnondes]]]
        
        # Folder[0] = foldernae
        # folder[1++] = children
        
        # Handle list of nodes
        for nodeName in nodeNameArray:
            if self.isFolder(nodeName):
                # Child is a folder
                folderName=nodeName[0]
                newFolder = self.getNewShapeKeyNode(folderName)

        
                if not newFolder:
                    # Shapekey not found. Possibly renamed or removed
                    newFolder = TreeNode(folderName)

                # Add folder to given treenode
                parentNode.addChild(newFolder)


                # Get children
                children=nodeName[1:]
                # parse node for its children
                self.parseArrayNode(children,newFolder)

                # print("New folder",newFolder.name," whit children:",len(newFolder.children))


            else: 
                # print("Add Key",nodeName)
                # Not a folder, so it is a shapekey
                node = self.getNewShapeKeyNode(nodeName)

                if node: # We found the Shape Key
                    parentNode.addChild(node)

        return parentNode

class StoredTreeParser:

    parser=LegacyTreeStructureParser()

    def _getStoredTreeFromObject(self):
        selectedObject=bpy.context.active_object
        print("REstore from obhject")
        return selectedObject[TREE_STORE_NAME] or []
    
    def hasStoredTree(self):
        selectedObject=bpy.context.active_object

        hasStoredTree=TREE_STORE_NAME in selectedObject
        print ("Object",selectedObject.name,TREE_STORE_NAME,"has a stored tree",hasStoredTree)
        return hasStoredTree

    def storeTree(self, rootNode:TreeNode):
        # Store parsed tree in object
        
        selectedObject=bpy.context.active_object
        print ("Store tree on ",selectedObject.name)
        selectedObject[TREE_STORE_NAME]=rootNode.getAsLegacyArray()
        hasStoredTree=hasattr(selectedObject,TREE_STORE_NAME)
        print ("Tree stored",hasStoredTree)


    def getStoredTree(self)->TreeNode:
        if self.hasStoredTree():
            print("Restore tree from Object (new style)")
            return self._parseStoredTree()
        else:
            # Parse legacy
            print("Restore tree from Shape Keys (legacy)")
            return self._parseLegacyTree()

    def _parseStoredTree(self)->TreeNode:
        # Parse the old tree into a new tree
        # Parse old tree
        newTree = TreeNode("Root")

        storedTreeStructure=self._getStoredTreeFromObject()
        #print(storedTreeStructure)
        result=self.parser.parseArrayNode(storedTreeStructure,newTree)
        return result
        # Done

    def _parseLegacyTree(self)->TreeNode:
        # Is derived from Shapekey++ setup
        legacyTreeStructure = []

        selectedObject=bpy.context.active_object
        if bpy.context.active_object and selectedObject.data.shape_keys:
            legacyTreeStructure = self.parser.getTreeFromShapeKeys(selectedObject.data.shape_keys.key_blocks)
        
        #print(legacyTreeStructure)

        # Parse the old tree-structure into our new tree structure
        # Parse old tree
        newTree = TreeNode("Root")
        result=self.parser.parseArrayNode(legacyTreeStructure,newTree)
        # Done

        return result



class PkTree:

    parser=StoredTreeParser()

    dictionary={}

    shapeKeyTreeOrder=[]
    selectedShapeKeys=[]

    rootNode:TreeNode=TreeNode("Root")

    flatList:list[TreeNodeWithParent]=[]

    activeObject=None

    @classmethod
    def __init__(self):
        self.cache = {}
 
            
    def __str__(self):
        import json
        return json.dumps(self, indent=4, default=repr)

    def checkStatus(self):

        activeObject=bpy.context.active_object
        
        if self.activeObject != activeObject:
            self.init(activeObject)
            print("Activate tree for", activeObject.name)
        
        return self

    def init(self, activeObject):
        print("Mesh selected. Creating new tree")
        # Original solution used skhape keys only to resolve the tree
        # This gave several uissues:
        # 1: Moving things around would:
        # 1: Lead to Folders being displaced
        # 2: Mean moving Shape Keya around, which would make Blender hang with a lot of shape keys
        self.activeObject=activeObject
        # Prefer to take the stored keys

        self.reset()

        activeObject=bpy.context.active_object
        if activeObject.data.shape_keys:
            self.rootNode=self.parser.getStoredTree()

            key_blocks = bpy.context.active_object.data.shape_keys.key_blocks

            print("Rootbode had childern",len(self.rootNode.children))
            self.updateFlatLists()

            print("Tree has been parsed and has ",len(self.flatList),"elements. There are shapekeys:",len(key_blocks))
        # print([item.name for item in self.flatList])

        # print([item.name for item in key_blocks])
    
        return self

    def reset(self):
        self.dictionary={}
        self.flatList=[]

        self.shapeKeyTreeOrder=[]
        self.selectedShapeKeys=[]

    rootNode:TreeNode=TreeNode("Root")

    flatList:list[TreeNodeWithParent]=[]

    def getShapeKey_TreeOrder(self):
        key_blocks = bpy.context.active_object.data.shape_keys.key_blocks

        # [key.name for key in get_selected()]
        treeOrder=[key.name for key in self.flatList]

        # Returns index of where the key is in the tree order
        keyOrder=[treeOrder.index(key.name) for key in key_blocks if key.name in treeOrder]
        
        self.shapeKeyTreeOrder=keyOrder
        return keyOrder

    def keyIsSelected(self, keyName):
        # Check if key is selected in the tree
        return keyName in self.selectedShapeKeys 

    def getShapekeysAreSelected(self):
        return self.selectedShapeKeys and len(self.selectedShapeKeys)>0
    
    def getAncesterIsSelected(self, keyName):
        # Check if any of the parents of the key are selected in the tree
        node=self.getNodeByName(keyName)
        if node:
            ancestors= node.getAncestryNames()
            isSelected=bool([p for p in ancestors if p in self.selectedShapeKeys])

            return isSelected
        
        return False

    def updateFlatLists(self):  
        
        # Get a flat list of all nodes in the tree
        self.flatList = self.rootNode.getAsFlatList([])

        self.dictionary={item.name: item for item in self.flatList}

        print("updateFlatLists priudiced a flatlist with elements",len(self.flatList))

        # With this we determine the sort order of the shape keys in the tree
        self.shapeKeyTreeOrder = self.getShapeKey_TreeOrder()

        self.selectedShapeKeys = []+[key.name for key in core.key.get_selected()]

    def getFlatlist(self,folderOnly=False):
        if folderOnly:
            return [item for item in self.flatList if item.hasChildren()]
        
        return self.flatList
    
    def moveNode(self,name,type):
        node=self.getNodeByName(name)
        if node:
            node.moveMe(type)
    
    def getAncestryNames(self,name):
        node=self.getNodeByName(name)
        
        if not node:
            return []
        
        return node.getAncestryNames()

    def getNodeByName(self,nodeName)->TreeNode|None:
        
        
        result = self.dictionary[nodeName]

        if not result:
            print("Did not find ",nodeName,"in list hwith length",len(self.flatList))

        return result if result else None

    
    def findNodesInFLatlist(self,shapekeyNameList:list[str])->list[TreeNode]:
        # Get nodes
        nodeList=[x.node for x in self.flatList if x.name in shapekeyNameList]

        return nodeList
       
    def update(self):
        """1: Applies the changes to the flatlist that is used to display the tree\n
        2: Stores the nested tree structure (string references) in the selected mesh that contains the shapekeys\n"""

        # Apply the changes to the tree
        self.updateFlatLists()
        self.parser.storeTree(self.rootNode)


tree:PkTree=PkTree()




