# django-crudmixin
_a mixin for Django models implementing CRUD and CRUD API functionality_

## Installation

This library has been tested with `Python 3.4` and `Python 3.5` and `Django 1.9.2`. Other versions
might work, albeit not Python 2.

## Usage

If a model is defined as follows

	from django.db import models
	from crudmixin import CrudMixin
	
	class MyModel(CrudMixin, models.Model):
		mycharfield = model.CharField(...)
		myintfield = model.IntegerField(...)
		...

then the following functions are defining as simple CRUD API for this model

	record = MyModel.crud_create(mycharfield='mytext', myintfield=100)
	record.crud_update(myintfield=200)
	record.crud_read(['myintfield'])
	record.crud_duplicate(myintfield=200)
	MyModel.crud_delete(record.id)

Moreover, the following functions allow to easily expose a CRUD API via Django views.
Firstly, those function create tokens for certain operations (those with `_cm` suffix
are classmethods)

- `crud_token_create_cm`: token to create a record
- `crud_token_read`, `crud_token_read_cm`: token to read data for one specific record
- `crud_token_update`, `crud_token_update_cm`: token to update one specific record
- `crud_token_delete`, `crud_token_delete_cm`: token to delete one specific record
- `crud_token_duplicate`, `crud_token_duplicate_cm`: token to duplicate one specific record
- `crud_token_combined_cm`: combined-permissions token

Those tokens are then _executed_ using the `crud_token_execute` function. More often however
the `crud_as_view` function will be used, which--like Django's class-based-views--returns
a view when called. A sample `url.py` would look as follows:

	from django.conf.urls import url
	from .models import MyModel

	urlpatterns = [
	    url(r'^crud/mymodel$', MyModel.crud_as_view(), name='crud_mymodel'), 
	    ...
	]

## Contributions
Contributions welcome. Send us a pull request!

## Change Log
The idea is to use [semantic versioning](http://semver.org/), even though initially we might make some minor
API changes without bumping the major version number. Be warned!

- **v1.2** initial version in this repo (added CRUD API code)
- **v1.0** initial version 