Changelog for django-nece
=========================

0.12. (2022-08-22)
-----------------

- Remove admin and dependency of ``django-admin-json-editor``. Reason was
  simple, breaks the css and for what it is, it's useless.
- Make `values` and `values_list` to work (replace the original field with the
  translation)
- Deprecated python2 code
- Add tox.ini so you can run tests for different python / django combos
- Integration with Django i18n framework to detect the language and apply it to
  `language` method.
- Add ``NeceMiddleware``, now with a special header `X-NECE-LANGUAGE` you can
  request translations as long as the language is on the available languages
  setting.


0.11 (2021-05-10)
-----------------

- Drop support of Python 2.7, 3.4 & 3.5
- Drop support of Django 1.9, 1.10, 1.11, 2.0 & 2.1
- Add support for Django 3.1 & 3.2


0.10 (2021-01-15)
-----------------

- Add ``admin`` extra to automatically install ``django-admin-json-editor``

*Note:*

    * Python 2.7, 3.4 & 3.5 support will be dropped in next minor version.
    * Django 1.9, 1.10, 1.11, 2.0 & 2.1 support will be dropped in next minor version.

0.9.0 (2021-01-14)
------------------

- Changed name from ``nece`` to ``django-nece``


0.8.0
-----

- Language fallback support
- Installation error on Windows
- Requirements fixes

0.7.0
-----

- Django 1.11 and Python 3.6 support

0.6.0
-----

- Django 1.8 support dropped

0.5.4
-----

- `translatable_fields` must now be defined in meta class
