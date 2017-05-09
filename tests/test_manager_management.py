import bson

from pillar.tests import common_test_data as ctd
from abstract_flamenco_test import AbstractFlamencoTest


class ManagerAccessTest(AbstractFlamencoTest):
    """Test for access to manager info."""

    def setUp(self, **kwargs):
        AbstractFlamencoTest.setUp(self, **kwargs)

        from pillar.api.utils.authentication import force_cli_user

        mngr_doc, account, token = self.create_manager_service_account()
        self.mngr_id = mngr_doc['_id']
        self.mngr_doc = mngr_doc
        self.mngr_token = token['token']

        self.create_user(user_id=24 * 'f', roles={'flamenco-admin'}, token='fladmin-token')

        with self.app.test_request_context():
            force_cli_user()
            job = self.jmngr.api_create_job(
                'test job',
                'Wörk wørk w°rk.',
                'sleep',
                {
                    'frames': '12-18, 20-22',
                    'chunk_size': 3,
                    'time_in_seconds': 3,
                },
                self.proj_id,
                ctd.EXAMPLE_PROJECT_OWNER_ID,
                self.mngr_id,
            )
            self.job_id = job['_id']

    def test_assign_manager_to_project(self):
        """The owner of a manager should be able to assign it to any project she's a member of."""

        self.create_project_member(user_id=24 * 'd',
                                   roles={'subscriber'},
                                   groups=[self.mngr_doc['owner']],
                                   token='owner-projmember-token')

        # User who is both owner and project member can assign.
        self.patch(
            f'/api/flamenco/managers/{self.mngr_id}',
            json={'op': 'assign-to-project',
                  'project': self.proj_id},
            auth_token='owner-projmember-token',
            expected_status=204,
        )
        self.assertManagerIsAssignedToProject(self.mngr_id, self.proj_id)

        self.patch(
            f'/api/flamenco/managers/{self.mngr_id}',
            json={'op': 'remove-from-project',
                  'project': self.proj_id},
            auth_token='owner-projmember-token',
            expected_status=204,
        )

        self.assertManagerIsNotAssignedToProject(self.mngr_id, self.proj_id)

    def test_assign_manager_to_project_denied(self):
        """Non-project members and non-owners should not be able to assign."""

        self.create_user(24 * 'c',
                         roles={'subscriber'},
                         groups=[self.mngr_doc['owner']],
                         token='owner-nonprojmember-token')

        self.create_project_member(user_id=24 * 'e',
                                   roles={'subscriber'},
                                   token='projmember-token')

        # Owner-only user cannot assign to project.
        self.patch(
            f'/api/flamenco/managers/{self.mngr_id}',
            json={'op': 'assign-to-project',
                  'project': self.proj_id},
            auth_token='owner-nonprojmember-token',
            expected_status=403,
        )

        # User who is project member but not owner the Manager cannot assign.
        self.patch(
            f'/api/flamenco/managers/{self.mngr_id}',
            json={'op': 'assign-to-project',
                  'project': self.proj_id},
            auth_token='projmember-token',
            expected_status=403,
        )

        self.assertManagerIsNotAssignedToProject(self.mngr_id, self.proj_id)

    def assertManagerIsAssignedToProject(self,
                                         manager_id: bson.ObjectId,
                                         project_id: bson.ObjectId):
        manager = self._get_manager_from_db(manager_id)
        projects = manager.get('projects', [])

        if not projects:
            self.fail(f'Manager {manager_id} is not assigned to any project')

        if project_id not in projects:
            projs = ', '.join(f"'{pid}'" for pid in projects)
            self.fail(
                f'Manager {manager_id} is not assigned to project {project_id}, only to {projs}')

        # Check that the admin group of the project is contained in the manager's group.
        with self.app.test_request_context():
            proj_coll = self.app.db().projects
            project = proj_coll.find_one({'_id': project_id}, {'permissions': 1})

        if not project:
            self.fail(f'Project {project_id} does not exist.')

        admin_group_id = project['permissions']['groups'][0]['group']
        user_groups = manager.get('user_groups', [])
        if admin_group_id not in user_groups:
            self.fail(f"Admin group {admin_group_id} is not contained in "
                      f"{manager_id}'s user_groups {user_groups}")

    def assertManagerIsNotAssignedToProject(self,
                                            manager_id: bson.ObjectId,
                                            project_id: bson.ObjectId):
        manager = self._get_manager_from_db(manager_id)
        projects = manager.get('projects', [])

        if project_id in projects:
            if len(projects) > 1:
                projs = ', '.join(f"'{pid}'" for pid in projects
                                  if pid != project_id)
                self.fail(f'Manager {manager_id} unexpectedly assigned to project {project_id} '
                          f'(as well as {projs})')
            else:
                self.fail(f'Manager {manager_id} unexpectedly assigned to project {project_id}')

        # Check that the admin group of the project is not contained in the manager's group.
        with self.app.test_request_context():
            proj_coll = self.app.db().projects
            project = proj_coll.find_one({'_id': project_id}, {'permissions': 1})

        if not project:
            self.fail(f'Project {project_id} does not exist.')

        admin_group_id = project['permissions']['groups'][0]['group']
        user_groups = manager.get('user_groups', [])
        if admin_group_id in user_groups:
            self.fail(f"Admin group {admin_group_id} is contained in "
                      f"{manager_id}'s user_groups {user_groups}")

    def _get_manager_from_db(self, mngr_id: bson.ObjectId) -> dict:
        from flamenco import current_flamenco

        with self.app.test_request_context():
            mngr_coll = current_flamenco.db('managers')
            return mngr_coll.find_one(mngr_id)
