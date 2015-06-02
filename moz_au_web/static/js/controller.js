angular.module('phonecatFilters', []).filter('checkmark', function() {
  return function(input) {
      return input;
  };
});
function AccordionDemoCtrl($scope) {
  $scope.oneAtATime = true;

  $scope.groups = [
    {
      title: 'Dynamic Group Header - 1',
      content: 'Dynamic Group Body - 1'
    },
    {
      title: 'Dynamic Group Header - 2',
      content: 'Dynamic Group Body - 2'
    }
  ];

  $scope.items = ['Item 1', 'Item 2', 'Item 3'];

  $scope.addItem = function() {
    var newItemNo = $scope.items.length + 1;
    $scope.items.push('Item ' + newItemNo);
  };

  $scope.status = {
    isFirstOpen: true,
    isFirstDisabled: false
  };
}
var mozAUApp = angular.module('mozAUApp', ['ngRoute','ui.bootstrap','dndLists', 'flash']);
mozAUApp.config(function($routeProvider){
    $routeProvider
    // route for the home page
    .when('/', {
        templateUrl : '/static/js/pages/list.html',
        controller  : 'ServerListCtrl'
    })

    .when('/groups/', {
        templateUrl : '/static/js/pages/group_list.html',
        controller  : 'GroupListCtrl'
    })

    .when('/groups/create/', {
        templateUrl : '/static/js/pages/group_create.html',
        controller  : 'GroupCreateCtrl'
    })

    .when('/groups/edit_hosts/:id', {
        templateUrl : '/static/js/pages/group_host_edit.html',
        controller  : 'GroupHostEditCtrl'
    })

    .when('/groups/detail/:id', {
        templateUrl : '/static/js/pages/group_detail.html',
        controller  : 'GroupDetailCtrl'
    })

    .when('/scripts/create/', {
        templateUrl : '/static/js/pages/script_create.html',
        controller  : 'ScriptCreateCtrl'
    })

    .when('/scripts/', {
        templateUrl : '/static/js/pages/scripts_list.html',
        controller  : 'ScriptListCtrl'
    })

    .when('/scripts/edit/:id', {
        templateUrl : '/static/js/pages/script_edit.html',
        controller  : 'ScriptEditCtrl'
    })

    // route for the about page
    .when('/detail/:hostname', {
        templateUrl : '/static/js/pages/update_list.html',
        controller  : 'UpdateListCtrl'
    })

    .when('/groups/edit_scripts/:id', {
        templateUrl : '/static/js/pages/edit_scripts.html',
        controller  : 'ScriptsCtrl'
    })

    .when('/updatedetail/:id', {
        templateUrl : '/static/js/pages/update_detail.html',
        controller  : 'BackupDetailCtrl'
    })

    .when('/updatecron/:hostname', {
        templateUrl : '/static/js/pages/update_cron.html',
        controller  : 'UpdateCronCtrl'
    })

    // route for the contact page
    .when('/contact', {
        templateUrl : 'pages/contact.html',
        controller  : 'contactController'
    });
});

mozAUApp.directive('delaySearch', function ($timeout) {
        return {
            restrict: 'EA',
            template: ' <input ng-model="search" ng-change="modelChanged()">',
            link: function ($scope, element, attrs) {
                $scope.modelChanged = function () {
                    $timeout(function () {
                        if ($scope.lastSearch != $scope.search) {
                            if ($scope.delayedMethod) {
                                $scope.lastSearch = $scope.search;
                                $scope.delayedMethod({ search: $scope.search });
                            }
                        }
                    }, 300);
                }
            },
            scope: {
                delayedMethod:'&'
            }
        }
    });


mozAUApp.controller('ScriptEditCtrl', function ($scope, $location, $http, $interval, $routeParams) {
    $scope.debug = true;
    $scope.script_exit_code_reboot = ''
    $scope.id = $routeParams['id'];
    $scope.file_name = ''
    $scope.description = ''
    log('here');

    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }
    var changeLocation = function(url, forceReload) {
      $scope = $scope || angular.element(document).scope();
      if(forceReload || $scope.$$phase) {
        window.location = url;
      }
      else {
        $location.path(url);
        $scope.$apply();
      }
    };

    $scope.update = function() {
        $scope.alert_id++;
        data = {};
        data['file_name'] = $scope.file_name;
        data['description'] = $scope.description;
        data['script_exit_code_reboot'] = $scope.script_exit_code_reboot;
        $http({
            withCredentials: false,
            method: 'post',
            headers: { 'Content-Type': 'application/json' },
            url: '/api/scriptedit/' + $scope.id + '/',
            data: JSON.stringify(data)
        }).success(function(data){
            changeLocation('/#/scripts/')
        }).error(function(data){
            log(data);
        });
        log("$scope.filename: " + $scope.file_name);
        log("$scope.description: " + $scope.description);
        log("$scope.script_exit_code_reboot: " + $scope.script_exit_code_reboot);
    }


    $scope.init = function(){
        $http.get('/api/scriptdetail/' + $scope.id + '/').success(function(data){
            $scope.file_name = data.script.file_name;
            $scope.description = data.script.description;
            $scope.script_exit_code_reboot = data.script.script_exit_code_reboot;
            log($scope.scripts);
        });

    }

});
mozAUApp.controller('ScriptCreateCtrl', function ($scope, $location, $http, $interval) {
    $scope.debug = false;
    $scope.file_name = ''
    $scope.description = ''

    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }
    var changeLocation = function(url, forceReload) {
      $scope = $scope || angular.element(document).scope();
      if(forceReload || $scope.$$phase) {
        window.location = url;
      }
      else {
        $location.path(url);
        $scope.$apply();
      }
    };

    $scope.create = function() {
        $scope.alert_id++;
        data = {};
        data['file_name'] = $scope.file_name;
        data['description'] = $scope.description;
        $http({
            withCredentials: false,
            method: 'post',
            headers: { 'Content-Type': 'application/json' },
            url: '/api/scriptcreate/',
            data: JSON.stringify(data)
        }).success(function(data){
            changeLocation('/#/scripts/')
        }).error(function(data){
            log(data);
        });
        log("$scope.filename: " + $scope.file_name);
        log("$scope.description: " + $scope.description);
    }


    $scope.init = function(){
        log('init called');
    }

});

mozAUApp.controller('ScriptListCtrl', function ($scope, $http, $interval) {
    $scope.debug = false;
    $scope.scripts = [];

    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }


    function scripts(){
        $http.get('/api/scripts/').success(function(data){
            $scope.scripts = data.scripts;
            log($scope.scripts);
        });
    }

    $scope.init = function(){
        log('Calling Init')
        scripts();
    }

});
mozAUApp.controller('ServerListCtrl', function ($scope, $http, $interval) {
    $scope.debug = false;
    $scope.systems = [];
    $scope.recent = [];
    $scope.system = '';

    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }


    function recent_updates(limit){
        $http.get('/api/recentupdateonly/?limit=' + limit).success(function(data){
            $scope.recent = data.updates;
            log($scope.recent);
        });
    }



    $scope.requery = function(search){
        $scope.systems = [];
        if(search){
            $http.get('/api/system/?hostname=' + search).success(function(data){
                $scope.systems = data.systems;
            });
        }
        log("requery called");
    };

    $scope.init = function(limit){
        log("init called");
        if(!$scope.timer){
            $scope.timer = $interval(function(){
                recent_updates(20);
            }, 5000);
        }
        recent_updates(20);
    }

    $scope.$on('$destroy', function() {
      $interval.cancel($scope.timer);
    });

});

mozAUApp.controller('UpdateListCtrl', function ($scope, $http, $routeParams, $interval) {
    $scope.hostname = $routeParams['hostname'];
    $scope.has_loaded = false;
    $scope.updates = [];
    $scope.debug = true;
    $scope.system = {};
    $scope.pings = [];
    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }
    $scope.ping = function(){
        log("Ping Called");
        $http.get('/api/ping/' + $scope.hostname + '/').success(function(data){
            log(data);
        });
    }

    $scope.start_update = function(){
        log("start_update Called");
        $http.get('/api/start_system_update/' + $scope.hostname + '/').success(function(data){
            log(data);
        });
    }

    function build_update_list(limit){
        if (!limit){
            limit = 10;
        }
        $http.get('/api/updates/' + $scope.hostname + '?limit=' + limit).success(function(data){
            $scope.updates = data.updates;
        });
        $http.get('/api/system/' + $scope.hostname + '/').success(function(data){
            $scope.system = data.system;
            log($scope.system);
            $scope.pings = data.system.pings;
            log($scope.pings);
        });
        $scope.has_loaded = true;
    }
    $scope.init = function(limit){
        log("init called");
        if(!$scope.timer){
            $scope.timer = $interval(function(){
                build_update_list(limit);
            }, 5000);
        }
        build_update_list(limit);
    }

    $scope.$on('$destroy', function() {
      $interval.cancel($scope.timer);
    });

});

mozAUApp.controller('GroupCreateCtrl', function ($scope, $http, $sce, Flash) {
    $scope.has_loaded = false;
    $scope.debug = true;
    $scope.group_name = ""
    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }

    $scope.createGroup = function(event){
        log("function called");
        log("group_name: " + $scope.group_name);
        data = {};
        data['group_name'] = $scope.group_name;
        $http({
            withCredentials: false,
            method: 'post',
            headers: { 'Content-Type': 'application/json' },
            url: '/api/groups/create/',
            data: JSON.stringify(data)
        }).success(function(data){
            var message = "Group Created";
            Flash.create('success', message);
        });
    }

    $scope.init = function(limit){
    }


});

mozAUApp.controller('GroupListCtrl', function ($scope, $http, $interval) {
    $scope.has_loaded = false;
    $scope.debug = true;
    $scope.groups = [];
    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }

    function build_group_list(){
        $http.get('/api/groups/').success(function(data){
            $scope.groups = data.groups;
        });
        $scope.has_loaded = true;
    }
    $scope.init = function(limit){
        log("init called");
        if(!$scope.timer){
            $scope.timer = $interval(function(){
                build_group_list(limit);
            }, 5000);
        }
        build_group_list(limit);
    }

    $scope.$on('$destroy', function() {
      $interval.cancel($scope.timer);
    });

});

mozAUApp.controller('GroupDetailCtrl', function ($scope, $http, $interval, $routeParams, Flash) {
    $scope.id = $routeParams['id'];
    $scope.has_loaded = false;
    $scope.debug = true;
    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }

    $scope.updateHost = function(system_id){
        log("system_id: " + system_id);
        log("group_id: " + $scope.id);
        $http.get('/api/start_system_update_with_group/' + system_id + '/' + $scope.id + '/').success(function(data){
            log('start_system_update_with_group called');
        });
    }

    $scope.updateAllGroupHosts = function(){
        log("updateAllGroupHosts called");
        $http({
            withCredentials: false,
            method: 'post',
            headers: { 'Content-Type': 'application/json' },
            url: '/api/start_update/' + $scope.id + '/'
        }).success(function(data){
            var message = "Updating All Hosts in Group";
            Flash.create('success', message);
        }).error(function(data){
            log(data);
            var message = "Error: Unable to update hosts.";
            Flash.create('danger', message);
        });
    }

    function get_group(){
        $http.get('/api/groups/' + $scope.id + '/').success(function(data){
            $scope.group = data.group;
        });
        $scope.has_loaded = true;
    }
    function get_scripts(){
        $http.get('/api/groupscripts/' + $scope.id + '/').success(function(data){
            $scope.scripts = data.scripts;
        });
        $scope.has_loaded = true;
    }

    var changeLocation = function(url, forceReload) {
      $scope = $scope || angular.element(document).scope();
      if(forceReload || $scope.$$phase) {
        window.location = url;
      }
      else {
        $location.path(url);
        $scope.$apply();
      }
    };

    $scope.editGroupHosts = function(){
        changeLocation("#/groups/edit_hosts/" + $scope.id + '/');
    }
    $scope.editGroupScripts = function(){
        changeLocation("#/groups/edit_scripts/" + $scope.id + '/');
    }
    $scope.init = function(){
        get_group();
        get_scripts();
    }

});
mozAUApp.controller('UpdateCronCtrl', function ($scope, $http, $sce, $routeParams) {
    $scope.hostname = $routeParams['hostname'];
    $scope.debug = false;
    $scope.system = {};
    $scope.cronfile = "";
    $scope.show_success = false;
    $scope.success_message = "";
    $scope.alert_id = 1;
    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }
    $scope.updateCronfile = function(){
        $scope.alert_id++;
        data = {};
        data['cronfile'] = $scope.cronfile;
        $http({
            withCredentials: false,
            method: 'post',
            headers: { 'Content-Type': 'application/json' },
            url: '/api/updatecronfile/' + $scope.system.id + '/',
            data: JSON.stringify(data)
        }).success(function(data){
            var alert_text = '<div class="alert alert-success"><button type="button" class="close" id="' + $scope.alert_id +' " data-dismiss="alert" aria-hidden="true">&times;</button>Cronfile Successfully Updated</div>';
            $scope.success_message = $sce.trustAsHtml(alert_text);
        });
    }

    $scope.init = function(limit){
        $http.get('/api/system/' + $scope.hostname + '/').success(function(data){
            $scope.system = data.system;
            $scope.cronfile = $scope.system.cronfile;
        });
    }
});
mozAUApp.controller('ScriptsCtrl', function ($scope, $http, $routeParams) {
    $scope.debug = false;
    $scope.id = $routeParams['id'];
    $scope.installed_script_file_names = [];
    $scope.current_installed_scripts = {};
    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }

    $scope.models = {
        selected: null,
        lists: {
            "Installed_Scripts": [],
            "Available_Scripts": []
        }
    };

    // Generate initial model
    $http.get('/api/groupscripts/' + $scope.id + '/').success(function(data){
        for (f=0;f<data.scripts.length;f++){
            $scope.models.lists.Installed_Scripts.push({
                label: data.scripts[f].file_name,
                id: data.scripts[f].id
            });
            $scope.installed_script_file_names.push(data.scripts[f].file_name)
        }
        $scope.current_installed_scripts = $scope.models.lists.Installed_Scripts;
        $http.get('/api/scripts/').success(function(data){
            for (f=0;f<data.scripts.length;f++){
                if ($scope.installed_script_file_names.indexOf(data.scripts[f].file_name) == -1){
                    $scope.models.lists.Available_Scripts.push({
                        label: data.scripts[f].file_name,
                        id: data.scripts[f].id
                    });
                }
            }
        });
    });

    // Model to JSON for demo purpose
    $scope.save = function(){
        $scope.modelAsJson = angular.toJson($scope.models.lists.Installed_Scripts, true);
            $http({
                withCredentials: false,
                method: 'post',
                headers: { 'Content-Type': 'application/json' },
                url: '/api/updategroupscripts/' + $scope.id + '/',
                data: $scope.modelAsJson
            }).success(function(data){
                log("Successfully Saved");
            }).error(function(data){
                log(data);
        });

    }


    $scope.init = function(limit){
        log('here in model');
    }

});
mozAUApp.controller('GroupHostEditCtrl', function ($scope, $http, $routeParams) {
    $scope.debug = true;
    $scope.id = $routeParams['id'];
    $scope.enabled_host_names = [];
    $scope.s_group = {};
    $scope.current_enabled_hosts = {};
    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }

    $scope.models = {
        selected: null,
        lists: {
            "Enabled_Hosts": [],
            "Available_Hosts": []
        }
    };

    // Generate initial model
        $http.get('/api/grouphosts/' + $scope.id + '/').success(function(data){
            for (f=0;f<data.systems.length;f++){
                $scope.models.lists.Enabled_Hosts.push({
                    label: data.systems[f].hostname,
                    id: data.systems[f].id
                });
                $scope.enabled_host_names.push(data.systems[f].hostname);
            }
            log("Start scope.models.lists.Enabled_Hosts");
            log($scope.models.lists.Enabled_Hosts);
            log("End scope.models.lists.Enabled_Hosts");
            log("Start $scope.enabled_host_names");
            log($scope.enabled_host_names);
            log("End $scope.enabled_host_names");
            $scope.current_enabled_hosts = $scope.models.lists.Enabled_Hosts;
            $http.get('/api/system/').success(function(data){
                for (f=0;f<data.systems.length;f++){
                    if ($scope.enabled_host_names.indexOf(data.systems[f].hostname) == -1){
                        log("Not Found: " + data.systems[f].hostname);
                        $scope.models.lists.Available_Hosts.push({
                            label: data.systems[f].hostname,
                            id: data.systems[f].id
                        });
                    } else {
                        log("Found: " + data.systems[f].hostname);
                    }
                }
            });
        });


    // Model to JSON for demo purpose
    $scope.save = function(){
        $scope.modelAsJson = angular.toJson($scope.models.lists.Enabled_Hosts, true);
            $http({
                withCredentials: false,
                method: 'post',
                headers: { 'Content-Type': 'application/json' },
                url: '/api/updategrouphosts/' + $scope.id + '/',
                data: $scope.modelAsJson
            }).success(function(data){
                log("Successfully Saved");
            }).error(function(data){
                log(data);
        });

    }


    $scope.init = function(){
        $http.get('/api/groups/' + $scope.id + '/').success(function(data){
            $scope.s_group = data.group;
        });
    }

});
mozAUApp.controller('BackupListCtrl', function ($scope, $http, $routeParams) {
    $scope.hostname = $routeParams['hostname'];
    $scope.has_loaded = false;
    $scope.updates = [];
    $scope.debug = false;
    $scope.system = {};
    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }
    function build_update_list(limit){
        if (!limit){
            limit = 10;
        }
        $http.get('/api/updates/' + $scope.hostname + '?limit=' + limit).success(function(data){
            $scope.updates = data.updates;
        });
        $http.get('/api/system/' + $scope.hostname + '/').success(function(data){
            $scope.system = data.system;
        });
        $scope.has_loaded = true;
    }

    $scope.init = function(limit){
        build_update_list(limit);
    }
});
mozAUApp.controller('BackupDetailCtrl', function ($scope, $http, $routeParams, $interval) {
    $scope.id = $routeParams['id'];
    $scope.updates = [];
    $scope.has_loaded = false;

    function build_update_list(limit){
        $http.get('/api/updatedetail/' + $scope.id).success(function(data){
            $scope.updates = data.updates;
            $scope.hostname = data['hostname']
        });
        $scope.has_loaded = true;
    }

    $scope.init = function(limit){
        if(!$scope.timer){
            $scope.timer = $interval(function(){
                build_update_list(1);
            }, 5000);

        }
        build_update_list();
    }

    $scope.$on('$destroy', function() {
        $interval.cancel($scope.timer);
    });

});

