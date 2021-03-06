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

from tuning_box import db
from tuning_box.tests.test_app import BaseTest


class TestResourceOverrides(BaseTest):

    object_url = '/environments/{0}/{1}resources/{2}/overrides'
    object_keys_url = object_url + '/keys/{3}'

    def test_put_resource_values_overrides_root(self):
        self._fixture()
        res = self.client.put('/environments/9/resources/5/overrides',
                              data={'k': 'v'})
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')
        with self.app.app_context():
            resource_values = db.ResourceValues.query.filter_by(
                environment_id=9, resource_definition_id=5).one_or_none()
            self.assertIsNotNone(resource_values)
            self.assertEqual(resource_values.overrides, {'k': 'v'})
            self.assertIsNone(resource_values.level_value)

    def test_put_resource_values_overrides_deep(self):
        self._fixture()
        res = self.client.put(
            '/environments/9/lvl1/val1/lvl2/val2/resources/5/overrides',
            data={'k': 'v'},
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')
        with self.app.app_context():
            resource_values = db.ResourceValues.query.filter_by(
                environment_id=9, resource_definition_id=5).one_or_none()
            self.assertIsNotNone(resource_values)
            self.assertEqual(resource_values.overrides, {'k': 'v'})
            level_value = resource_values.level_value
            self.assertIsNotNone(level_value)
            self.assertEqual(level_value.level.name, 'lvl2')
            self.assertEqual(level_value.value, 'val2')
            level = level_value.level.parent
            self.assertIsNotNone(level)
            self.assertEqual(level.name, 'lvl1')
            self.assertIsNone(level.parent)

    def test_get_resource_values_local_override(self):
        self._fixture()
        self.client.put('/environments/9/lvl1/1/resources/5/values',
                        data={'key': 'value1'})
        res = self.client.put('/environments/9/lvl1/1/resources/5/overrides',
                              data={'key': 'value2'})
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')
        res = self.client.get(
            '/environments/9/lvl1/1/resources/5/values?effective',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {'key': 'value2'})

    def test_get_resource_values_level_override(self):
        self._fixture()
        self.client.put('/environments/9/resources/5/values',
                        data={'key': 'value', 'key1': 'value'})
        self.client.put('/environments/9/lvl1/1/resources/5/values',
                        data={'key': 'value1'})
        res = self.client.put('/environments/9/lvl1/2/resources/5/values',
                              data={'key1': 'value2'})
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')
        res = self.client.get(
            '/environments/9/lvl1/1/resources/5/values?effective',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {'key': 'value1', 'key1': 'value'})

    def test_get_resource_values_level_and_local_override(self):
        self._fixture()
        self.client.put('/environments/9/resources/5/values',
                        data={'key': 'value', 'key1': 'value'})
        self.client.put('/environments/9/lvl1/1/resources/5/values',
                        data={'key': 'value1'})
        res = self.client.put('/environments/9/lvl1/1/resources/5/overrides',
                              data={'key1': 'value2'})
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')
        res = self.client.get(
            '/environments/9/lvl1/1/resources/5/values?effective',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {'key': 'value1', 'key1': 'value2'})

    def test_put_resource_overrides_by_name(self):
        self._fixture()
        env_id = 9
        res_id = 5
        res_name = 'resdef1'
        levels = (('lvl1', 'val1'), ('lvl2', 'val2'))
        data = {'k': 'v'}

        obj_name_url = self.object_url.format(
            env_id,
            self.get_levels_path(levels),
            res_name
        )
        res = self.client.put(obj_name_url, data=data)
        self.assertEqual(204, res.status_code)

        obj_id_url = self.object_url.format(
            env_id,
            self.get_levels_path(levels),
            res_id
        )
        res = self.client.get(obj_id_url)
        self.assertEqual(200, res.status_code)
        self.assertEqual(data, res.json)

    def test_get_resource_overrides_by_name(self):
        self._fixture()
        env_id = 9
        res_id = 5
        res_name = 'resdef1'
        levels = (('lvl1', 'val1'), ('lvl2', 'val2'))

        obj_id_url = self.object_url.format(
            env_id,
            self.get_levels_path(levels),
            res_id
        )
        data = {'key': 'value'}
        self.client.put(obj_id_url, data=data)

        obj_name_url = self.object_url.format(
            env_id,
            self.get_levels_path(levels),
            res_name
        )
        res = self.client.get(obj_name_url)
        self.assertEqual(200, res.status_code)
        self.assertEqual(data, res.json)

    def test_put_resource_overrides_set_operation_error(self):
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self._fixture()

        environment_id = 9
        res_def_id = 5
        levels = (('lvl1', 'val1'), ('lvl2', 'val2'))
        overrides = {'key': 'val_overridden'}
        self._add_resource_overrides(environment_id, res_def_id, levels,
                                     overrides)

        data = [['a', 'b', 'c', 'value']]
        obj_keys_url = self.object_keys_url.format(
            environment_id,
            self.get_levels_path(levels),
            res_def_id,
            'set'
        )

        res = self.client.put(obj_keys_url, data=data)
        self.assertEqual(409, res.status_code)

    def test_put_resource_overrides_set(self):
        self._fixture()
        environment_id = 9
        res_def_id = 5
        levels = (('lvl1', 'val1'), ('lvl2', 'val2'))
        overrides = {'key': 'val_overridden'}
        self._add_resource_overrides(environment_id, res_def_id, levels,
                                     overrides)

        obj_url = self.object_url.format(
            environment_id,
            self.get_levels_path(levels),
            res_def_id
        )
        obj_keys_url = obj_url + '/keys/set'

        data = [['key', 'key_over'], ['key_x', 'key_x_over']]
        res = self.client.put(obj_keys_url, data=data)
        self.assertEqual(204, res.status_code)

        res = self.client.get(obj_url)
        self.assertEqual(200, res.status_code)
        actual = res.json
        self.assertEqual({'key': 'key_over', 'key_x': 'key_x_over'},
                         actual)

    def test_put_resource_overrides_set_no_levels(self):
        self._fixture()
        environment_id = 9
        res_def_id = 5
        values = {'key': 'val'}
        self._add_resource_overrides(environment_id, res_def_id, (), values)

        obj_url = '/environments/{0}/resources/{1}/overrides'.format(
            environment_id, res_def_id)
        obj_keys_url = obj_url + '/keys/set'

        data = [['key', 'key_value'], ['key_x', 'key_x_value']]
        res = self.client.put(obj_keys_url, data=data)
        self.assertEqual(204, res.status_code)

        res = self.client.get(obj_url)
        self.assertEqual(200, res.status_code)
        actual = res.json
        self.assertEqual({'key': 'key_value', 'key_x': 'key_x_value'},
                         actual)

    def test_put_resource_overrides_delete(self):
        self._fixture()
        environment_id = 9
        res_def_id = 5
        levels = (('lvl1', 'val1'), ('lvl2', 'val2'))
        overrides = {'key_0': 'val_0', 'key_1': 'val_1'}
        self._add_resource_overrides(environment_id, res_def_id, levels,
                                     overrides)

        obj_url = self.object_url.format(
            environment_id,
            self.get_levels_path(levels),
            res_def_id
        )
        obj_keys_url = obj_url + '/keys/delete'

        data = [['key_0']]
        res = self.client.put(obj_keys_url, data=data)
        self.assertEqual(204, res.status_code)

        res = self.client.get(obj_url)
        self.assertEqual(200, res.status_code)
        actual = res.json
        self.assertEqual({'key_1': 'val_1'}, actual)

    def test_put_resource_overrides_delete_operation_error(self):
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self._fixture()
        environment_id = 9
        res_def_id = 5
        levels = (('lvl1', 'val1'), ('lvl2', 'val2'))
        overrides = {'key_0': 'val_0', 'key_1': 'val_1'}
        self._add_resource_overrides(environment_id, res_def_id, levels,
                                     overrides)

        obj_keys_url = self.object_keys_url.format(
            environment_id,
            self.get_levels_path(levels),
            res_def_id,
            'delete'
        )
        data = [['fake_key']]
        res = self.client.put(obj_keys_url, data=data)
        self.assertEqual(409, res.status_code)

        data = [['key_0', 'val_0']]
        res = self.client.put(obj_keys_url, data=data)
        self.assertEqual(409, res.status_code)

    def test_get_resource_overrides_effective_with_lookup(self):
        self._fixture()
        res = self.client.put('/environments/9/resources/5/values',
                              data={'key0': 'root_value_0',
                                    'key1': 'root_value_1',
                                    'key2': 'root_value_2',
                                    'key3': 'root_value_3'})
        self.assertEqual(res.status_code, 204)
        res = self.client.put('/environments/9/lvl1/1/resources/5/values',
                              data={'key0': 'lvl1_value_0'})
        self.assertEqual(res.status_code, 204)

        # Override key0 on level1
        res = self.client.put('/environments/9/lvl1/1/resources/5/overrides',
                              data={'key0': 'lvl1_overrides_0'})
        self.assertEqual(res.status_code, 204)

        # Override key1 on level1/level2
        res = self.client.put(
            '/environments/9/lvl1/1/lvl2/2/resources/5/values',
            data={'key1': 'lvl2_value_1', 'key2': 'lvl2_value_2'}
        )
        self.assertEqual(res.status_code, 204)
        res = self.client.put(
            '/environments/9/lvl1/1/lvl2/2/resources/5/overrides',
            data={'key1': 'lvl2_overrides_1'}
        )
        self.assertEqual(res.status_code, 204)

        # Checking lookup info
        res = self.client.get(
            '/environments/9/lvl1/1/lvl2/2/resources/5/values',
            query_string={'effective': 1, 'show_lookup': 1}
        )
        self.assertEqual(res.status_code, 200)
        expected = {
            'key0': ['lvl1_overrides_0', '/lvl1/1/'],
            'key1': ['lvl2_overrides_1', '/lvl1/1/lvl2/2/'],
            'key2': ['lvl2_value_2', '/lvl1/1/lvl2/2/'],
            'key3': ['root_value_3', '/']
        }
        self.assertEqual(expected, res.json)
