class ChorizoQueueState(object):

    def __init__(self):
        self.running_group_updates = {}

    def has_group(self, group_name):
        return group_name in self.running_group_updates

    def add_group(self, group_name):
        self.running_group_updates[group_name] = {}

    def add_group_if_not_exists(self, group_name):
        if not self.has_group(group_name):
            self.add_group(group_name)

    def add_host_to_group_if_not_exists(self, group, host_name, add_scripts=False):
        group_name = group.group_name
        self.add_group_if_not_exists(group_name)
        if not host_name in self.running_group_updates[group_name]:
            self.running_group_updates[group_name][host_name] = {}
            self.running_group_updates[group_name][host_name]['scripts_to_run'] = []
            self.running_group_updates[group_name][host_name]['scripts_ran'] = []
            self.running_group_updates[group_name][host_name]['order'] = len(self.running_group_updates[group_name]) - 1
            if add_scripts is True:
                for s in group.scripts:
                    self.running_group_updates[group_name][host_name]['scripts_to_run'].append(s.script.file_name)


    def add_script_to_host_group(self, script_name, host_name, group):
        group_name = group.group_name
        self.add_group_if_not_exists(group_name)
        self.add_host_to_group_if_not_exists(group, host_name)
        self.running_group_updates[group_name][host_name]['scripts_to_run'].append(script_name)

    def set_script_ran(self, script_name, host_name, group_name):
        try:
            if script_name in self.running_group_updates[group_name][host_name]['scripts_to_run']:
                self.running_group_updates[group_name][host_name]['scripts_to_run'].remove(script_name)
                self.running_group_updates[group_name][host_name]['scripts_ran'].append(script_name)
            return True
        except KeyError:
            return False

    def remove_group(self, group_name):
        try:
            del self.running_group_updates[group_name]
            return True
        except:
            return False

    def remove_group_if_empty(self, group_name):
        try:
            host_count_in_group = len(self.running_group_updates[group_name])
        except KeyError:
            host_count_in_group = 0

        if host_count_in_group == 0:
            return remove_group(group_name)
        else:
            return False

    def remove_host_from_group(self, host_name, group_name):
        try:
            scripts_left_count = len(self.running_group_updates[group_name][host_name]['scripts_to_run'])
        except KeyError:
            scripts_left_count = 0

        if scripts_left_count == 0:
            try:
                del self.running_group_updates[group_name][host_name]
            except KeyError:
                pass

    def check_if_host_done(self, host_name, group_name):
        try:
            scripts_left = len(self.running_group_updates[group_name][host_name]['scripts_to_run'])
        except (IndexError, KeyError):
            scripts_left = 0
        return scripts_left == 0

    def check_if_group_done(self, group_name):
        try:
            hosts_left = len(self.running_group_updates[group_name])
        except (IndexError, KeyError):
            hosts_left = 0

        return hosts_left == 0

    def get_scripts_to_run_len(self, host_name, group_name):
        try:
            return len(self.running_group_updates[group_name][host_name]['scripts_to_run'])
        except KeyError:
            return 0

    def get_next_host_by_group(self, group):
        group_name = group.group_name
        try:
            ret_sorted = sorted(self.running_group_updates[group_name].iteritems(), key=lambda (x, y): y['order'])
            return ret_sorted[0][0]
        except (KeyError, IndexError):
            return False

    def get_next_script_to_run(self, group_name):
        if not group_name in self.running_group_updates:
            return None, None
        for dict_host in self.running_group_updates[group_name].copy().iterkeys():
            try:
                script_to_run = self.running_group_updates[group_name][dict_host]['scripts_to_run'][0]
            except (KeyError, IndexError):
                script_to_run = None

            if dict_host and script_to_run:
                return dict_host, script_to_run

        return None, None
