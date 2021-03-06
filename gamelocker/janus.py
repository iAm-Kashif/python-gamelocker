__author__ = "Bruno Hautzenberger"
__copyright__ = "Copyright 2015, xamoom GmbH"
__version__ = "0.4.3"
__maintainer__ = "Bruno Hautzenberger"
__email__ = "bruno@xamoom.com"
__status__ = "Development"
__url__ = "https://github.com/xamoom/xamoom-janus"

"""
Copyright (c) 2015, xamoom GmbH

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

"""
janus

A module to serialze python objects to json api compatible messages
and also deserialize json api messages back to python objects.
spec: http://jsonapi.org/
"""

import json
import copy
import collections

#--- exceptions ---

import hashlib
import time

class JanusException(Exception):
    """
    contains additional information to exceptions to return as much information as possible
    using an ErrorMessage object as specified in jsonapi.
    """

    id = None #a unique identifier for this particular occurrence of the problem.

    #the HTTP status code applicable to this problem, expressed as a string value.
    #if we get no specificerror code (derived Exceptions will set their own) we use 503 (internal server error).
    status = 503

    #an application-specific error code, expressed as a string value. (will be set by derived exceptions or by the one raising the exception)
    code = -1

    #get's set while raising the exception. a short, human-readable summary of the problem that SHOULD NOT change from occurrence to occurrence of the problem, except for purposes of localization.
    title = ""

    #get's set while raising the exception. a human-readable explanation specific to this occurrence of the problem.
    detail = None

    #get's set while raising the exception. a meta object containing non-standard meta-information about the error.
    #this has to be none or a dict of primitive types.
    #TODO verify that
    meta = None

    def __init__(self,title="",detail="",status="",code=-1,meta=None):
        Exception.__init__(self,self.title)

        self.title = title
        self.detail = detail
        self.status = status
        self.code = code
        self.meta = meta

        #we use a string representation of all we got in details plus timestamp as hash to identify this error.
        #So we can search for it in the logs, if we need to.
        self.id = hashlib.sha1(
                                str(time.time()) +
                                str(self.title) +
                                str(self.detail) +
                                str(self.status) +
                                str(self.code) +
                                str(self.meta)
                              ).hexdigest()

class BadRequestException(JanusException):
    """
    represents a Bad Request exception (HTTP 400)
    """
    def __init__(self, detail=None, code=-1, meta = None):
        JanusException. __init__(self,
            title="The web server was unable to understand the request and process it.",
            detail=detail,
            status=400,
            code=code,
            meta=meta)

class UnauthorizedException(JanusException):
    """
    represents a Unauthorized exception (HTTP 401)
    """
    def  __init__(self, detail=None, code=-1, meta = None):
        #just call super with some prefilled information fitting this special type of exception
        JanusException. __init__(self,
            title="The request can not be process, because authorization is missing.",
            detail=detail,
            status=401,
            code=code,
            meta=meta)

class ForbiddenException(JanusException):
    """
    represents a Forbidden exception (HTTP 403)
    """
    def  __init__(self, detail=None, code=-1, meta = None):
        #just call super with some prefilled information fitting this special type of exception
        JanusException. __init__(self,
            title="You are not allowed to access this resource.",
            detail=detail,
            status=403,
            code=code,
            meta=meta)

class NotFoundException(JanusException):
    """
    represents a not found exception (HTTP 404)
    """
    def  __init__(self, detail=None, code=-1, meta = None):
        #just call super with some prefilled information fitting this special type of exception
        JanusException. __init__(self,
            title="The requested resource could not be found but may be available again in the future. Subsequent requests by the client are permissible.",
            detail=detail,
            status=404,
            code=code,
            meta=meta)

class DeveloperException(JanusException):
    """
    represents an Exception caused by Developer Error
    """
    def  __init__(self, title="Developer Error", detail=None, code=-1, meta = None, status = 500):
        #just call super with some prefilled information fitting this special type of exception
        JanusException. __init__(self,
            title=title,
            detail=detail,
            status=500,
            code=code,
            meta=meta)

class InternalServerErrorException(JanusException):
    """
    represents a Internal Server Error exception (HTTP 500)
    """
    def  __init__(self, detail=None, meta = None):
        #just call super with some prefilled information fitting this special type of exception
        JanusException. __init__(self,
            title="Internal Server Error",
            detail=detail,
            status=500,
            code="42", #this is always error 42, because this should never happen on production.
            meta=meta)

#--- ---

class JanusResponse(object): #JSON API Message Object see: http://jsonapi.org/format/#document-structure
    """
    Represents a jsonapi compatible message.
    This is the root type for all messages transmitted using jsonapi decorator
    spec: http://jsonapi.org/format/#document-structure
    """
    
    message = None #the message typ to return
    data = None #an object, or a list of objects that should be returned from this message as data payload
    meta = None #custom, non json api standard meta data as dict of simple types (no objects please)
    include_relationships = None #flag to overrule this flag in the decorator.
    
    def __init__(self,data=None,meta=None,message=None,include_relationships=None):
        self.data = data
        self.meta = meta
        self.message = message
        self.include_relationships = include_relationships
        
        #check data
        if self.data == None:
            raise Exception("JanusResponse data can't be None.")
        
        #check message
        if self.message == None:
            raise Exception("JanusResponse message can't be None.")
        
        #check message type
        if issubclass(self.message,DataMessage) == False:
            raise Exception("JanusResponse message must be subclass of janus.DataMessage.")
        
        #check meta
        if self.meta != None and isinstance(self.meta,dict) == False:
            raise Exception('Meta has to be a dict with non jsonapi standard information.')

class JsonApiMessage(object): #JSON API Message Object see: http://jsonapi.org/format/#document-structure
    """
    Represents a jsonapi compatible message.
    This is the root type for all messages transmitted using jsonapi decorator
    spec: http://jsonapi.org/format/#document-structure
    """

    data = None #an object, or a list of objects, derived from janus.DataMessage or a list of such objects. Represents a json api data object.
    meta = None #custom, non json api standard meta data as dict of simple types (no objects please)
    errors = None #a list of objects derived from janus.ErrorMessage or a list of such objects. Represents a json api error object.
    included = None #an array of resource objects that are related to the primary data and/or each other ("included resources").

    def __init__(self,data=None,errors=None,included=None,meta=None):
        """
        initializes the object
        at least one of the three objects (data,errors,meta) has to be set.
        """
        if errors == None and data == None and meta == None:
            raise Exception('JSON Api message has to contain at least one of these members: data, errors and/or meta.')

        self.errors = errors
        self.data = data
        self.meta = meta
        
        self.included = included

    def __setattr__(self, name, value):
        """
        overrides __setattr__ to check if data and errors aren't set at the same time.
        """
        if value != None:
            if (name == "errors" and self.data != None) or (name == "data" and self.errors != None):
                raise Exception('JSON Api message may only contain data or errors, not both.')

        #call default __setattr__
        object.__setattr__(self, name, value)

    def to_json(self):
        """
        returns a json representation of the message.
        This is always a valid json api message according to http://jsonapi.org/format/#document-structure
        """

        msg = {} #initializes a dict which will later be turned into json
        if self.data != None: #if data is present add it to the message
            if isinstance(self.data, (list, tuple)): #if data is list of objects transform these objects to a list of dicts
                #call to_dict on all data objects to get a dict representation of the data object
                #and write this as a list to the message
                msg['data'] = [d.to_dict() for d in self.data]
            else:
                msg['data'] = self.data.to_dict() #set the data object dicts to the message

        if self.errors != None:
            if isinstance(self.errors, (list, tuple)):
                msg['errors'] = [e.to_dict() for e in self.errors]
            else:
                msg['errors'] = [self.errors.to_dict(),]

        if self.included != None: msg['included'] = self.included #if included is present add it to the message
        
        if self.meta != None: msg['meta'] = self.meta #if meta is present add it to the message
        
        json_msg = json.loads(json.dumps(msg)) #serialize dict to json and return
        

        return json_msg

class Attribute(object): #Attribute Class to map Data from input Object to Message Object
    """
    Repesents an attribute in the DataMessage object that will be present
    in the final json api message.
    This is used to hold it's value as well as all configuration for the
    transformation to json.
    """

    __primitive_types = (str,int,float,bool) #all allowed types for attribute values. (lists and dicts are also allowed, but treated differently)

    value = None #holds the actual value of this attribute once it is set.
    
    value_type = None #the value type of this attribute. Used for value verification.
    name = "" #the name of this value in json.
    required = True #indicates if this attribute is required or not.
    mapping = None #tells the mapping function (DataMessage.map_object) how to get the value for this
    
    key_mapping = None #tells the mapping function how to get type and id of a related entity without loading the whole entity. This is used only for relationships.
    key_value = None #holds the actual key
    
    read_only = False #only for request messages. If property is readonly it won't be serialized back. #TODO implement this.
    write_only = False #only for request messages. If property is writeonly it won't be included in responses (passwords on users for example). #TODO implement this.
    updated = False #only for request messages. True if property was present in the request and therefor has to be updated.
    
    def __init__(self,value_type=value_type,name=name,required=False,mapping=None,key_mapping=None,read_only=False,write_only=False):
        """
        initializes the object
        sets all needed configurations and checks if value is a primitive type or list or dict.
        """

        if issubclass(value_type, self.__primitive_types + (list, dict)) or issubclass(value_type,DataMessage):
            self.value_type = value_type
            self.name = name
            self.required = required
            self.mapping = mapping
            self.read_only = read_only
            self.write_only = write_only
            
            if issubclass(value_type,DataMessage): #relationship
                self.key_mapping = key_mapping
        else:
            raise Exception('Value Type must be either be a simple type such as ' + str(self.__primitive_types) + ', a subclass of DataMessage or a list or dict containing these types.')

    #TODO USE THIS WHEN OBJECT GETS FILLED WITH VALUES
    def __check_list(self,list_value):
        for item in list_value:
            if not item in self.__primitive_types:
                raise Exception('Attribute ' + self.name + ' contains invalid object of type ' + str(type(item)) + ". Valid types are " + str(self.__primitive_types))

class DataMessage(object): #JSON API Data Object see: http://jsonapi.org/format/#document-structure
    """
    Repesents a DataMessage object that will be present in the final json api message.
    This is used as a base class for all message template objects.
    Do not initialize this or derived objects yourself. Always inherit from this object
    and use class method "from_object" to initialize it with a fitting object containing
    members fitting the Attribute mappings to get the Attribute values from.

    spec: http://jsonapi.org/format/#document-structure
    """

    id = None #the data object's id (has to be set for each json api data object)
    __type_name = None #the data object's type (has to be set for each json api data object)
    
    __data_object = None #the data object that holds the data for the message

    def __init__(self):
        """
        initializes the object
        sets __type_name to the name type name of the derived class.
        __type_name can be overriden by creating a member "type_name" in the derived class
        and setting a new string value to it.
        This method also reinitializes all members containing Attribute objects by full
        copies of the objects, so every instance of this get's also its own Attribute objects.
        """

        #set type name to class name (takes name of sub class)
        self.__type_name = self.__class__.__name__

        ### START ATTRIBUTE COPY """
        #get all members of the sub class containing Attribute objects
        attributes = {attr:object.__getattribute__(self,attr).value
                        for attr in dir(self)
                            if not isinstance(object.__getattribute__(self,attr), collections.Callable)
                            and type(object.__getattribute__(self,attr)) == Attribute
                            and not attr.startswith("__")}

        #reinitialize all members containing Attribute objects by full
        #copies of the objects, so every instance of this get's also its own Attribute objects.
        #otherwise they would share these objects resulting in all instances having the same value,
        #which is bad. ;-)
        for attr in attributes:
            object.__setattr__(self,attr,copy.deepcopy(object.__getattribute__(self,attr)))
            
    def __get_id_attribute(self):
        #check if there is a id attribute in the subclass
        result = [attr for attr in dir(self)
                    if not isinstance(getattr(self,attr), collections.Callable)
                    and type(object.__getattribute__(self,attr)) == Attribute
                    and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == False
                    and object.__getattribute__(self,attr).mapping != None
                    and object.__getattribute__(self,attr).name == 'id'
                    and not attr.startswith("__")]
        
        if len(result) == 1: #id attribute found
            return result[0]
        else:
            raise Exception(self.__type_name + " is missing Attribute 'id'.")
        
    def __convert_to_value_type(self,name,value):
        if value == None:
            return None
        else:
            #try to convert to desired type for simple types
            if issubclass(object.__getattribute__(self,name).value_type,DataMessage) == False:
                _type = object.__getattribute__(self,name).value_type
                try:
                    return _type(value)
                except:
                    raise AttributeError("Failed to convert " + str(value) + " to " + str(_type) + " in " + self.__type_name)
            else: 
                return value

    def __setattr__(self, name, value):
        """
        Overrides the default behaviour of members assignments to make members containing
        Attribute objects behave like members contaning a simple type like int or str.
        So this causes assignments to set the value of the Attribute object inside
        the actual member to be set instead of overriding the whole object on
        assignment.
        """
        if type(object.__getattribute__(self,name)) == Attribute or name == "id":
            #if this set's id we also set id to the member that contains id in the subclass
            is_id = False
            if name == "id":
                is_id = True
                name = self.__get_id_attribute()
                
            #convert value to defined value_type
            value = self.__convert_to_value_type(name, value)
            
            #set value
            object.__getattribute__(self,name).value = value
            object.__getattribute__(self,name).updated = True
            
            if is_id:
                object.__setattr__(self, "id", value) #set value to id
            
        else: #if the member does not contain an Attribute object, act normal.
            object.__setattr__(self, name, value)

    def __getattribute__(self, name):
        """
        Overrides the default behaviour of gettting member values containing Attribute
        objects, to return the value of the Attribute object instead of the whole
        Attribute object.
        """        
        try:
            if type(object.__getattribute__(self,name)) == Attribute:
                return object.__getattribute__(self,name).value
            else: #if the member does not contain an Attribute object, act normal.
                return object.__getattribute__(self,name)
        except AttributeError: #if message does not contain an Attribute, return None
            return None

    def to_dict(self):
        """
        Returns a dict representation of this objects's members containing Attribute
        objects, with their configured name as key and their values.
        The dict is already in a jsonapi format.
        """

        #initialize the dict with id and type, because they are mandatory in json api.
        msg = {
            'id': str(self.id),
            'type': self.__type_name
        }

        #get all members of the subclass containing Attribute members that are not relations, which do not contain
        #None as value and their name is not id, because id is treated diferrently, as a
        #a dict fitting the jsonapi specification for the data objects "attributes" member.
        #key => attribute name as specified in the Attribute object
        #value => the loaded valvue from the object(s) given to "from_object"
        attributes = {object.__getattribute__(self,attr).name:object.__getattribute__(self,attr).value
                        for attr in dir(self)
                            if not isinstance(object.__getattribute__(self,attr), collections.Callable)
                            and type(object.__getattribute__(self,attr)) == Attribute
                            and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == False
                            and not attr.startswith("__")
                            and object.__getattribute__(self,attr).name != 'id'
                            and object.__getattribute__(self,attr).value != None}

        #if there are attributes we add them to the dict using "attributes" as key.
        if len(list(attributes.keys())) > 0: msg['attributes'] = attributes
        
        #get all members of the subclass containing Attribute members that are relations, which do not contain
        #None as key_value and their name is not id, because id is treated diferrently, as a
        #a dict fitting the jsonapi specification for the data objects "relations" member.
        #key => attribute name as specified in the Attribute object
        #value => the loaded relations key (type and id) from the object(s) given to "from_object"
        relations = {object.__getattribute__(self,attr).name:object.__getattribute__(self,attr).key_value
                        for attr in dir(self)
                            if not isinstance(object.__getattribute__(self,attr), collections.Callable)
                            and type(object.__getattribute__(self,attr)) == Attribute
                            and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == True
                            and not attr.startswith("__")
                            and object.__getattribute__(self,attr).name != 'id'
                            and object.__getattribute__(self,attr).key_value != None}

        #if there are relations we add them to the dict using "relations" as key.
        if len(list(relations.keys())) > 0: msg['relationships'] = relations


        return msg

    def map_object(self,obj,include_relationships=True):
        """
        Used to set values from a python object, as specified in the Attribute objects
        of the sub class of this, to the values of the Attribute objects of the sub class.
        So in other words, this is the data mpping from object to DataMessage object.
        """
        
        self.__data_object = obj #remember the object this message is based on

        #get all members of the subclass containing Attribute members that are no relations as a dict.
        #key => member name in the sub class.
        #value => the Attribute inside of this member.
        attributes = {attr:object.__getattribute__(self,attr)
                        for attr in dir(self)
                            if not isinstance(getattr(self,attr), collections.Callable)
                            and type(object.__getattribute__(self,attr)) == Attribute
                            and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == False
                            and object.__getattribute__(self,attr).mapping != None
                            and object.__getattribute__(self,attr).write_only == False
                            and not attr.startswith("__")}

        #for each member containing an Attribute object that is no relations set its value
        #to the value retrieved from the python object as specified in the
        #Attribute mapping and set it to the Attribute objects value.
        for attr in attributes:            
            value = obj #start in the object itself to search for value
            value_path = attributes[attr].mapping.split('.') #get mapping and split by '.', because this indicates a deeper path to get it.
            for path_element in value_path: #go down this path in the python object to find the value
                try: #Did a simple try/except, because hassattr actually calls the member
                    current_value = getattr(value,path_element) #get the next value of current path element.
                    value = current_value() if isinstance(current_value, collections.Callable) else current_value #call the attribute if it is callable otherwise just read value
                except AttributeError:
                    value = None
            
            if value == None: #check if this field is required
                if attributes[attr].required:
                    raise Exception('Missing required field ' + str(attributes[attr].name) + ".")
            else:       
                if isinstance(value,attributes[attr].value_type) == False: #check if actual value fit's value_type
                    raise Exception('Expected ' + str(attributes[attr].value_type) + " got " + str(type(value)) + " for " + str(attributes[attr].name) + " of " + str(self.__type_name) + ".")
            
                if attributes[attr].name == 'id': #if the attributes name is id, set it to the object'S id, because id is not inside "attributes"
                    setattr(self,'id',value)
                else:
                    attributes[attr].value = value #set loaded value to the Attribute object's value.
        
        if include_relationships:          
            #get all members of the subclass containing Attribute members that are relations as a dict.
            #key => member name in the sub class.
            #value => the Attribute inside of this member.
            relations = {attr:object.__getattribute__(self,attr)
                            for attr in dir(self)
                                if not isinstance(getattr(self,attr), collections.Callable)
                                and type(object.__getattribute__(self,attr)) == Attribute
                                and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == True
                                and object.__getattribute__(self,attr).key_mapping != None
                                and object.__getattribute__(self,attr).write_only == False
                                and not attr.startswith("__")}
    
            #for each member containing an Attribute object that is a relations set its value
            #to the value retrieved from the python object as specified in the
            #Attribute mapping and set it to the Attribute objects value.
            for attr in relations:
                #load key first (for relations element)
                key_id = obj
                key_id_path = relations[attr].key_mapping.split('.') #get mapping to the keys of this relations and split by '.', because this indicates a deeper path to get it.
    
                for path_element in key_id_path: #go down this path in the python object to find the value
                    if key_id == None:
                        if relations[attr].required:
                            raise InternalServerErrorException("Keypath: " + str(key_id_path) + " returned None for path element " + path_element + " on message type " + self.__type_name)
                        else:
                            key_id = None
                            continue # skip this not required relationship, because it'S value is None.
                    
                    if hasattr(key_id,path_element):
                        current_key_id = getattr(key_id,path_element) #get the next value of current path element.
                        key_id = current_key_id() if isinstance(current_key_id, collections.Callable) else current_key_id #call the attribute if it is callable otherwise just read value
                    else:
                        if relations[attr].required:
                            raise InternalServerErrorException("Keypath: " + str(key_id_path) + " returned None for path element " + path_element + " on message type " + self.__type_name)
                        else:
                            key_id = None
                            continue # skip this not required relationship, because it'S value is None.
                        
                #now get type name for this relation
                if key_id != None:
                    type_name = relations[attr].value_type.__name__
                    if hasattr(relations[attr].value_type(),'type_name') and relations[attr].value_type().type_name != None: #if sub class has a member "type_name"...
                        type_name = relations[attr].value_type().type_name #get this type name
                        
                    if isinstance(key_id,list): #one-to-many relation
                        relations[attr].key_value = {'data':[]}
                        for k in key_id:
                            relations[attr].key_value['data'].append({'type':type_name,'id':str(k)})
                    else: #one-to-one relation
                        relations[attr].key_value = {'data':{'type':type_name,'id':str(key_id)}}
            
        if hasattr(self,'type_name') and self.type_name != None: #if sub class has a member "type_name"...
            self.__type_name = self.type_name #... override __type_name to set this to 'type' in the final data object.
            
            
        return self

    def get_included(self):
        included = []
        
        #get all members of the subclass containing Attribute members that are relations and have a mapping as a dict.
        #key => member name in the sub class.
        #value => the Attribute inside of this member.
        relations = {attr:object.__getattribute__(self,attr)
                        for attr in dir(self)
                            if not isinstance(getattr(self,attr), collections.Callable)
                            and type(object.__getattribute__(self,attr)) == Attribute
                            and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == True
                            and object.__getattribute__(self,attr).mapping != None
                            and not attr.startswith("__")}

        #for each member containing an Attribute object that is a relations set its value
        #to the value retrieved from the python object as specified in the
        #Attribute mapping and set it to the Attribute objects value.
        for attr in relations:
            #load key first (for relations element)
            value = self.__data_object
            value_path = relations[attr].mapping.split('.') #get mapping to the keys of this relations and split by '.', because this indicates a deeper path to get it.

            for path_element in value_path: #go down this path in the python object to find the value
                if hasattr(value,path_element):
                    current_value = getattr(value,path_element) #get the next value of current path element.
                    value = current_value() if isinstance(current_value, collections.Callable) else current_value #call the attribute if it is callable otherwise just read value
                else:
                    if relations[attr].required:
                        raise InternalServerErrorException("Keypath: " + str(value_path) + " returned None for path element " + path_element + " on message type " + self.__type_name)
                    else:
                        value = None
                        continue # skip this not required relationship, because it'S value is None.
                
                #current_value = getattr(value,path_element) #get the next value of current path element.
                #value = current_value() if callable(current_value) else current_value #call the attribute if it is callable otherwise just read value

            if value == None:
                if relations[attr].required:
                    raise InternalServerErrorException("Keypath: " + str(value_path) + " returned None for path element " + path_element + " on message type " + self.__type_name)
                else:
                    continue # skip this not required relationship, because it'S value is None.
        

            #data = DataMessage.from_object(value,object.__getattribute__(self,attr).value_type,include_relationships=False) #map but without relationships
            data = DataMessage.from_object(value,object.__getattribute__(self,attr).value_type,include_relationships=True) #map now with relationships
            
            if isinstance(data,list) == True:
                for d in data: included.append(d.to_dict())
            else:
                included.append(data.to_dict())
        
        
        return included
        
    @classmethod
    def from_object(cls,obj,msg_class,include_relationships=True):
        """
        Used to get a DataMessage (an object derived from DataMessage) with values in its
        Attribute members loaded from a python object according to Attribute objects mapping.
        obj => the python object containing the data that should be mapped to the message object. If this is a list of objects a list of message objects is returned.
        msg_class => the class (derived from DataMessage) which should be used as message class. (This class will be initialized and returned)
        """
        if isinstance(obj, (list, tuple)):
            messages = []
            for o in obj: #map all objects to new meassage objects
                msg = msg_class()
                msg.map_object(o,include_relationships)
                messages.append(msg)
                
            return messages
        else: #map a single object to a message object.
            msg = msg_class()
            msg.map_object(obj,include_relationships)
            return msg

    ### REQUEST HANDLING ###
    def map_message(self,message):
        """
        Used to set values from a jsonapi request message, as specified in the Attribute objects
        of the sub class of this, to the values of the Attribute objects of the sub class.
        So in other words, this is the data mapping from message to DataMessage object.
        """
        
        #get id
        if 'id' in message:
            self.id = message['id']
            
        if 'attributes' in message:
            #get attributes
            attributes = {attr:object.__getattribute__(self,attr)
                            for attr in dir(self)
                                if not isinstance(getattr(self,attr), collections.Callable)
                                and type(object.__getattribute__(self,attr)) == Attribute
                                and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == False
                                and object.__getattribute__(self,attr).mapping != None
                                and object.__getattribute__(self,attr).name != 'id'
                                and not attr.startswith("__")}
            
            for attr in attributes:
                if attributes[attr].name in message['attributes']:
                    setattr(self,attr,message['attributes'][attributes[attr].name])
                    setattr(attributes[attr],'updated',True) #mark this attribute as updated for later updating the backend object
                else:
                    if attributes[attr].required == True:
                        raise Exception('Missing required field ' + str(attributes[attr].name) + ".")
                    
        if 'relationships' in message:
            #get relationships
            relations = {attr:object.__getattribute__(self,attr)
                            for attr in dir(self)
                                if not isinstance(getattr(self,attr), collections.Callable)
                                and type(object.__getattribute__(self,attr)) == Attribute
                                and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == True
                                and object.__getattribute__(self,attr).key_mapping != None
                                and object.__getattribute__(self,attr).name != 'id'
                                and not attr.startswith("__")}
            
            for attr in relations:
                if relations[attr].name in message['relationships']:
                    rel_objects = []
                    if isinstance(message['relationships'][relations[attr].name]['data'], (list, tuple)):
                        for item in message['relationships'][relations[attr].name]['data']:
                            rel_object = relations[attr].value_type()
                            rel_object.id = item['id']
                            rel_objects.append(rel_object)
                    else:
                        rel_object = relations[attr].value_type()
                        
                        rel_data = message['relationships'][relations[attr].name]['data']
                        
                        #removed releationships result in "None" data part. We use None id to idicate this state internally.
                        if rel_data == None:
                            rel_object.id = None
                        else:
                            rel_object.id = message['relationships'][relations[attr].name]['data']['id']
                        
                        rel_objects = rel_object
                    
                    setattr(self,attr,rel_objects)
                    setattr(relations[attr],'updated',True) #mark this attribute as updated for later updating the backend object
                else:
                    if relations[attr].required == True:
                        raise Exception('Missing required field ' + str(relations[attr].name) + ".")
    
    @classmethod
    def from_message(cls,raw_message,msg_class):
        """
        Used to get a DataMessage (an object derived from DataMessage) with values in its
        Attribute members loaded from a jsonapi request object (raw string request) according to Attribute objects mapping.
        If the jsonapi request object is a list a list of message objects is returned.
        msg_class => the class (derived from DataMessage) which should be used as message class. (This class will be initialized and returned)
        """
        json_message = json.loads(raw_message) #parse raw_message to json
        
        if json_message == None: #no request body
            return None
        
        #get data part
        data = None
        if 'data' in json_message:
            data = json_message['data']
        else:
            raise Exception("Message is missing data.")
        
        if isinstance(data, (list, tuple)):
            messages = []
            for d in data:
                msg = msg_class()
                msg.map_message(d)
                messages.append(msg)

            return messages
        else:
            msg = msg_class()
            msg.map_message(data)
            return msg
        
    def update_object(self,obj,useids=True):
        """
        Used to set values from a DataMessage that were updated (self.__updated == True),
        as specified in the Attribute objects of the sub class of this, to the values of
        the backend object that matches this DataMessage Object.
        So in other words, this is the data mapping from DataMessage to backend object.
        Read-Only Attributes are also skipped.

        If useids==True (default), relations will be replaced by their respective IDs.
        """
        
        attributes = {attr:object.__getattribute__(self,attr)
                        for attr in dir(self)
                            if not isinstance(getattr(self,attr), collections.Callable)
                            and type(object.__getattribute__(self,attr)) == Attribute
                            and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == False
                            and object.__getattribute__(self,attr).updated == True
                            and object.__getattribute__(self,attr).read_only == False
                            and object.__getattribute__(self,attr).mapping != None
                            and object.__getattribute__(self,attr).name != 'id'
                            and not attr.startswith("__")}
        
        
        for attr in attributes:
            attr_obj = obj
            attr_path = attributes[attr].mapping.split('.') #get mapping and split by '.', because this indicates a deeper path to get it.
            actual_attr = None
            i = 1
            for path_element in attr_path: #go down this path in the python object to find the value
                if i < len(attr_path): #go down the path, but exclude the last element to get the parent object of the attribute
                    current_attr_obj = getattr(attr_obj,path_element) #get the next value of current path element.
                    attr_obj = current_attr_obj() if isinstance(current_attr_obj, collections.Callable) else current_attr_obj #call the attribute if it is callable otherwise just read value
                else: #the last element is what we actually want to set
                    actual_attr = path_element
                    
                i = i + 1
                    
            #set value to to the attr i nthe subobject
            setattr(attr_obj, actual_attr, object.__getattribute__(self,attr).value)
            
            
        relations = {attr:object.__getattribute__(self,attr)
                        for attr in dir(self)
                            if not isinstance(getattr(self,attr), collections.Callable)
                            and type(object.__getattribute__(self,attr)) == Attribute
                            and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == True
                            and object.__getattribute__(self,attr).updated == True
                            and object.__getattribute__(self,attr).read_only == False
                            and object.__getattribute__(self,attr).key_mapping != None
                            and not attr.startswith("__")}
        
        
        for attr in relations:
            attr_obj = obj
            attr_path = relations[attr].key_mapping.split('.') #get key_mapping and split by '.', because this indicates a deeper path to get it.
            actual_attr = None
            i = 1
            for path_element in attr_path: #go down this path in the python object to find the value
                if i < len(attr_path): #go down the path, but exclude the last element to get the parent object of the attribute
                    current_attr_obj = getattr(attr_obj,path_element) #get the next value of current path element.
                    attr_obj = current_attr_obj() if isinstance(current_attr_obj, collections.Callable) else current_attr_obj #call the attribute if it is callable otherwise just read value
                else: #the last element is what we actually want to set
                    actual_attr = path_element
                    
                i = i + 1
                           
            #extract ids and set to object            
            if isinstance(object.__getattribute__(self,attr).value,(list,tuple)):
                if useids:
                    vals = [r.id for r in object.__getattribute__(self,attr).value]                
                else:
                    vals = object.__getattribute__(self,attr).value
                setattr(attr_obj, actual_attr, vals)
            else:
                if useids:
                    setattr(attr_obj, actual_attr, object.__getattribute__(self,attr).value.id)
                else:
                    setattr(attr_obj, actual_attr, object.__getattribute__(self,attr).value)
            
        return obj
    
    def describe(self):
        """
        Used to get a description of this message type (Subclass of DataMessage), containing
        all it's attributes and relationships as dict. This can be send in a meta member of
        a JsonApiMessage to describe the service entites to client developers.
        """
        #read type name
        if hasattr(self,'type_name') and self.type_name != None: #if sub class has a member "type_name"...
            self.__type_name = self.type_name #... override __type_name to set this to 'type' in the final data object.
            
        message_description = { "type":self.__type_name }
        
        #initialize attribute and relationship lists
        message_description['attributes'] = []
        message_description['relationships'] = []
        
        #get attributes
        attributes = {attr:object.__getattribute__(self,attr)
                        for attr in dir(self)
                            if not isinstance(getattr(self,attr), collections.Callable)
                            and type(object.__getattribute__(self,attr)) == Attribute
                            and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == False
                            and object.__getattribute__(self,attr).mapping != None
                            and object.__getattribute__(self,attr).name != 'id'
                            and not attr.startswith("__")}
        
        for attr in attributes:
            attr_desription = {
                "name": attributes[attr].name,
                "value-type": type(attributes[attr].value_type()).__name__,
                "is-required": str(attributes[attr].required),
                "is-read-only": str(attributes[attr].read_only),
                "is-write-only": str(attributes[attr].write_only)
            }
            
            message_description['attributes'].append(attr_desription)
            
        #get relationships
        relations = {attr:object.__getattribute__(self,attr)
                        for attr in dir(self)
                            if not isinstance(getattr(self,attr), collections.Callable)
                            and type(object.__getattribute__(self,attr)) == Attribute
                            and issubclass(object.__getattribute__(self,attr).value_type,DataMessage) == True
                            and object.__getattribute__(self,attr).key_mapping != None
                            and object.__getattribute__(self,attr).name != 'id'
                            and not attr.startswith("__")}
        
        for attr in relations:
            #get type name of relation
            rel_object = relations[attr].value_type()
            type_name = type(relations[attr].value_type()).__name__
            if hasattr(rel_object,'type_name') and rel_object.type_name != None: #if sub class has a member "type_name"...
                type_name = rel_object.type_name #... take this one
                
            attr_desription = {
                "name": relations[attr].name,
                "value-type": type_name,
                "is-required": str(relations[attr].required),
                "is-read-only": str(relations[attr].read_only),
                "is-write-only": str(relations[attr].write_only)
            }
            
            message_description['relationships'].append(attr_desription)
            
        return message_description
           
class ErrorMessage(object): #JSON API Error Object see: http://jsonapi.org/format/#errors
    id = None #a unique identifier for this particular occurrence of the problem.
    status = None #the HTTP status code applicable to this problem, expressed as a string value.
    code = None #an application-specific error code, expressed as a string value.
    title = None #a short, human-readable summary of the problem that SHOULD NOT change from occurrence to occurrence of the problem, except for purposes of localization.
    detail = None #a human-readable explanation specific to this occurrence of the problem.
    meta = None #a meta object containing non-standard meta-information about the error.
    traceback = None #excepton traceback

    @classmethod
    def from_exception(cls, exception):
        """
        Used to get a ErrorMessage filled with data based on the data in the given Exception.
        Only of Exception is derived from JanusException all the Data will be filled in with.
        All Exceptions that does not derive from Janus Exception will result in a 503 Internal Server Error.
        exception => an Exception
        """
        msg = cls()
        if isinstance(exception,JanusException):
            msg.id = exception.id
            msg.status = exception.status
            msg.code = exception.code
            msg.title = exception.title
            msg.detail = exception.detail
            msg.meta = exception.meta
        else:
            msg.id = hashlib.sha1(str(time.time()) + str(exception)).hexdigest()
            msg.status = 500
            msg.code = 500 #TODO add code for uncaught exception
            msg.title = "Internal Server Error"
            msg.detail = str(exception)
            msg.meta = None

        return msg

    def to_dict(self):
        """
        Returns a dict representation of this objects's members containing Attribute
        objects, with their configured name as key and their values.
        The dict is already in a jsonapi format.
        """

        msg = {
            'id': self.id,
            'status':self.status,
            'code':self.code,
            'title':self.title,
            'detail':self.detail
        }

        if self.meta != None:
            msg['meta'] = self.meta

        if self.traceback != None:
            if self.meta == None: self.meta = {}
            msg['meta']['traceback'] = self.traceback

        return msg
