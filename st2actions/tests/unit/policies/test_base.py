# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

import st2actions
from st2tests import config as test_config
test_config.parse_args()
from st2actions.notifier import notifier
from st2common.bootstrap.policiesregistrar import register_policy_types
from st2common.models.db.action import LiveActionDB
from st2common.persistence.policy import Policy
from st2common.services import action as action_service
from st2tests.base import DbTestCase
from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import FixturesLoader


__all__ = [
    'BasePoliciesTestCase'
]


PACK = 'generic'
TEST_FIXTURES = {
    'runners': [
        'testrunner1.yaml'
    ],
    'actions': [
        'action1.yaml'
    ],
    'policies': [
        'policy_4.yaml'
    ]
}


class BasePoliciesTestCase(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        DbTestCase.setUpClass()
        super(BasePoliciesTestCase, cls).setUpClass()

    def setUp(self):
        super(BasePoliciesTestCase, self).setUp()

        # Register common policy types
        register_policy_types(st2actions)

        loader = FixturesLoader()
        models = loader.save_fixtures_to_db(fixtures_pack=PACK,
                                            fixtures_dict=TEST_FIXTURES)

        # Instantiate policy applicator we will use in the tests
        self.policy_db = models['policies']['policy_4.yaml']

    @mock.patch('st2actions.notifier.notifier.policies')
    def test_disabled_policies_are_not_applied(self, mock_policies):
        notifier_worker = notifier.get_notifier()

        ##########
        # First test a scenario where policy is enabled
        ##########
        self.assertTrue(self.policy_db.enabled)

        # Post run hasn't been called yet, call count should be 0
        self.assertEqual(mock_policies.get_driver.call_count, 0)

        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        live_action_db, execution_db = action_service.request(liveaction)
        notifier_worker._apply_post_run_policies(liveaction=live_action_db)

        # Ony policy has been applied so call count should be 1
        self.assertEqual(mock_policies.get_driver.call_count, 1)

        ##########
        # Now a scenaro with disabled policy
        ##########
        mock_policies.get_driver.call_count = 0
        self.policy_db.enabled = False
        self.policy_db = Policy.add_or_update(self.policy_db)
        self.assertFalse(self.policy_db.enabled)

        self.assertEqual(mock_policies.get_driver.call_count, 0)


        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        live_action_db, execution_db = action_service.request(liveaction)
        notifier_worker._apply_post_run_policies(liveaction=live_action_db)

        # Policy is disabled so call_count should stay the same as before as no policies have been
        # applied
        self.assertEqual(mock_policies.get_driver.call_count, 0)
