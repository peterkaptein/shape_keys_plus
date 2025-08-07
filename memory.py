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
    _name:str=""

    children:list=[]
    parent=None

    isFirst:bool=False
    isLast:bool=False

    @property
    def name(self)->str:
        # Always present the correct name
        if self.shapeKey:
            try:
                self._name=self.shapeKey.name
                return self.shapeKey.name
            except Exception as e:
                # Handle any exception
                print(f"An error occurred: {e}, restoring name to stored name")
                try:
                    self.shapeKey.name=self._name
                except Exception as e:
                    print(f"An error occurred: {e}, unableto restore name to stored name")
            
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
        if not self.children:
            self.children=[]
            return False

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

    def parentIsClosed(self):

        if self.parent:
            parent:TreeNodeWithParent = self.parent
            # Check if parent is collapsed
            isClosed = not parent.isOpen()
            return isClosed or parent.parentIsClosed()
        
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

    def remove(self)->ShapeKeyInterface:
        
        nextNode=None

        # Remove node from parent
        if self.parent and self.parent.children and self in self.parent.children:

            parentChildren:list[TreeNode] = self.parent.children

            myIndex=parentChildren.index(self)

            parentChildren.remove(self)

            if myIndex<len(parentChildren)-1:
                myIndex=0

            
            if len(parentChildren)==0 and len(parentChildren)>myIndex:
                nextNode=parentChildren[myIndex].shapeKey
            else:
                nextNode=self.parent.shapeKey

            
                

        # Also remove all children from the node
        if self.children and len(self.children)>0:
            # Remove all children from the parent
            for child in self.children:
                child.remove()
                child.parent=None

        # Remove all references to other objects
        self.shapeKey=None
        self.children=None
        self.parent=None
    
        return nextNode

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

            print("Added copy",node.name,"To parent",self.parent.name)
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
            if self.shapeKey:
                if not core.key.is_folder(self.shapeKey):
                    self.shapeKey.vertex_group = core.folder.generate()    

                return core.folder.get_block_value(self.shapeKey, 'expand') if self.shapeKey else True
        return True

    def __repr__(self):
        return f"Node(name={self.name}, index={self.index}, children={self.children})"

    # Transformations
    def getAsFlatList(self,visited:list[str],level=0, recursive=True,includemissingShapeKeys=False)->list[BaseTreeNode]:
        """The flatlist is used to get all required data to display the treestructure of ShapeKeys properly in the UI"""
        # Get a flat list of all children and their children

        flatList=[self]

        isWrongNode=not self.shapeKey

        if isWrongNode and not includemissingShapeKeys:
            # Skip self
            flatList=[]

        self.indent=level

        # Skip root node
        if self.isRootNode():
            flatList = []
            level=-1 # prevents wrongful indenting

        visited.append(self.name)

        if self.hasChildren() and includemissingShapeKeys:
            print("Folder:",self.name)

        if self.hasChildren() and (self.isOpen() or recursive):
            children:list[TreeNode] = self.children
            lastIndex=len(children)-1
            index=0
            for child in children:
                
                index+=1
                child.isFirst=index==1
                child.isLast=index==lastIndex

                if child.name not in visited:
                    visited.append(child.name)
                    flatList += child.getAsFlatList(visited,level+1,recursive,includemissingShapeKeys)
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

        if parent and parent.hasParents():
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
            if shapeKeyName in bpy.context.active_object.data.shape_keys.key_blocks:
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
        print("Restore from object")
        tree=selectedObject[TREE_STORE_NAME] or []
        print("on object ",bpy.context.active_object.name)
        return tree
    
    def hasStoredTree(self):
        selectedObject=bpy.context.active_object

        hasStoredTree=TREE_STORE_NAME in selectedObject
        print ("Object",selectedObject.name,TREE_STORE_NAME,"has a stored tree",hasStoredTree)
        return hasStoredTree

    def storeTree(self, rootNode:TreeNode):
        # Store parsed tree in object
        
        try:
            selectedObject=bpy.context.active_object
            print ("Store tree on ",selectedObject.name)
            selectedObject[TREE_STORE_NAME]=rootNode.getAsLegacyArray()
            print ("Tree stored")
        except:
            print("Tree not stored due to error")


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

    buffered_flt_flags=[]
    buffered_name_filters=[]
    previousSearch=""
    previousItenCount=0

    _hasIssues=False
    issuesDescriptions=""

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

    def hasIssues(self):
        return self._hasIssues

    def updateAndSanitizeFlatTree(self, fixDirectories=False):
        
        self._hasIssues=False
        self.issuesDescriptions=""

        self.updateFlatLists()

        print("Sanitizing. Flatlist has",len(self.flatList),"elements")
        """Do sanity check and fix issues if found. Also saves sanitized tree to object."""
        key_blocks=key_blocks = bpy.context.active_object.data.shape_keys.key_blocks

        shapeKeyNames=[key.name for key in key_blocks]
        nodeNames=[key.name for key in self.flatList]

        foldernames=self.rootNode.getChildrenNames(folderOnly=True,recursive=True)

        # Keys have been renamed or removed and not properly processed
        fullFlatList=self.rootNode.getAsFlatList([],includemissingShapeKeys=True) 

        missingShapeKeys=[node for node in fullFlatList if node.name not in shapeKeyNames]
        unmappedShapeKeys=[key for key in key_blocks if key.name not in nodeNames]

        missingFolders=[node for node in missingShapeKeys if node.hasChildren()]

        hasChangedFolderStru=False


        # Remove wrong keys in our viewmodel
        if missingShapeKeys:
            self._hasIssues=True
            self.issuesDescriptions=self.issuesDescriptions+"Missing shape keys, including",len(missingFolders), " folders. "

            print("Found",len(missingShapeKeys)," references of non-existing shape keys in tree")
            for node in missingShapeKeys:

                # Not a folder
                if not node.hasChildren():
                    node.remove()

                # A folder, something went wrong copying shapekeys from anbother object
                # Or structure is assigned to wrong object
                # User decided to force new structure by pressing button
                if node.hasChildren():
                    print("Missing node is a folder:",node.name)
                    if fixDirectories :
                        hasChangedFolderStru=False
                        print("Creating folder",node.name)
                        newShapeKey = core.key.add('FOLDER')
                        newShapeKey.name=node.name
                        node.shapeKey=newShapeKey

        # Add missing shapekeys to root of tree
        if unmappedShapeKeys:

            print("Adding ",len(unmappedShapeKeys),"missing shape keys to Root")
            for key in unmappedShapeKeys:
                tree.rootNode.addShapeKeyAsChild(key)

        # Fix dirs also include detemining if something is a folder or not
        # After copying shapekeys with DAz TOOLS, not all info is there
        if fixDirectories:
            for node in fullFlatList:

                if node.children:
                    if node.shapeKey and not core.key.is_folder(node.shapeKey):
                    
                        print("Shapekey not a folder. Force shapekey to be a folder",node.name)
                        node.shapeKey.vertex_group = core.folder.generate()    
                    # Set to be a folder
                    node.isFolder=True

        # Update list only when something went wrong
        # Also stor in object, so it contains sanitized version
        if missingShapeKeys or unmappedShapeKeys or fixDirectories:
            self.updateFlatLists()
            self.parser.storeTree(self.rootNode)

        return not (missingShapeKeys or unmappedShapeKeys)

    def getFlatlist(self,folderOnly=False):
        if folderOnly:
            return [item for item in self.flatList if item.isFolder]
        
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

        if nodeName==self.rootNode.name:
            return self.rootNode
        
        if nodeName not in self.dictionary:
            # Something changed the name of a property
            # Now the key cannot be found
            # 1: We need to update the flatlist. This will probablu fix it,
            #    As the shapekey with changed name is still connected
            # 2: We do a sanity check, just in case something else happened
            self.updateAndSanitizeFlatTree()
        

        result = self.dictionary[nodeName]

        if not result:
            print("Did not find ",nodeName,"in list hwith length",len(self.flatList))

        return result if result else None

    
    def findNodesInFLatlist(self,shapekeyNameList:list[str])->list[TreeNode]:
        # Get nodes
        nodeList=[x.node for x in self.flatList if x.name in shapekeyNameList]

        return nodeList
       
    def update(self,clearSelections:bool=False):
        """1: Applies the changes to the flatlist that is used to display the tree\n
        2: Stores the nested tree structure (string references) in the selected mesh that contains the shapekeys\n"""

        # Apply the changes to the tree
        self.updateAndSanitizeFlatTree() # Removes all non-existing keys, adds missing from Shape Key list
        self.parser.storeTree(self.rootNode) # Stores the tree to the selected object
        print("Tree has been updated")

        if clearSelections:
            # Done with operation, clear selections
            self.clearShapeKeySelection()

    def clearShapeKeySelection(self):
        active = bpy.context.active_object
        selections = active.data.shape_keys.shape_keys_plus.selections
        selections.clear()

tree:PkTree=PkTree()




