"""
CrudMixin - Mixing for Django models to implement CRUD functionality

Copyright (c) Stefan LOESCH, oditorium 2016. All rights reserved.
Licensed under the Mozilla Public License, v. 2.0 <https://mozilla.org/MPL/2.0/>
"""
__version__="1.2"
__version_dt__="2016-04-25"

from django.http import JsonResponse
from django.core.signing import Signer, BadSignature
from django.views.decorators.csrf import csrf_exempt

import json
#import copy
import inspect
    # http://stackoverflow.com/questions/395735/python-how-to-check-whether-a-variable-is-a-class-or-not


################################################################################
## ERROR / SUCCESS
def _error(msg, status=None):
    if status == None: status = 404
    return JsonResponse({'success': False, 'errmsg': msg}, status=status)

def _success(data, status=None):
    if status == None: status = 200
    data['success'] = True
    return JsonResponse(data, status=status)


################################################################################
## EXCEPTIONS
class TokenSignatureError(RuntimeError): pass       # the token signature is invalid
class TokenFormatError(RuntimeError): pass          # the token format is invalid
class TokenContentError(RuntimeError): pass         # the token content is invalid
class TokenDefinitionError(RuntimeError): pass      # bad parameters when defining a token
class TokenPermissionError(RuntimeError): pass      # tried to access unpermissioned resource
class ParamsError(RuntimeError): pass               # json decode of params failed
class DoesNotExistError(RuntimeError): pass         # the item does not exist


##############################################################################################
## TOKEN
class Token():
    """
    allows definition of highly granular tokens, eg for a JSON/CRUD Api
    """
    def __init__(s, token):
        try: token = Signer(sep=s.separators, salt=s.salt).unsign(token)
        except BadSignature: raise TokenSignatureError(token)
        s.token = token.split(s.separator)
        if len(s.token) != 4: raise TokenFormatError("Invalid token format [1]")
        if s.token[2] != "ALLOW": raise TokenFormatError("Invalid token format [2]")
        s.fields = s.token[3].split(s.separator2)
    
    separators=":::"
    separator="::"
    separator2=":"
    salt="token"
    
    
    @classmethod
    def create(cls, namespace, command, fields=None, negative_fields=False):
        """
        create a token
        
        PARAMETERS
        - ns: the token namespace (string, minimum 2 characters)
        - command: the token command (can be a string, or a list of strings if it uses parameters)
        - fields: list o fields that this token is allowed (or forbidden, see below) to access
        - negative_fields: if True, all but the listed fields are free to access
        """
        if negative_fields: raise NotImplementedError()
        if len(namespace) < 2: raise TokenDefinitionError("namespace minimum 2 characters")
        if fields == None: fields = []
        if not isinstance(command, str): command = cls.separator2.join(command)
        if not isinstance(fields, str): fields = cls.separator2.join(fields)
        token = cls.separator.join([namespace, command, "ALLOW", fields])
        return Signer(sep=cls.separators, salt=cls.salt).sign(token)
        
        
    def allowed(s, field):
        """
        whether or not the field is allow by this token
        """
        return field in s.fields
    
    @property
    def namespace(s):
        """
        the token namespace
        """
        return s.token[0]
        
    @property
    def command(s):
        """
        the token command (without paramters)
        """
        return s.token[1].split(s.separator2)[0]
        
    @property
    def parameters(s):
        """
        the token command parameters (as list)
        """
        return s.token[1].split(s.separator2)[1:]
        
    @property
    def numparameters(s):
        """
        the number of token parameters
        """ 
        return len(s.parameters)
    
##############################################################################################
## CRUD MIXIN
class CrudMixin():
    """
    CRUD methods for Django models
    
    DEFINES
    - `byid`: gets element by id, None if does not exist
    - `crud_read`: read multiple fields at once
    - `crud_update`: update multiple fields at once
    - `crud_create`: a convenience method for `crud_update`, create an element
    - `crud_duplicate`: duplicate an element
    - `crud_delete`: delete an element
    
    NOTE
        tests are in Presmo's ImageDB.tests_crudmixin
    """
    
    ########################################
    ## BY ID
    @classmethod
    def byid(cls, id):
        """
        returns an element by id (or None if does not exist)
        
        EXAMPLE
            class MyModel(ModelToolsMixin, models.Model)
                ...
        
            obj = MyModel.byid(id)
        """
        try: return cls.objects.get(id=id)
        except: return None

    ########################################
    ## CRUD READ
    def crud_read(s, fields, id=None):
        """
        read multiple data fields of a model at once (returns as dict)
        
        NOTES
        - the primary key field `id` is always added
        - fields would usually be a list, but it can also be a dict or a string (dicts and strings converted to lists)
        - if a field is requested that does not exist an error is raised
        - if None is passed in a `s` (when called as classmethod) None is returned
        
        EXAMPLE
            class MyModel(ModelToolsMixin, models.Model)
                ...
            
            obj = MyModel.byid(id)
            obj.read_fields(['first', 'last'])  # {'id': -id-, 'first': -first-, 'last': -last-}
            obj.read_fields({'id':-nr-, 'first':-nr-, 'last':-nr-})  # {'id': -id-, 'first': -first-, 'last': -last-}
            obj.read_fields('first')  # {'id': -id-, 'first': -first-}
            
            MyModel.read_fields(MyModel.byid(id), ['first', 'last']) # {'id': -id-, 'first': -first-, 'last': -last-}
            
        """
        if inspect.isclass(s):
            if id==None: raise RuntimeError("When called as a classmethod, the `id` field must not be None")
            else: s = s.byid(id)
        if s == None: return None
        if isinstance(fields, dict): fields = fields.keys
        if isinstance(fields, str): fields = [fields]
        if not 'id' in fields: fields += ['id']
        return {f:getattr(s, f) for f in fields}


    ########################################
    ## CRUD UPDATE   
    def crud_update(s, do_not_save_object=False, **kwargs):
        """
        update multiple data fields of a model at once (returns updated object)

        NOTES
        - if an unknown field is passed in this is a runtime error
        - if called as a classmethod, then the record with this id is updated (id == None or does not exist: new)
        """
        if inspect.isclass(s):
            # if called as a classmethod: new object on id=None, otherwise get object id 
            if not 'id' in kwargs: raise RuntimeError("When called as a classmethod, the `id` field must be present")
            if kwargs['id'] == None: s = s() # s is initially a class, then a fresh instance
            else: s = s.byid(kwargs['id'])
        for field in kwargs:
            if hasattr(s, field): setattr(s, field, kwargs[field])
            else: raise RuntimeError("unkwown attribute: {}".format(field))
        if not do_not_save_object: s.save()
        return s


    ########################################
    ## CRUD CREATE
    @classmethod
    def crud_create(cls, **kwargs):
        """
        creates a new object in the database
        
        NOTES
        - this is a convenience method for `update_fields`
        """
        kwargs['id'] = None
        return cls.crud_update(cls, **kwargs)


    ########################################
    ## CRUD DUPLICATE
    @classmethod
    def crud_duplicate(cls, id, do_not_save_object=False, **kwargs):
        """
        duplicate an existing object (possibly changing some fields)
        """

        try: new = cls.objects.get(id=id)
        except: raise DoesNotExistError("object with id={} does not exist".format(id))
        new.id = None
        for field in kwargs:
            if hasattr(new, field): setattr(new, field, kwargs[field])
            else: raise RuntimeError("unkwown attribute: {}".format(field))
        if not do_not_save_object: 
            new.save()
            print ("SAVING ({0.id})".format(new))
        return new


    ########################################
    ## CRUD DELETE
    @classmethod
    def crud_delete(cls, ids):
        """
        deletes an object (or a list of objects) in the database
        """
        if isinstance(ids, int): ids=[ids]
        for id in ids:
            try: record = cls.objects.get(id=id)
            except: continue
            record.delete()
        return

    ########################################
    ## CRUD TOKEN XXX
    @classmethod
    def _crud_token(cls, command, fields=None):
        """
        generic token generation
        """
        return Token.create(cls.__name__, command, fields)
        
    @classmethod
    def crud_token_create_cm(cls, fields):
        """
        creates a token to allow creating an element
        """
        return cls._crud_token("create", fields)
        
    def crud_token_read(s, fields):
        """
        creates a token to allow reading fields of the current element
        """
        return s.crud_token_read_cm(s.id, fields)

    @classmethod
    def crud_token_read_cm(cls, id, fields):
        """
        creates a token to allow reading fields of the element `id`
        """
        return cls._crud_token(["read", str(id)], fields)
        
    def crud_token_update(s, fields):
        """
        creates a token to allow updating fields of the current element
        """
        return s.crud_token_update_cm(s.id, fields)

    @classmethod
    def crud_token_update_cm(cls, id, fields):
        """
        creates a token to allow updating fields of the element `id`
        """
        return cls._crud_token(["update", str(id)], fields)     
  
    def crud_token_delete(s):
        """
        creates a token to allow deleting the current element
        """
        return s.crud_token_delete_cm(s.id)

    @classmethod
    def crud_token_delete_cm(cls, id):
        """
        creates a token to allow deleting the element `id`
        """
        return cls._crud_token(["delete", str(id)])

    def crud_token_duplicate(s, fields):
        """
        creates a token to allow duplicating the current element and updating its fields 
        """
        return s.crud_token_duplicate_cm(s.id, fields)

    @classmethod
    def crud_token_duplicate_cm(cls, id, fields):
        """
        creates a token to allow duplicating the element `id` and updating its fields 
        """
        return cls._crud_token(["duplicate", str(id)], fields)

    @classmethod
    def crud_token_combined_cm(cls, ids, fields_read, fields_write_if_different=None, 
                        create=False, read=True, update=True, duplicate=True, delete=True):
        """
        creates a set of tokens
        """
        tokens = {'create': None, 'read': None, 'update': None, 'duplicate': None, 'delete': None}
        if isinstance(ids, int): ids = [ids]
        fields_write = fields_write_if_different if fields_write_if_different != None else fields_read
        if create: tokens['create'] = cls.crud_token_create_cm(fields_write)
        if read: tokens['read'] = {id: cls.crud_token_read_cm(id, fields_read) for id in ids}
        if update: tokens['update'] = {id: cls.crud_token_update_cm(id, fields_write) for id in ids}
        if duplicate: tokens['duplicate'] = {id: cls.crud_token_duplicate_cm(id, fields_write) for id in ids}
        if delete: tokens['delete'] = {id: cls.crud_token_delete_cm(id) for id in ids}
        return tokens


    ########################################
    ## CRUD TOKEN EXECUTE
    @classmethod
    def crud_token_execute(cls, token, params=None):
        """
        execute a token command (create, read, update, delete)

        COMMANDS
        - create: create a new record (returns its id)
        - read: read the fields from a record (plus id)
        - update: update the fields in the record (returns read)
        - delete: delete the record
        - duplicate: create a new record and updates it (returns read)

        PARAMETERS
        - token: the CRUD token, specifying permissions and command
        - params: the command parameters (dict for create, update, duplicate; 
            list for read; nothing for delete)
        """
        t = Token(token)
        if t.namespace != cls.__name__: 
            raise TokenContentError("using {} token for a {} object".format(t.namespace, cls.__name__))
        if isinstance(params, bytes): params = params.decode()
        if isinstance(params, str): 
            try: params = json.loads(params)
            except: raise ParamsError(params) 
        
        # create
        if t.command == "create":
            if params == None: params = {}
            for field in params:
                if not t.allowed(field): raise TokenPermissionError("Field `{}` not allowed by token".format(field))
            record = cls.crud_create(**params)
            return record.crud_read([])
        
        # read
        elif t.command == "read":
            if params == None: return {'id': int(t.parameters[0])}
            for field in params:
                if not t.allowed(field): raise TokenPermissionError("Field `{}` not allowed by token".format(field))
            record = cls.byid( int(t.parameters[0]) )
            if record == None: raise DoesNotExistError("object with id={} does not exist".format(int(t.parameters[0])))
            return record.crud_read(params)

        # update
        elif t.command == "update":
            if params == None: params = {}
            for field in params:
                if not t.allowed(field): raise TokenPermissionError("Field `{}` not allowed by token".format(field))
            record = cls.byid( int(t.parameters[0]) )
            if record == None: raise DoesNotExistError("object with id={} does not exist".format(int(t.parameters[0])))
            record.crud_update(**params)
            return record.crud_read( list(params.keys()) )

        # delete
        elif t.command == "delete":
            record = cls.byid( int(t.parameters[0]) )
            if record == None: raise DoesNotExistError("object with id={} does not exist".format(int(t.parameters[0])))
            record.crud_delete(record.id)
            return {}

        # duplicate
        elif t.command == "duplicate":
            if params == None: params = {}
            for field in params:
                if not t.allowed(field): raise TokenPermissionError("Field `{}` not allowed by token".format(field))
            record = cls.crud_duplicate(int(t.parameters[0]), **params)
            return record.crud_read( list(params.keys()) )

        # error
        else:
            raise TokenFormatError("Unknown command {}".format(t.command))
            

    ########################################
    ## CRUD AS VIEW
    @classmethod
    def crud_as_view(cls):
        """
        returns a CRUD API view function that can be used directly in an `urls.py` file

        NOTE:
        - the view function expects POST for all requests, even those that are only reading data
        - the data has to be transmitted in json, not URL encoded
        - the response is json; fields are the same as with `crud_token_execute` plus a `success`
            field (true or false), and an `errmsg` field in case of non success
    
        PARAMETERS:
        - token: the CRUD token that (mostly) determines the request
        - params: the command parameters (dict for create, update, and duplicate tokens; 
            list for read token; nothing for delete token)
        """
        @csrf_exempt
        def view(request):
            if request.method != "POST": return _error("request must be POST")
            try: data = json.loads(request.body.decode())
            except: return _error('could not json-decode request body [{}]'.format(request.body.decode()))
            try: token = data['token']
            except: return _error('missing token')
            params = data['params'] if 'params' in data else None
            try: result = cls.crud_token_execute(token, params)
            except TokenSignatureError as e: return _error('token signature error [{}]'.format(str(e)))
            except TokenFormatError as e: return _error('token format error [{}]'.format(str(e)))
            except TokenPermissionError as e: return _error('token permission error [{}]'.format(str(e)))
            except ParamsError as e: return _error('parameter error [{}]'.format(str(e)))
            except DoesNotExistError as e: return _error('item does not exist [{}]'.format(str(e)))
            except Exception as e: return _error('error executing token [{}::{}]'.format(type(e), str(e)))
            return _success(result)
    
        return view
                
