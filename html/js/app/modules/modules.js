/*global angular*/

/**
 * Configuration directive
 * Handle all modules configuration
 */
angular
.module('Cleep')
.directive('modulesDirective', ['$rootScope', 'cleepService', '$window', 'toastService', 'confirmService', '$mdDialog', '$location', '$anchorScroll',
function($rootScope, cleepService, $window, toast, confirm, $mdDialog, $location, $anchorScroll) {

    var modulesController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.cleepService = cleepService;
        self.search = {'$': ''};
        self.updates = [];
        self.displayedModules = [];
        self.moduleUpdate = {};
        self.moduleNotStarted = null;

        /**
         * Clear search input
         */
        self.clearSearch = function() {
            self.search['$'] = '';
        };

        /**
         * Redirect to install module page
         */
        self.gotoInstallPage = function() {
            $window.location.href = '#!install';
        };

        /**
         * Redirect to update module page
         */
        self.gotoUpdateModule = function() {
            $window.location.href = '#!/module/update?tab=logs';
        }

        /**
         * Uninstall module
         */
        self.uninstallModule = function(module) {
            confirm.open(
                'App uninstallation',
                'Do you want to uninstall ' + module + ' application?<br/>Configuration files will be kept.',
                'Uninstall',
                'Cancel'
            )
                .then(function() {
                    // uninstall module
                    return cleepService.uninstallModule(module);
                }, function() {});
        };

        /**
         * Force module uninstall
         */
        self.forceUninstallModule = function(module) {
            // close dialog
            self.closeDialog();

            // uninstall module
            return cleepService.forceUninstallModule(module);
        };

        /**
         * Update module
         */
        self.updateModule = function(module) {
            // close dialog
            self.closeDialog();

            // update module
            cleepService.updateModule(module);
        };

        /**
         * Init controller
         */
        self.$onInit = function() {
            // scroll to app
            if( $location.search().app ) {
                $location.hash('mod-' + $location.search().app);
                $anchorScroll();
            }

            // load mandatory stuff
            cleepService.getInstallableModules();
            cleepService.refreshModulesUpdates();

            // add fab action
            action = [{
                callback: self.gotoInstallPage,
                icon: 'plus',
                aria: 'Install app',
                tooltip: 'Install app'
            }];
            $rootScope.$broadcast('enableFab', action);
        };

        /**
         * Fill modules
         */
        self.fillModules = function() {
            var modules = [];
            for( var [moduleName, module] of Object.entries(cleepService.modules) ) {
                if (module.library) {
                    continue;
                }
                modules.push(module);
            }
            self.displayedModules = modules;
        };

        /**
         * Fill modules as soon as cleep configuration is loaded
         */
        $scope.$watchCollection(
            function() {
                return cleepService.modules;
            },
            function(newValue, oldValue) {
                if( newValue && Object.keys(newValue).length ) {
                    self.fillModules();
                }
            }
        );

        /**
         * Close update dialog
         */
        self.closeDialog = function() {
            $mdDialog.hide();
        };

        /**
         * Show module update dialog
         */
        self.showModuleUpdateDialog = function(module, ev) {
            self.moduleUpdate = module;

            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'updateCtl',
                templateUrl: 'js/app/modules/update.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            })
            .then(function() {}, function() {});
        };

        /**
         * Show not started dialog
         */
        self.showNotStartedDialog = function(module, ev) {
            self.moduleNotStarted = module;
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'notstartedCtl',
                templateUrl: 'js/app/modules/not-started.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            })
            .then(function() {}, function() {});
        };

        /** 
         * Catch module uninstall events
         */
        $rootScope.$on('update.module.uninstall', function(event, uuid, params) {
            // module uninstall event received, refresh modules updates infos
            cleepService.refreshModulesUpdates();
        });

        /** 
         * Catch module update events
         */
        $rootScope.$on('update.module.update', function(event, uuid, params) {
            // module update event received, refresh modules updates infos
            cleepService.refreshModulesUpdates();
        });

    }];

    return {
        templateUrl: 'js/app/modules/modules.html',
        replace: true,
        controller: modulesController,
        controllerAs: 'modulesCtl',
    };
}]);

