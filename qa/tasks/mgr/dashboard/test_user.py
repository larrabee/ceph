# -*- coding: utf-8 -*-

from __future__ import absolute_import

import time

from .helper import DashboardTestCase


class UserTest(DashboardTestCase):
    @classmethod
    def _create_user(cls, username=None, password=None, name=None, email=None, roles=None, enabled=True):
        data = {}
        if username:
            data['username'] = username
        if password:
            data['password'] = password
        if name:
            data['name'] = name
        if email:
            data['email'] = email
        if roles:
            data['roles'] = roles
        data['enabled'] = enabled
        cls._post("/api/user", data)

    @classmethod
    def _reset_login_to_admin(cls, username):
        cls.logout()
        cls.delete_user(username)
        cls.login('admin', 'admin')

    def test_crud_user(self):
        self._create_user(username='user1',
                          password='mypassword10#',
                          name='My Name',
                          email='my@email.com',
                          roles=['administrator'])
        self.assertStatus(201)
        user = self.jsonBody()

        self._get('/api/user/user1')
        self.assertStatus(200)
        self.assertJsonBody({
            'username': 'user1',
            'name': 'My Name',
            'email': 'my@email.com',
            'roles': ['administrator'],
            'lastUpdate': user['lastUpdate'],
            'enabled': True
        })

        self._put('/api/user/user1', {
            'name': 'My New Name',
            'email': 'mynew@email.com',
            'roles': ['block-manager'],
        })
        self.assertStatus(200)
        user = self.jsonBody()
        self.assertJsonBody({
            'username': 'user1',
            'name': 'My New Name',
            'email': 'mynew@email.com',
            'roles': ['block-manager'],
            'lastUpdate': user['lastUpdate'],
            'enabled': True
        })

        self._delete('/api/user/user1')
        self.assertStatus(204)

    def test_crd_disabled_user(self):
        self._create_user(username='klara',
                          password='mypassword10#',
                          name='Klara Musterfrau',
                          email='klara@musterfrau.com',
                          roles=['administrator'],
                          enabled=False)
        self.assertStatus(201)
        user = self.jsonBody()

        # Restart dashboard module.
        self._unload_module('dashboard')
        self._load_module('dashboard')
        time.sleep(10)

        self._get('/api/user/klara')
        self.assertStatus(200)
        self.assertJsonBody({
            'username': 'klara',
            'name': 'Klara Musterfrau',
            'email': 'klara@musterfrau.com',
            'roles': ['administrator'],
            'lastUpdate': user['lastUpdate'],
            'enabled': False
        })

        self._delete('/api/user/klara')
        self.assertStatus(204)

    def test_list_users(self):
        self._get('/api/user')
        self.assertStatus(200)
        user = self.jsonBody()
        self.assertEqual(len(user), 1)
        user = user[0]
        self.assertJsonBody([{
            'username': 'admin',
            'name': None,
            'email': None,
            'roles': ['administrator'],
            'lastUpdate': user['lastUpdate'],
            'enabled': True
        }])

    def test_create_user_already_exists(self):
        self._create_user(username='admin',
                          password='mypassword10#',
                          name='administrator',
                          email='my@email.com',
                          roles=['administrator'])
        self.assertStatus(400)
        self.assertError(code='username_already_exists',
                         component='user')

    def test_create_user_invalid_role(self):
        self._create_user(username='user1',
                          password='mypassword10#',
                          name='My Name',
                          email='my@email.com',
                          roles=['invalid-role'])
        self.assertStatus(400)
        self.assertError(code='role_does_not_exist',
                         component='user')

    def test_delete_user_does_not_exist(self):
        self._delete('/api/user/user2')
        self.assertStatus(404)

    @DashboardTestCase.RunAs('test', 'test', [{'user': ['create', 'read', 'update', 'delete']}])
    def test_delete_current_user(self):
        self._delete('/api/user/test')
        self.assertStatus(400)
        self.assertError(code='cannot_delete_current_user',
                         component='user')

    @DashboardTestCase.RunAs('test', 'test', [{'user': ['create', 'read', 'update', 'delete']}])
    def test_disable_current_user(self):
        self._put('/api/user/test', {'enabled': False})
        self.assertStatus(400)
        self.assertError(code='cannot_disable_current_user',
                         component='user')

    def test_update_user_does_not_exist(self):
        self._put('/api/user/user2', {'name': 'My New Name'})
        self.assertStatus(404)

    def test_update_user_invalid_role(self):
        self._put('/api/user/admin', {'roles': ['invalid-role']})
        self.assertStatus(400)
        self.assertError(code='role_does_not_exist',
                         component='user')

    def test_change_password_from_other_user(self):
        self._post('/api/user/test2/change_password', {
            'old_password': 'abc',
            'new_password': 'xyz'
        })
        self.assertStatus(400)
        self.assertError(code='invalid_user_context', component='user')

    def test_change_password_old_not_match(self):
        self._post('/api/user/admin/change_password', {
            'old_password': 'foo',
            'new_password': 'bar'
        })
        self.assertStatus(400)
        self.assertError(code='invalid_old_password', component='user')

    def test_change_password_as_old_password(self):
        self.create_user('test1', 'mypassword10#', ['read-only'], force_password=False)
        self.login('test1', 'mypassword10#')
        self._post('/api/user/test1/change_password', {
            'old_password': 'mypassword10#',
            'new_password': 'mypassword10#'
        })
        self.assertStatus(400)
        self.assertError('password_policy_validation_failed', 'user',
                         'Password cannot be the same as the previous one.')
        self._reset_login_to_admin('test1')

    def test_change_password_contains_username(self):
        self.create_user('test1', 'mypassword10#', ['read-only'], force_password=False)
        self.login('test1', 'mypassword10#')
        self._post('/api/user/test1/change_password', {
            'old_password': 'mypassword10#',
            'new_password': 'mypasstest1@#'
        })
        self.assertStatus(400)
        self.assertError('password_policy_validation_failed', 'user',
                         'Password cannot contain username.')
        self._reset_login_to_admin('test1')

    def test_change_password_contains_forbidden_words(self):
        self.create_user('test1', 'mypassword10#', ['read-only'], force_password=False)
        self.login('test1', 'mypassword10#')
        self._post('/api/user/test1/change_password', {
            'old_password': 'mypassword10#',
            'new_password': 'mypassOSD01'
        })
        self.assertStatus(400)
        self.assertError('password_policy_validation_failed', 'user',
                         'Password cannot contain keywords.')
        self._reset_login_to_admin('test1')

    def test_change_password_contains_sequential_characters(self):
        self.create_user('test1', 'mypassword10#', ['read-only'], force_password=False)
        self.login('test1', 'mypassword10#')
        self._post('/api/user/test1/change_password', {
            'old_password': 'mypassword10#',
            'new_password': 'mypass123456!@$'
        })
        self.assertStatus(400)
        self.assertError('password_policy_validation_failed', 'user',
                         'Password cannot contain sequential characters.')
        self._reset_login_to_admin('test1')

    def test_change_password_contains_repetetive_characters(self):
        self.create_user('test1', 'mypassword10#', ['read-only'], force_password=False)
        self.login('test1', 'mypassword10#')
        self._post('/api/user/test1/change_password', {
            'old_password': 'mypassword10#',
            'new_password': 'aaaaA1@!#'
        })
        self.assertStatus(400)
        self.assertError('password_policy_validation_failed', 'user',
                         'Password cannot contain repetitive characters.')
        self._reset_login_to_admin('test1')

    def test_change_password(self):
        self.create_user('test1', 'mypassword10#', ['read-only'], force_password=False)
        self.login('test1', 'mypassword10#')
        self._post('/api/user/test1/change_password', {
            'old_password': 'mypassword10#',
            'new_password': 'newpassword01#'
        })
        self.assertStatus(200)
        self.logout()
        self._post('/api/auth', {'username': 'test1', 'password': 'mypassword10#'})
        self.assertStatus(400)
        self.assertError(code='invalid_credentials', component='auth')
        self.delete_user('test1')
        self.login('admin', 'admin')

    def test_create_user_password_cli(self):
        exitcode = self._ceph_cmd_result(['dashboard', 'ac-user-create',
                                          'test1', 'mypassword10#'])
        self.assertEqual(exitcode, 0)
        self.delete_user('test1')

    def test_change_user_password_cli(self):
        self.create_user('test2', 'foo_bar_10#', force_password=False)
        exitcode = self._ceph_cmd_result(['dashboard', 'ac-user-set-password',
                                          'test2', 'foo_new-password01#'])
        self.assertEqual(exitcode, 0)
        self.delete_user('test2')

    def test_create_user_password_force_cli(self):
        exitcode = self._ceph_cmd_result(['dashboard', 'ac-user-create',
                                          '--force-password', 'test11',
                                          'bar'])
        self.assertEqual(exitcode, 0)
        self.delete_user('test11')

    def test_change_user_password_force_cli(self):
        self.create_user('test22', 'foo_bar_10#', force_password=False)
        exitcode = self._ceph_cmd_result(['dashboard', 'ac-user-set-password',
                                          '--force-password', 'test22',
                                          'bar'])
        self.assertEqual(exitcode, 0)
        self.delete_user('test22')

    def test_create_user_password_cli_fail(self):
        exitcode = self._ceph_cmd_result(['dashboard', 'ac-user-create', 'test3', 'foo'])
        self.assertNotEqual(exitcode, 0)

    def test_change_user_password_cli_fail(self):
        self.create_user('test4', 'x1z_tst+_10#', force_password=False)
        exitcode = self._ceph_cmd_result(['dashboard', 'ac-user-set-password',
                                          'test4', 'bar'])
        self.assertNotEqual(exitcode, 0)
        self.delete_user('test4')
