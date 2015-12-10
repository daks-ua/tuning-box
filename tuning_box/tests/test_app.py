# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json

from flask import testing
from werkzeug import wrappers

from tuning_box import app
from tuning_box import db
from tuning_box.tests import base


class JSONResponse(wrappers.BaseResponse):
    @property
    def json(self):
        return json.loads(self.data.decode(self.charset))


class TestApp(base.TestCase):
    def setUp(self):
        super(TestApp, self).setUp()
        self.app = app.build_app()
        self.app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///'
        with self.app.app_context():
            db.db.create_all()
        self.client = testing.FlaskClient(self.app,
                                          response_wrapper=JSONResponse)

    def test_get_namespaces_empty(self):
        res = self.client.get('/namespaces')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, [])

    def test_get_namespaces(self):
        with self.app.app_context():
            namespace = db.Namespace(id=3, name='nsname')
            db.db.session.add(namespace)
            db.db.session.commit()
        res = self.client.get('/namespaces')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, [{'id': 3, 'name': 'nsname'}])

    def test_get_one_namespace(self):
        with self.app.app_context():
            namespace = db.Namespace(id=3, name='nsname')
            db.db.session.add(namespace)
            db.db.session.commit()
        res = self.client.get('/namespaces/3')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {'id': 3, 'name': 'nsname'})

    def test_get_one_namespace_404(self):
        res = self.client.get('/namespaces/3')
        self.assertEqual(res.status_code, 404)