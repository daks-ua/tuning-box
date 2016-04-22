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

import os

# oslo_db internals refuse to work properly if this is not set
# actual file name in that URL doesn't matter, it'll be generated by oslo.db
os.environ.setdefault("OS_TEST_DBAPI_ADMIN_CONNECTION", "sqlite:///testdb")

from alembic import command as alembic_command
from alembic import config as alembic_config
from alembic import script as alembic_script
import flask
from oslo_db.sqlalchemy import test_base
from oslo_db.sqlalchemy import test_migrations
import pkg_resources
import sqlalchemy as sa
import testscenarios
from werkzeug import exceptions

from tuning_box import db
from tuning_box.tests import base


class _DBTestCase(base.TestCase):
    def setUp(self):
        super(_DBTestCase, self).setUp()
        self.app = flask.Flask('test')
        self.app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///'
        self.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # no warning
        db.db.init_app(self.app)
        with self.app.app_context():
            db.fix_sqlite()
            db.db.create_all()


class TestDB(_DBTestCase):
    def test_create_all(self):
        pass

    def test_get_or_create_get(self):
        with self.app.app_context():
            db.db.session.add(db.Component(name="nsname"))
            res = db.get_or_create(db.Component, name="nsname")
            self.assertEqual(res.name, "nsname")

    def test_get_or_create_create(self):
        with self.app.app_context():
            res = db.get_or_create(db.Component, name="nsname")
            self.assertIsNotNone(res.id)
            self.assertEqual(res.name, "nsname")


class TestGetByIdOrName(_DBTestCase):
    def setUp(self):
        super(TestGetByIdOrName, self).setUp()
        ctx = self.app.app_context()
        ctx.push()
        self.addCleanup(ctx.pop)
        self.component = db.Component(name="compname")
        db.db.session.add(self.component)
        db.db.session.flush()

    def test_by_id(self):
        res = db.Component.query.get_by_id_or_name(self.component.id)
        self.assertEqual(self.component, res)

    def test_by_name(self):
        res = db.Component.query.get_by_id_or_name(self.component.name)
        self.assertEqual(self.component, res)

    def test_by_id_fail(self):
        self.assertRaises(
            exceptions.NotFound,
            db.Component.query.get_by_id_or_name,
            self.component.id + 1,
        )

    def test_by_name_fail(self):
        self.assertRaises(
            exceptions.NotFound,
            db.Component.query.get_by_id_or_name,
            self.component.name + "_",
        )


class TestDBPrefixed(base.PrefixedTestCaseMixin, TestDB):
    pass


class TestEnvironmentHierarchyLevel(_DBTestCase):
    def setUp(self):
        super(TestEnvironmentHierarchyLevel, self).setUp()
        with self.app.app_context():
            session = db.db.session
            environment = db.Environment()
            session.add(environment)
            session.commit()
            self.environment_id = environment.id

    def _create_levels(self, num):
        session = db.db.session
        last_lvl = None
        for i in range(num):
            lvl = db.EnvironmentHierarchyLevel(
                environment_id=self.environment_id,
                parent=last_lvl,
                name="lvl%s" % (i,),
            )
            session.add(lvl)
            last_lvl = lvl
        session.commit()

    def _test_get_for_environment(self, num, expected):
        with self.app.app_context():
            self._create_levels(num)
            res = db.EnvironmentHierarchyLevel.get_for_environment(
                db.Environment(id=self.environment_id))
        level_names = [level.name for level in res]
        self.assertEqual(level_names, expected)

    def test_get_for_environment_empty(self):
        self._test_get_for_environment(0, [])

    def test_get_for_environment_one(self):
        self._test_get_for_environment(1, ['lvl0'])

    def test_get_for_environment_three(self):
        self._test_get_for_environment(3, ['lvl0', 'lvl1', 'lvl2'])


class TestEnvironmentHierarchyLevelPrefixed(base.PrefixedTestCaseMixin,
                                            TestEnvironmentHierarchyLevel):
    pass


class _RealDBTest(testscenarios.WithScenarios,
                  base.TestCase,
                  test_base.DbTestCase):
    scenarios = [
        ('sqlite', {'FIXTURE': test_base.DbFixture}),
        # ('mysql', {'FIXTURE': test_base.MySQLOpportunisticFixture}),
        ('postgres', {'FIXTURE': test_base.PostgreSQLOpportunisticFixture}),
    ]

    def get_migrations_dir(self):
        return pkg_resources.resource_filename('tuning_box', 'migrations')

    def get_alembic_config(self, engine):
        config = alembic_config.Config()
        config.set_main_option('sqlalchemy.url', str(engine.url))
        config.set_main_option('script_location', self.get_migrations_dir())
        config.set_main_option('version_table', 'alembic_version')
        return config


class _RealDBPrefixedTest(base.PrefixedTestCaseMixin,
                          _RealDBTest):
    def get_alembic_config(self, engine):
        config = super(_RealDBPrefixedTest, self).get_alembic_config(
            engine)
        config.set_main_option('version_table', 'test_prefix_alembic_version')
        config.set_main_option('table_prefix', 'test_prefix_')
        return config


class TestMigrationsSync(_RealDBTest,
                         test_migrations.ModelsMigrationsSync):
    def get_metadata(self):
        return db.db.metadata

    def get_engine(self):
        return self.engine

    def db_sync(self, engine):
        config = self.get_alembic_config(engine)
        alembic_command.upgrade(config, 'head')


class TestMigrationsSyncPrefixed(_RealDBPrefixedTest,
                                 TestMigrationsSync):
    def include_object(self, object_, name, type_, reflected, compare_to):
        # ModelsMigrationsSync doesn't pass any config to MigrationContext
        # so alembic assumes 'alembic_version' table by default, not our
        # prefixed table
        if type_ == 'table' and name == 'test_prefix_alembic_version':
            return False

        return super(TestMigrationsSyncPrefixed, self).include_object(
            object_, name, type_, reflected, compare_to)


class TestRemoveFakeRootMigration(_RealDBTest):
    revision = '9ae15c85fa92'
    prefix = ''

    def setUp(self):
        super(TestRemoveFakeRootMigration, self).setUp()
        self.alembic_config = self.get_alembic_config(self.engine)
        script_dir = alembic_script.ScriptDirectory.from_config(
            self.alembic_config)
        self.migration_module = script_dir.get_revision(self.revision).module
        self.down_revision = self.migration_module.down_revision
        self.session = sa.orm.Session(bind=self.engine)
        self.addCleanup(self.session.close)

    def test_upgrade(self):
        alembic_command.upgrade(self.alembic_config, self.down_revision)
        abase = self.migration_module._get_autobase(self.prefix, self.engine)
        clss = abase.classes
        env = clss.Environment()
        env_level = clss.EnvironmentHierarchyLevel(environment=env, name='lvl')
        self.session.add(env_level)
        fake_root_1 = clss.EnvironmentHierarchyLevelValue(
            level_id=None, value=None, parent_id=None)
        self.session.add(fake_root_1)
        self.session.flush()
        child_1 = clss.EnvironmentHierarchyLevelValue(
            level_id=env_level.id, value="1", parent_id=fake_root_1.id)
        self.session.add(child_1)
        fake_root_2 = clss.EnvironmentHierarchyLevelValue(
            level_id=None, value=None, parent_id=None)
        self.session.add(fake_root_2)
        self.session.flush()
        child_2 = clss.EnvironmentHierarchyLevelValue(
            level_id=env_level.id, value="2", parent_id=fake_root_2.id)
        self.session.add(child_2)
        self.session.commit()
        alembic_command.upgrade(self.alembic_config, self.revision)
        ehlvs = self.session.query(clss.EnvironmentHierarchyLevelValue).all()
        for ehlv in ehlvs:
            self.assertIsNotNone(ehlv.level_id)
            self.assertIsNone(ehlv.parent_id)

    def test_downgrade(self):
        alembic_command.upgrade(self.alembic_config, self.revision)
        abase = self.migration_module._get_autobase(self.prefix, self.engine)
        clss = abase.classes
        env = clss.Environment()
        env_level = clss.EnvironmentHierarchyLevel(environment=env, name='lvl')
        self.session.add(env_level)
        self.session.flush()
        child_1 = clss.EnvironmentHierarchyLevelValue(
            level_id=env_level.id, value="1", parent_id=None)
        self.session.add(child_1)
        child_2 = clss.EnvironmentHierarchyLevelValue(
            level_id=env_level.id, value="2", parent_id=None)
        self.session.add(child_2)
        self.session.commit()
        alembic_command.downgrade(self.alembic_config, self.down_revision)
        fake_root = self.session.query(clss.EnvironmentHierarchyLevelValue) \
            .filter_by(parent_id=None) \
            .one()
        self.assertIsNone(fake_root.level_id)
        self.assertIsNone(fake_root.value)
        children = self.session.query(clss.EnvironmentHierarchyLevelValue) \
            .filter_by(parent_id=fake_root.id) \
            .all()
        self.assertItemsEqual(["1", "2"], [c.value for c in children])
        for child in children:
            self.assertEqual(fake_root.id, child.parent_id)
            self.assertEqual(env_level.id, child.level_id)


class TestRemoveFakeRootMigrationPrefixed(_RealDBPrefixedTest,
                                          TestRemoveFakeRootMigration):
    prefix = 'test_prefix_'
