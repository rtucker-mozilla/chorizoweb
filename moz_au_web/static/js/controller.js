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

    // route for the about page
    .when('/updates/:hostname', {
        templateUrl : '/static/js/pages/update_list.html',
        controller  : 'BackupListCtrl'
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
        log("Recent Backups Called");
        $http.get('/api/recentupdatedetail/?limit=' + limit).success(function(data){
            $scope.recent = data.updates;
            log($scope.recent);
        });
        /*$http.get('/api/system/asdf').success(function(data){
            $scope.recent = data.system;
        });*/
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
        if(!$scope.timer){
            $scope.timer = $interval(function(){
                log("Timer Fired");
                recent_updates(20);
            }, 5000);
        }
        recent_updates(20);
    }

    $scope.$on('$destroy', function() {
      $interval.cancel($scope.timer);
    });

});

mozAUApp.controller('UpdateListCtrl', function ($scope, $http, $routeParams) {
    $scope.hostname = $routeParams['hostname'];
    $scope.has_loaded = false;
    $scope.updates = [];
    $scope.debug = true;
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
        $http.get('/api/system/' + $scope.hostname).success(function(data){
            $scope.system = data.system;
        });
        $scope.has_loaded = true;
    }

    $scope.init = function(limit){
        log($scope.hostname);
        build_update_list(limit);
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
        $http.get('/api/system/' + $scope.hostname).success(function(data){
            $scope.system = data.system;
            $scope.cronfile = $scope.system.cronfile;
        });
    }
});
mozAUApp.controller('ScriptsCtrl', function ($scope, $http, $routeParams) {
    $scope.debug = true;
    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }

    $scope.models = {
        selected: null,
        lists: {"Installed_Scripts": [], "Available_Scripts": []}
    };

    // Generate initial model
    for (var i = 1; i <= 3; ++i) {
        $scope.models.lists.Installed_Scripts.push({label: "Script A" + i});
        $scope.models.lists.Available_Scripts.push({label: "Script B" + i});
    }

    // Model to JSON for demo purpose
    $scope.$watch('models', function(model) {
        $scope.modelAsJson = angular.toJson(model, true);
    }, true);

    $scope.init = function(limit){
        log('here');
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
        $http.get('/api/system/' + $scope.hostname).success(function(data){
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

