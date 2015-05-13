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
var mozAUApp = angular.module('mozAUApp', ['ngRoute','ui.bootstrap','dndLists']);
mozAUApp.config(function($routeProvider){
    $routeProvider
    // route for the home page
    .when('/', {
        templateUrl : '/static/js/pages/list.html',
        controller  : 'ServerListCtrl'
    })

    .when('/scripts/create/', {
        templateUrl : '/static/js/pages/script_create.html',
        controller  : 'ScriptCreateCtrl'
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

    .when('/scripts/:hostname', {
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
    $scope.debug = false;
    $scope.id = $routeParams['id'];
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

    $scope.update = function() {
        $scope.alert_id++;
        data = {};
        data['file_name'] = $scope.file_name;
        data['description'] = $scope.description;
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
    }


    $scope.init = function(){
        $http.get('/api/scriptdetail/' + $scope.id + '/').success(function(data){
            $scope.file_name = data.script.file_name;
            $scope.description = data.script.description;
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
    $scope.debug = false;
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
        $http.get('/api/start_update/' + $scope.hostname + '/').success(function(data){
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
    $scope.hostname = $routeParams['hostname'];
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
    $http.get('/api/hostscripts/' + $scope.hostname + '/').success(function(data){
        for (f=0;f<data.scripts.length;f++){
            $scope.models.lists.Installed_Scripts.push({
                label: data.scripts[f].file_name,
                id: data.scripts[f].id
            });
            $scope.installed_script_file_names.push(data.scripts[f].file_name)
        }
        $scope.current_installed_scripts = $scope.models.lists.Installed_Scripts;
    });
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

    // Model to JSON for demo purpose
    $scope.save = function(){
        $scope.modelAsJson = angular.toJson($scope.models.lists.Installed_Scripts, true);
            $http({
                withCredentials: false,
                method: 'post',
                headers: { 'Content-Type': 'application/json' },
                url: '/api/updatehostscripts/' + $scope.hostname + '/',
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

