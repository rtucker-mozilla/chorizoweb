var mozAUApp = angular.module('mozAUApp', ['ngRoute']);
mozAUApp.config(function($routeProvider){
    $routeProvider
    // route for the home page
    .when('/', {
        templateUrl : '/static/js/pages/list.html',
        controller  : 'ServerListCtrl'
    })

    // route for the about page
    .when('/backups/:hostname', {
        templateUrl : '/static/js/pages/backup_list.html',
        controller  : 'BackupListCtrl'
    })

    .when('/backupdetail/:id', {
        templateUrl : '/static/js/pages/backup_detail.html',
        controller  : 'BackupDetailCtrl'
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

    function log(message){
        if($scope.debug && console){
            console.log(message);
        }
    }


    function recent_backups(limit){
        log("Recent Backups Called");
        $http.get('/api/recentbackupdetail/?limit=' + limit).success(function(data){
            $scope.recent = data.backups;
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
        if(!$scope.timer){
            $scope.timer = $interval(function(){
                log("Timer Fired");
                recent_backups(20);
            }, 5000);
        }
        recent_backups(20);
    }

    $scope.$on('$destroy', function() {
      log('destroy called');
      $interval.cancel($scope.timer);
    });


});

mozAUApp.controller('BackupListCtrl', function ($scope, $http, $routeParams) {
    $scope.hostname = $routeParams['hostname'];
    $scope.backups = [];
    function build_backup_list(limit){
        if (!limit){
            limit = 10;
        }
        $http.get('/api/backups/' + $scope.hostname + '?limit=' + limit).success(function(data){
            $scope.backups = data.backups;
        });
    }

    $scope.init = function(limit){
        build_backup_list(limit);
    }
});
mozAUApp.controller('BackupDetailCtrl', function ($scope, $http, $routeParams, $interval) {
    $scope.id = $routeParams['id'];
    $scope.backups = [];

    function build_backup_list(limit){
        $http.get('/api/backupdetail/' + $scope.id).success(function(data){
            $scope.backups = data.backups;
            $scope.hostname = data['hostname']
        });
    }

    $scope.init = function(limit){
        if(!$scope.timer){
            $scope.timer = $interval(function(){
                build_backup_list(1);
            }, 5000);

        }
        build_backup_list();
    }

    $scope.$on('$destroy', function() {
        $interval.cancel($scope.timer);
    });
});
