#!/usr/bin/python                                                                                                                                                                                                                                                            
import unittest
import os
import datetime

from chorizo_queue_state import ChorizoQueueState
from moz_au_web.system.models import System, UpdateGroup
 
class testChorizoQueueState(unittest.TestCase):
 
    def setUp(self):
    	self.cqs = ChorizoQueueState()
    def tearDown(self):
    	self.cqs = ChorizoQueueState()
 
    def test1_has_group_empty_at_init(self):
    	self.assertTrue(len(self.cqs.running_group_updates) == 0)

    def test2_add_group(self):
    	self.cqs.add_group('Test Group 1')
    	self.assertTrue(len(self.cqs.running_group_updates) == 1)
    	self.assertTrue('Test Group 1' in self.cqs.running_group_updates)

    def test3_add_group_if_not_exists(self):
    	self.cqs.add_group('Test Group 1')
    	self.assertTrue(len(self.cqs.running_group_updates) == 1)
    	self.assertTrue('Test Group 1' in self.cqs.running_group_updates)

    def test4_add_host_to_group_if_not_exists(self):
    	group_name = 'Test Group 1'
    	host_name = 'foo.localdomain'
    	host_name2 = 'foo2.localdomain'
    	host_name3 = 'foo3.localdomain'
    	group1 = UpdateGroup()
    	group1.group_name = group_name
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name)
    	self.assertTrue(len(self.cqs.running_group_updates) == 1)
    	self.assertTrue(group_name in self.cqs.running_group_updates)
    	self.assertTrue(host_name in self.cqs.running_group_updates[group_name])
    	self.assertTrue(self.cqs.running_group_updates[group_name][host_name]['scripts_to_run'] == [])
    	self.assertTrue(self.cqs.running_group_updates[group_name][host_name]['scripts_ran'] == [])
    	self.assertEqual(self.cqs.running_group_updates[group_name][host_name]['order'], 0)
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name2)
    	self.assertTrue(self.cqs.running_group_updates[group_name][host_name2]['scripts_to_run'] == [])
    	self.assertTrue(self.cqs.running_group_updates[group_name][host_name2]['scripts_ran'] == [])
    	self.assertEqual(self.cqs.running_group_updates[group_name][host_name2]['order'], 1)
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name3)
    	self.assertEqual(self.cqs.running_group_updates[group_name][host_name3]['order'], 2)

    def test5_add_script_to_host_group(self):
    	group_name = 'Test Group 1'
    	host_name = 'foo.localdomain'
    	script_name = 'test-script.sh'
    	group1 = UpdateGroup()
    	group1.group_name = group_name
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name)
    	self.cqs.add_script_to_host_group(script_name, host_name, group1)
    	self.assertTrue(self.cqs.running_group_updates[group_name][host_name]['scripts_to_run'] == [script_name])
 
    def test6_set_script_ran(self):
    	group_name = 'Test Group 1'
    	host_name = 'foo.localdomain'
    	script_name = 'test-script.sh'
    	group1 = UpdateGroup()
    	group1.group_name = group_name
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name)
    	self.cqs.add_script_to_host_group(script_name, host_name, group1)
    	self.cqs.set_script_ran(script_name, host_name, group_name)
    	self.assertTrue(self.cqs.running_group_updates[group_name][host_name]['scripts_to_run'] == [])
    	self.assertTrue(self.cqs.running_group_updates[group_name][host_name]['scripts_ran'] == [script_name])

    def test7_get_next_script_to_run(self):
    	group_name = 'Test Group 1'
    	host_name = 'foo.localdomain'
    	script_name = 'test-script.sh'
    	script_name2 = 'test-script2.sh'
    	group1 = UpdateGroup()
    	group1.group_name = group_name
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name)
    	self.cqs.add_script_to_host_group(script_name, host_name, group1)
    	self.cqs.add_script_to_host_group(script_name2, host_name, group1)
    	host, next_script = self.cqs.get_next_script_to_run(group_name)
    	self.assertEqual(host, host_name)
    	self.assertEqual(next_script, script_name)
    	self.cqs.set_script_ran(script_name, host_name, group_name)
    	host, next_script = self.cqs.get_next_script_to_run(group_name)
    	self.assertEqual(host, host_name)
    	self.assertEqual(next_script, script_name2)

    def test8_host_is_done(self):
    	group_name = 'Test Group 1'
    	host_name = 'foo.localdomain'
    	script_name = 'test-script.sh'
    	group1 = UpdateGroup()
    	group1.group_name = group_name
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name)
    	self.cqs.add_script_to_host_group(script_name, host_name, group1)
    	self.assertEqual(self.cqs.check_if_host_done(host_name, group_name), False)
    	self.cqs.set_script_ran(script_name, host_name, group_name)
    	self.assertEqual(self.cqs.check_if_host_done(host_name, group_name), True)

    def test9_get_scripts_to_run_len(self):
    	group_name = 'Test Group 1'
    	host_name = 'foo.localdomain'
    	script_name = 'test-script.sh'
    	script_name2 = 'test-script2.sh'
    	host1 = System()
    	host1.hostname = host_name
    	group1 = UpdateGroup()
    	group1.group_name = group_name
    	self.assertEqual(self.cqs.get_scripts_to_run_len(host_name, group1), 0)
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name)
    	self.assertEqual(self.cqs.get_scripts_to_run_len(host_name, group_name), 0)
    	self.cqs.add_script_to_host_group(script_name, host_name, group1)
    	self.assertEqual(self.cqs.get_scripts_to_run_len(host_name, group_name), 1)
    	self.cqs.set_script_ran(script_name, host_name, group1)
    	self.assertEqual(self.cqs.get_scripts_to_run_len(host_name, group1), 0)

    def test10_check_group_done(self):
    	group_name = 'Test Group 1'
    	group_name2 = 'Test Group 2'
    	host_name = 'foo.localdomain'
    	host_name2 = 'foo2.localdomain'
    	script_name = 'test-script.sh'
    	group1 = UpdateGroup()
    	group1.group_name = group_name
    	group2 = UpdateGroup()
    	group2.group_name = group_name2
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name)
    	self.cqs.add_host_to_group_if_not_exists(group2, host_name2)
    	self.assertEqual(self.cqs.check_if_group_done(group_name), False)
    	self.cqs.remove_host_from_group(host_name, group_name)
    	self.assertEqual(self.cqs.check_if_group_done(group_name), True)
    	self.assertEqual(self.cqs.check_if_group_done(group_name2), False)
    	self.cqs.remove_host_from_group(host_name2, group_name2)
    	self.assertEqual(self.cqs.check_if_group_done(group_name2), True)

    def test11_group_order(self):
    	group_name = 'Test Group 1'
    	group_name2 = 'Test Group 2'
    	host_name = 'foo.localdomain'
    	host_name2 = 'foo2.localdomain'
    	script_name = 'test-script.sh'
    	group1 = UpdateGroup()
    	group1.group_name = group_name
    	group2 = UpdateGroup()
    	group2.group_name = group_name2
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name)
    	self.cqs.add_host_to_group_if_not_exists(group2, host_name2)
    	self.assertEqual(self.cqs.check_if_group_done(group_name), False)
    	self.cqs.remove_host_from_group(host_name, group_name)
    	self.assertEqual(self.cqs.check_if_group_done(group_name), True)
    	self.assertEqual(self.cqs.check_if_group_done(group_name2), False)
    	self.cqs.remove_host_from_group(host_name2, group_name2)
    	self.assertEqual(self.cqs.check_if_group_done(group_name2), True)

    def test11_get_next_host_by_group(self):
    	group_name = 'Test Group 1'
    	group_name2 = 'Test Group 2'
    	host_name = 'foo.localdomain'
    	host_name2 = 'foo2.localdomain'
    	script_name = 'test-script.sh'
    	group1 = UpdateGroup()
    	group1.group_name = group_name
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name)
    	self.cqs.add_host_to_group_if_not_exists(group1, host_name2)
    	next_host = self.cqs.get_next_host_by_group(group1)
    	self.assertFalse(next_host == False)
    	self.assertEqual(next_host.keys()[0], host_name)
    	
if __name__ == '__main__':
    unittest.main()