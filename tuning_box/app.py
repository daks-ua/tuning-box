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

import flask
import flask_restful
from flask_restful import fields

from tuning_box import db

api = flask_restful.Api()

namespace_fields = {
    'id': fields.Integer,
    'name': fields.String,
}


@api.resource('/namespaces', '/namespaces/<int:namespace_id>')
class Namespace(flask_restful.Resource):
    @flask_restful.marshal_with(namespace_fields)
    def get(self, namespace_id=None):
        if namespace_id is None:
            return db.Namespace.query.all()
        else:
            return db.Namespace.query.get_or_404(namespace_id)

    @flask_restful.marshal_with(namespace_fields)
    def post(self):
        namespace = db.Namespace(name=flask.request.json['name'])
        db.db.session.add(namespace)
        db.db.session.commit()
        return namespace, 201

    @flask_restful.marshal_with(namespace_fields)
    def put(self, namespace_id):
        namespace = db.Namespace.query.get_or_404(namespace_id)
        namespace.name = flask.request.json['name']
        db.db.session.commit()
        return namespace, 201

    def delete(self, namespace_id):
        namespace = db.Namespace.query.get_or_404(namespace_id)
        db.db.session.delete(namespace)
        db.db.session.commit()
        return None, 204

schema_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'component_id': fields.Integer,
    'namespace_id': fields.Integer,
    'content': fields.String,
}

template_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'component_id': fields.Integer,
    'content': fields.String,
}

component_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'schemas': fields.List(fields.Nested(schema_fields)),
    'templates': fields.List(fields.Nested(template_fields)),
}


@api.resource('/components', '/components/<int:component_id>')
class Component(flask_restful.Resource):
    @flask_restful.marshal_with(component_fields)
    def get(self, component_id=None):
        if component_id is None:
            return db.Component.query.all()
        else:
            return db.Component.query.get_or_404(component_id)

    @flask_restful.marshal_with(component_fields)
    def post(self):
        component = db.Component(name=flask.request.json['name'])
        component.schemas = []
        for schema_data in flask.request.json.get('schemas'):
            schema = db.Schema(name=schema_data['name'],
                               namespace_id=schema_data['namespace_id'],
                               content=schema_data['content'])
            component.schemas.append(schema)
        component.templates = []
        for template_data in flask.request.json.get('templates'):
            template = db.Template(name=template_data['name'],
                                   content=template_data['content'])
            component.templates.append(template)
        db.db.session.add(component)
        db.db.session.commit()
        return component, 201

    def delete(self, component_id):
        component = db.Component.query.get_or_404(component_id)
        db.db.session.delete(component)
        db.db.session.commit()
        return None, 204


def build_app():
    app = flask.Flask(__name__)
    api.init_app(app)  # init_app spoils Api object if app is a blueprint
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # silence warning
    db.db.init_app(app)
    return app


def main():
    import logging
    logging.basicConfig(level=logging.DEBUG)

    app = build_app()
    app.run()

if __name__ == '__main__':
    main()
