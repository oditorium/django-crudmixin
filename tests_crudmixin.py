"""
tests for ModelToolsMixin

(c) Stefan LOESCH, oditorium 2016. All Rights Reserved.
Licensed under the Mozilla Public License, v. 2.0 <https://mozilla.org/MPL/2.0/>
"""
from django.test import TestCase, RequestFactory
from django.conf import settings
from django.core.signing import Signer, BadSignature
#from django.contrib.auth.models import User
#from django.core.urlresolvers import reverse_lazy, reverse
#from Presmo.tools import ignore_failing_tests, ignore_long_tests
#from Presmo.tools import ModelToolsMixin

import json

from .models import *

from .crudmixin import Token, TokenSignatureError, TokenFormatError, TokenDefinitionError, TokenPermissionError

#########################################################################################
## TOKEN TEST
class TokenTest(TestCase):
    """test the Token helper class"""
    
    def test_create(s):
        """test token creation"""
        token = Token.create("myns", "mycmd", ["f1", "f2", "f3"])
        s.assertEqual(token[:31], "myns::mycmd::ALLOW::f1:f2:f3:::")
        token = Token.create("myns", ["acmd","1","2"], "f0")
        s.assertEqual(token[:28], "myns::acmd:1:2::ALLOW::f0:::")
        token = Token.create("myns", "mycmd")
        s.assertEqual(token[:23], "myns::mycmd::ALLOW:::::")
        with s.assertRaises(NotImplementedError): Token.create("myns", "mycmd", "1", True)
        with s.assertRaises(RuntimeError): Token.create("m", "mycmd", "1")

    def test_init(s):
        """test initialisation of Token objects creation"""
        token = Token.create("myns", "mycmd", ["f1", "f2", "f3"])
        with s.assertRaises(TokenSignatureError): Token(token[:-1])
        s.assertEqual(Token(token).namespace, "myns")
        s.assertEqual(Token(token).command, "mycmd")
        s.assertEqual(Token(token).parameters, [])
        s.assertEqual(Token(token).numparameters, 0)
        token = Token.create("myns", ["mycmd","1","2"], ["f1", "f2", "f3"])
        s.assertEqual(Token(token).parameters, ["1", "2"])
        s.assertEqual(Token(token).numparameters, 2)

    def test_fields(s):
        token = Token.create("myns", "mycmd", ["f1", "f2", "f3"])
        s.assertEqual(Token(token).allowed("f1"), True)
        s.assertEqual(Token(token).allowed("x"), False)

        
#########################################################################################
## CRUD MIXIN TEST
from .models import Presentation as Model 
    # any model will do to test the model mixin

class CrudMixinTest(TestCase):
    """test the CrudMixin"""
    
    def setUp(s):
        pass
            
    def test_byid(s):
        """test .byid method"""
        m = Model()
        m.save()
        id1 = m.id
        m2 = Model.byid(id1)
        s.assertEqual(m,m2) 

    def test_crud_create(s):
        """test .crud_create method"""
        p = Model.crud_create(title='Presentation1')
        s.assertEqual(p.title,'Presentation1')
        s.assertTrue(p.id != None)
        p.delete()

    def test_crud_read(s):
        """test .crud_read method"""
        p = Model.crud_create(title='Presentation1')
        response = p.crud_read(['title'])
        s.assertEqual(response['title'], 'Presentation1')
        response2 = Model.crud_read(Model, ['title'], id=p.id)
        s.assertEqual(response, response2)
        p.delete()
        
    def test_crud_update(s):
        """test .crud_update method"""
        p = Model.crud_create(title='Presentation1')
        s.assertEqual(p.title, 'Presentation1')
        p.crud_update(title = 'Presentation2')
        s.assertEqual(p.title, 'Presentation2')
        p.delete()

    def test_crud_read_update(s):
        """test .crud_update method"""
        p = Model.crud_create(title='Presentation1')
        response = p.crud_read(['title'])
        response['title'] = 'Presentation2'
        p.crud_update(**response)
        s.assertEqual(p.title, 'Presentation2')
        p.delete()

    def test_crud_duplicate(s):
        """test .crud_duplicate method"""
        p = Model.crud_create(title='Presentation1')
        pid = p.id
        p2 = Model.crud_duplicate(pid)
        s.assertEqual(p2.title, 'Presentation1')
        s.assertTrue(p2.id != None)
        s.assertTrue(pid != p2.id)
        #p3 = Model.crud_duplicate(Model, id=p.id)
        #s.assertEqual(p3.title, 'Presentation1')
        #s.assertTrue(p3.id != None)
        #s.assertTrue(p.id != p3.id)
        p.delete()
        p2.delete()
        #p3.delete()
        
    def test_crud_delete(s):
        """test .crud_delete method"""
        p = Model.crud_create(title='Presentation1')
        pid = p.id
        s.assertTrue( len(Model.objects.filter(id=pid)) > 0 )
        Model.crud_delete(pid)
        s.assertEqual(len(Model.objects.filter(id=pid)), 0)

        pid = Model.crud_create(title='xyz').id
        pid2 = Model.crud_create(title='xyz').id
        s.assertEqual( len(Model.objects.filter(title='xyz')), 2 )
        Model.crud_delete([pid, pid2])
        s.assertEqual( len(Model.objects.filter(title='xyz')), 0 )

    def test_crud_token(s):
        """test the various crud token generation methods"""
        p = Model.crud_create(title='Presentation1')
        s.assertEqual(Model.crud_token_create_cm(['title', 'comment'])[:45], "Presentation::create::ALLOW::title:comment:::")
        s.assertEqual(p.crud_token_read('title')[:37], "Presentation::read:{0.id}::ALLOW::title:::".format(p))
        s.assertEqual(p.crud_token_update('title')[:39], "Presentation::update:{0.id}::ALLOW::title:::".format(p))
        s.assertEqual(p.crud_token_delete()[:34], "Presentation::delete:{0.id}::ALLOW:::::".format(p))
        s.assertEqual(p.crud_token_duplicate('title')[:42], "Presentation::duplicate:{0.id}::ALLOW::title:::".format(p))

    def test_crud_token_combined(s):
        """test the combined crud token generation method"""

        tokens = Model.crud_token_combined_cm(1, ['read'], ['write'])
        s.assertEqual(tokens['create'], None)
        s.assertEqual(tokens['read'][1], Model.crud_token_read_cm(1, ['read']))
        s.assertEqual(tokens['update'][1], Model.crud_token_update_cm(1, ['write']))
        s.assertEqual(tokens['duplicate'][1], Model.crud_token_duplicate_cm(1, ['write']))
        s.assertEqual(tokens['delete'][1], Model.crud_token_delete_cm(1))

        tokens = Model.crud_token_combined_cm([1,3], ['rw'], create=True, update=False)
        s.assertEqual(tokens['create'], Model.crud_token_create_cm(['rw']))
        s.assertEqual(tokens['read'][3], Model.crud_token_read_cm(3, ['rw']))
        s.assertEqual(tokens['update'], None)
        s.assertEqual(tokens['duplicate'][3], Model.crud_token_duplicate_cm(3, ['rw']))
        s.assertEqual(tokens['delete'][3], Model.crud_token_delete_cm(3))

    def test_crud_execute(s):
        """test the various crud execution"""

        # CREATE
        token = Model.crud_token_create_cm("title")
        result = Model.crud_token_execute(token, {'title': 'présentation1'})
        pid = result['id']
        p = Model.objects.get(id=pid)
        s.assertEqual(p.title, 'présentation1')
        
        result = Model.crud_token_execute(token, json.dumps({'title': 'présentation2'}))
        p2 = Model.objects.get(id=result['id'])
        s.assertEqual(p2.title, 'présentation2')
        p2.delete()

        result = Model.crud_token_execute(token, json.dumps({'title': 'présentation3'}).encode('utf-8'))
        p3 = Model.objects.get(id=result['id'])
        s.assertEqual(p3.title, 'présentation3')
        p3.delete()

        with s.assertRaises(TokenPermissionError): Model.crud_token_execute(token, {'comment': 'comment1'})

        
        # READ
        token = p.crud_token_read('title')
        s.assertEqual(token, Model.crud_token_read_cm(p.id, 'title'))
        result = Model.crud_token_execute(token, ['title'])
        s.assertEqual(result['title'], 'présentation1')
        s.assertEqual(result['id'], pid)

        with s.assertRaises(TokenPermissionError): Model.crud_token_execute(token, ['comment'])
        
        
        # UPDATE
        token = p.crud_token_update('title')
        s.assertEqual(token, Model.crud_token_update_cm(p.id, 'title'))
        result = Model.crud_token_execute(token, {'title': 'présentation1a'})
        pid2 = result['id']
        s.assertTrue(pid2 == pid)
        p2 = Model.objects.get(id=pid2)
        s.assertEqual(p2.title, 'présentation1a')
        s.assertEqual(result['title'], 'présentation1a')

        with s.assertRaises(TokenPermissionError): Model.crud_token_execute(token, {'comment': 'comment1'})
  
        # DUPLICATE
        token = p.crud_token_duplicate('comment')
        s.assertEqual(token, Model.crud_token_duplicate_cm(p.id, 'comment'))
        result = Model.crud_token_execute(token, {'comment': 'crud_token'})
        dpid = result['id']
        #s.assertTrue(dpid != pid)
        s.assertEqual(result['comment'], 'crud_token')
        p2 = Model.objects.get(id=pid)
        s.assertEqual(p2.title, 'présentation1a')
        s.assertEqual(p2.comment, '')
        pd = Model.objects.get(id=dpid)
        s.assertEqual(pd.title, 'présentation1a')
        s.assertEqual(pd.comment, 'crud_token')
        pd.delete()
        
        
        # DELETE
        s.assertEqual( len(Model.objects.filter(id=pid)), 1 )
        token = p.crud_token_delete()
        s.assertEqual(token, Model.crud_token_delete_cm(p.id))
        Model.crud_token_execute(token)
        s.assertEqual( len(Model.objects.filter(id=pid)), 0 )
        

    def _api(s, data):
        return RequestFactory().post('/path/to/api', content_type='application/json', data=json.dumps(data))
        
    def test_crud_as_view(s):
        
        view = Model.crud_as_view()
        f = RequestFactory()
        
        # GET
        data = json.loads( view( f.get('/path/to/api') ).content.decode()  )
        s.assertEqual(data['success'],False)
        s.assertEqual(data['errmsg'], "request must be POST")

        # POST no json
        data = json.loads( view( f.post('/path/to/api', {'a':1,'b':2} ) ).content.decode()  )
        s.assertEqual(data['errmsg'][:34], "could not json-decode request body")


        # POST json, but wrong data
        data = json.loads( view( f.post('/path/to/api', content_type='application/json', data="123") ).content.decode()  )
        s.assertEqual(data['errmsg'][:14], "missing token")

        data = json.loads( view( s._api({'a':1,'b':2}) ).content.decode()  )
        s.assertEqual(data['errmsg'][:14], "missing token")

        # POST bad token signature
        data = json.loads( view( s._api({'token':'123::456'}) ).content.decode()  )
        s.assertEqual(data['errmsg'][:21], "token signature error")

        # CREATE permission error
        token = Model.crud_token_create_cm(['title'])
        data = json.loads( view( s._api({'token':token, 'params':{'comment':'c'}}) ).content.decode()  )
        s.assertEqual(data['errmsg'][:22], "token permission error")

        # CREATE
        data = json.loads( view( s._api({'token':token, 'params':{'title':'test_crud_as_view'}}) ).content.decode()  )
        s.assertEqual(data['success'], True)
        pid = data['id']
        p = Model.objects.get(id=pid)
        s.assertEqual(p.title, 'test_crud_as_view')

        # READ permission error
        token = p.crud_token_read(['title'])
        data = json.loads( view( s._api({'token':token, 'params':['title', 'comment']}) ).content.decode()  )
        s.assertEqual(data['errmsg'][:22], "token permission error")
        
        # READ
        token = p.crud_token_read(['title', 'comment'])
        data = json.loads( view( s._api({'token':token, 'params':['title', 'comment']}) ).content.decode()  )
        s.assertEqual(data['success'], True)
        s.assertEqual(data['title'], 'test_crud_as_view')

        # UPDATE permission error
        token = p.crud_token_update(['title'])
        data = json.loads( view( s._api({'token':token, 'params':{'comment':'test_crud_as_view'}}) ).content.decode()  )
        s.assertEqual(data['errmsg'][:22], "token permission error")
        
        # UPDATE
        token = p.crud_token_update(['title'])
        data = json.loads( view( s._api({'token':token, 'params':{'title':'test_crud_as_view1'}}) ).content.decode()  )
        s.assertEqual(data['success'], True)
        s.assertEqual(data['title'], 'test_crud_as_view1')
        p = Model.objects.get(id=pid)
        s.assertEqual(p.title, 'test_crud_as_view1')

        # DUPLICATE permission error
        token = p.crud_token_duplicate(['title'])
        data = json.loads( view( s._api({'token':token, 'params':{'content':'test_crud_as_view'}}) ).content.decode()  )
        s.assertEqual(data['errmsg'][:22], "token permission error")

        # DUPLICATE
        token = p.crud_token_duplicate(['title'])
        data = json.loads( view( s._api({'token':token, 'params':{'title':'test_crud_as_view2'}}) ).content.decode()  )
        s.assertEqual(data['success'], True)
        s.assertEqual(data['title'], 'test_crud_as_view2')
        pid2 = data['id']
        p2 = Model.objects.get(id=pid2)
        s.assertEqual(p2.title, 'test_crud_as_view2')
        s.assertTrue(pid != pid2)

        # DELETE
        token = p.crud_token_delete()
        data = json.loads( view( s._api({'token':token}) ).content.decode()  )
        s.assertEqual(data['success'], True)
        token = p2.crud_token_delete()
        data = json.loads( view( s._api({'token':token}) ).content.decode()  )
        s.assertEqual(data['success'], True)
        with s.assertRaises(Model.DoesNotExist): Model.objects.get(id=pid)
        with s.assertRaises(Model.DoesNotExist): Model.objects.get(id=pid2)
        
        
        
        
        
        
        
        

        
        

    
