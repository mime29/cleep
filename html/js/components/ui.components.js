/*global angular*/

angular.module('Cleep').component('clIcon', {
    template: `
        <md-icon ng-if="$ctrl.clTooltip" md-font-icon="{{ $ctrl.mdFontIcon }}" ng-class="$ctrl.clClass">
            <md-tooltip>{{ $ctrl.clTooltip }}</md-tooltip>
        </md-icon>
        <md-icon ng-if="!$ctrl.clTooltip" md-font-icon="{{ $ctrl.mdFontIcon }}" ng-class="$ctrl.clClass">
        </md-icon>`,
    bindings: {
        clIcon: '@',
        clTooltip: '@?',
        clClass: '@?'
    },
    controller: function() {
        const ctrl = this;

        ctrl.$onChanges = function(changes) {
            if (changes.clIcon?.currentValue) {
                const icon = changes.clIcon.currentValue;
                if (icon.startsWith('brand-')) {
                    ctrl.mdFontIcon = 'brand ' + icon;
                } else {
                    ctrl.mdFontIcon = 'mdi mdi-' + icon;
                }
            }
        };
    },
});

angular.module('Cleep').component('clAppImg', {
    template: `
        <img ng-src="{{ $ctrl.src }}" width="{{ $ctrl.clWidth }}" height="{{ $ctrl.clHeight }}"/>
    `,
    bindings: {
        clSrc: '@',
        clWidth: '@?',
        clHeight: '@?',
    },
    controller: function($location) {
        const MODULES_PATH = 'js/modules/';
        const ctrl = this;
        ctrl.src = '';
        
        ctrl.$onInit = function() {
            ctrl.src = MODULES_PATH + ctrl.getAppName() + ctrl.getClSrc();
        };

        ctrl.getClSrc = function() {
            if (!ctrl.clSrc) {
                return '';
            }
            return ctrl.clSrc[0] === '/' ? ctrl.clSrc : '/' + ctrl.clSrc;
        };

        ctrl.getAppName = function() {
            return $location.path().replace('/module/', '');
        };
    }
});

angular.module('Cleep').component('clAppFab', {
    template: `
    <div>
        <!-- single action -->
        <md-button ng-if="$ctrl.actions.length === 1" ng-click="$ctrl.onClick($ctrl.actions[0])" class="md-accent md-fab md-fab-bottom-right" style="position:fixed !important;">
            <md-tooltip md-direction="top">{{ $ctrl.actions[0].tooltip }}</md-tooltip>
            <cl-icon cl-icon="{{ $ctrl.actions[0].icon }}"></cl-icon>
        </md-button>

        <!-- multiple actions -->
        <md-fab-speed-dial ng-if="$ctrl.actions.length > 1" md-direction="left" class="md-scale md-fab-bottom-right" style="position:fixed !important;">
            <md-fab-trigger>
                <md-button class="md-accent md-fab md-primary">
                    <cl-icon cl-icon="dots-vertical"></cl-icon>
                </md-button>
            </md-fab-trigger>
            <md-fab-actions>
                <md-button ng-repeat="action in $ctrl.actions" ng-click="$ctrl.onClick(action)" class="md-accent md-fab md-mini md-primary">
                    <md-tooltip md-direction="top">{{ action.tooltip }}</md-tooltip>
                    <cl-icon cl-icon="{{ action.icon }}"></cl-icon>
                </md-button>
            </md-fab-actions>
        </md-fab-speed-dial>
    </div>
    `,
    controller: function($rootScope) {
        const ctrl = this;
        ctrl.actions = [];

        $rootScope.$on('enableFab', function (event, actions) {
            if (!angular.isArray(actions)) {
                console.error('Cleep cl-app-fab: Actions parameter must be an array');
                return;
            }
            ctrl.actions.splice(0, ctrl.actions.length);
            ctrl.actions = actions;
        });

        $rootScope.$on('$routeChangeSuccess', function() {
            ctrl.actions.splice(0, ctrl.actions.length);
        });

        ctrl.onClick = (action) => {
            (action.callback || angular.noop)();
        };
    }
});

angular.module('Cleep').service('cleepLoadingBarService', ['$timeout', function($timeout) {
    var self = this;
    self.started = false;
    self.status = 0;
    self.completeTimeout = null;
    self.incTimeout = null;
    self.autoIncrement = true;

    self.start = function() {
        $timeout.cancel(self.completeTieout);

        // do not continually broadcast the started event:
        if (self.started) {
            return;
        }
        self.started = true;
        self.set(0);
    };

    self.set = function(n) {
        if (!self.started) {
            return;
        }

        self.status = n;

        // increment loadingbar to give the illusion that there is always
        // progress but make sure to cancel the previous timeouts so we don't
        // have multiple incs running at the same time.
        if (self.autoIncrement) {
            $timeout.cancel(self.incTimeout);
            self.incTimeout = $timeout(function() {
                self.inc();
            }, 250);
        }
    };

    self.inc = function() {
        if (self.status >= 1) {
            return;
        }

        var rnd = 0;
        var stat = self.status;
        if (stat >= 0 && stat < 0.25) {
            // Start out between 3 - 6% increments
            rnd = (Math.random() * (5 - 3 + 1) + 3) / 100;
        } else if (stat >= 0.25 && stat < 0.65) {
            // increment between 0 - 3%
            rnd = (Math.random() * 3) / 100;
        } else if (stat >= 0.65 && stat < 0.9) {
            // increment between 0 - 2%
            rnd = (Math.random() * 2) / 100;
        } else if (stat >= 0.9 && stat < 0.99) {
            // finally, increment it .5 %
            rnd = 0.005;
        } else {
            // after 99%, don't increment:
            rnd = 0;
        }
        self.set(self.status  + rnd);
    };

    self.getStatus = function() {
        return self.status;
    };

    self.completeAnimation = function() {
        self.status = 0;
        self.started = false;
    };

    self.complete = function() {
        self.set(1);
    };
}]).config(['$httpProvider', function($httpProvider) {
    $httpProvider.interceptors.push(['$q', '$cacheFactory', '$timeout', 'cleepLoadingBarService',
        function($q, $cacheFactory, $timeout, cleepLoadingBarService) {
            // The total number of requests made
            var reqsTotal = 0;
            // The number of requests completed (either successfully or not)
            var reqsCompleted = 0;
            // The amount of time spent fetching before showing the loading bar
            var latencyThreshold = 500; //TODO cfpLoadingBar.latencyThreshold;
            // $timeout handle for latencyThreshold
            var startTimeout;

            /**
             * calls cfpLoadingBar.complete() which removes the loading bar from the DOM.
             */
            function setComplete() {
                $timeout.cancel(startTimeout);
                cleepLoadingBarService.complete();
                reqsCompleted = 0;
                reqsTotal = 0;
            };

            /**
             * Determine if the response has already been cached
             * @param  {Object}  config the config option from the request
             * @return {Boolean} retrns true if cached, otherwise false
             */
            function isCached(config) {
                var cache;
                var defaultCache = $cacheFactory.get('$http');
                var defaults = $httpProvider.defaults;
        
                // Choose the proper cache source. Borrowed from angular: $http service
                if ((config.cache || defaults.cache) && config.cache !== false && (config.method === 'GET' || config.method === 'JSONP')) {
                    cache = angular.isObject(config.cache) ? config.cache : angular.isObject(defaults.cache) ? defaults.cache : defaultCache;
                }

                var cached = cache !== undefined ? cache.get(config.url) !== undefined : false;
                if (config.cached !== undefined && cached !== config.cached) {
                    return config.cached;
                }

                config.cached = cached;
                return cached;
            };

            return {
                'request': function(config) {
                    var disabled = false;
                    if (config.config) {
                        disabled = config.config.ignoreLoadingBar;
                    }
                    if (!disabled && !isCached(config)) {
                        if (reqsTotal === 0) {
                            startTimeout = $timeout(function() {
                                cleepLoadingBarService.start();
                            }, 250);
                        }
                        reqsTotal++;
                        cleepLoadingBarService.set(reqsCompleted / reqsTotal);
                    }
                    return config;
                },
                'response': function(response) {
                    if (!response || !response.config) {
                        return response;
                    }
    
                    var disabled = false;
                    if (response.config) {
                        disabled = response.config.ignoreLoadingBar;
                    }
                    if (!disabled && !isCached(response.config)) {
                        reqsCompleted++;
                        if (reqsCompleted >= reqsTotal) {
                            setComplete();
                        } else {
                            cleepLoadingBarService.set(reqsCompleted / reqsTotal);
                        }
                    }
                    return response;
                },
                'responseError': function(rejection) {
                    if (!rejection || !rejection.config) {
                        return $q.reject(rejection);
                    }

                    var disabled = false;
                    if (rejection.config) {
                        disabled = rejection.config.ignoreLoadingBar;
                    }
                    if (!disabled && !isCached(rejection.config)) {
                        reqsCompleted++;
                        if (reqsCompleted >= reqsTotal) {
                            setComplete();
                        } else {
                            cleepLoadingBarService.set(reqsCompleted / reqsTotal);
                        }
                    }

                    return $q.reject(rejection);
                }
            };
        }])
}]).component('clLoadingBar', {
    template: `
    <div>
        <md-progress-linear ng-if="$ctrl.status<100" class="md-accent" md-mode="determinate" value="{{ $ctrl.status }}"></md-progress-linear>
        <md-progress-linear ng-if="$ctrl.status==100" md-mode="determinate" value="100"></md-progress-linear>
    </div>
    `,
    controller: function($scope, cleepLoadingBarService) {
        const ctrl = this;
        ctrl.status = 0;

        $scope.$watch(function() {
            return cleepLoadingBarService ? cleepLoadingBarService.status : 0;
        }, function(newStatus) {
            ctrl.status = newStatus * 100;
        });
    }
});

/**
 * Upload file component.
 * 
 * Usage: <cl-app-upload cl-on-select="ctrl.onSelect(file)"></cl-app-upload>
 * 
 * ctrl.onSelect = function(file) {
 *   rpcService.upload('<your app command>','<your app name>', file, <more data to send with command>)
 *     .then(function(<command result>) {
 *       // upload successful
 *     }, function(<error message>) {
 *       // upload failed
 *     });
 * };
 */
angular.module('Cleep').directive('clAppUpload', ['rpcService', function(rpcService) {
    var uploadFileLink = function(scope, element) {
        var input = $(element[0].querySelector('#fileInput'));
        var button = $(element[0].querySelector('#uploadButton'));
        var textInput = $(element[0].querySelector('#textInput'));

        scope.btnLabel = scope.clBtnLabel || 'Select file';
        scope.btnStyle = scope.clBtnStyle || 'md-raised md-primary';
        scope.btnIcon = scope.clBtnIcon || 'upload';

        // bind file input event to input and button
        if (input.length && button.length && textInput.length) {
            button.click(function (e) {
                input.click();
            });
            textInput.click(function (e) {
                input.click();
            });
        }

        // define event
        input.on('change', function (e) {
            if (rpcService._uploading === false) {
                var files = e.target.files;
                if (files[0]) {
                    scope.filename = files[0].name;
                    scope.clOnSelect({ file: files[0] });
                } else {
                    scope.filename = null;
                }
                scope.$apply();
            }
        });

        // handle end of upload to reset directive content
        scope.$watch(function() {
            return rpcService._uploading;
        }, function(newVal, oldVal) {
            if (newVal === false && oldVal === true) {
                input.val('');
                textInput.val('');
                scope.filename = null;
            }
        });
    };

    return {
        restrict: 'E',
        template: `
        <input id="fileInput" type="file" class="ng-hide">
        <md-button id="uploadButton" ng-class="btnStyle" ng-disabled="clDisabled">
            <cl-icon cl-icon="{{ btnIcon }}"></cl-icon>
            {{ btnLabel }}
        </md-button>
        <md-input-container md-no-float class="no-margin no-error-spacer" ng-show="clPlaceholder">
            <input id="textInput" ng-model="filename" type="text" placeholder="{{ clPlaceholder }}" ng-readonly="true">
        </md-input-container>
        `,
        scope: {
            clOnSelect: '&',
            clBtnLabel: '@?',
            clBtnIcon: '@?',
            clBtnStyle: '@?',
            clPlaceholder: '@?',
            clDisabled: '<?',
        },
        link: uploadFileLink
    };
}]);

angular.module('Cleep').service('cleepToolbarService', function() {
    var self = this;
    self.dashboardButton = {
        icon: 'view-dashboard',
        href: '#!dashboard',
        label: 'Dashboard',
    };
    self.appsButton = {
        icon: 'apps',
        href: '#!modules',
        label: 'Apps',
    };
    self.buttons = [self.dashboardButton, self.appsButton];

    self.__getId = function() {
         return '' + Math.random().toString(36).substring(2, 11);
    };

    self.addButton = function(label, icon, click, color) {
        if (!color) {
            color = 'md-primary';
        }

        const id = self.__getId();
        self.buttons.unshift({
            id,
            label,
            icon,
            click,
            color,
        });

        return id;
    };

    self.removeButton = function(id) {
        for (var i=0; i < self.buttons.length; i++) {
            if (self.buttons[i].id === id) {
                self.buttons.splice(i, 1);
                return true;
            }
        }

        // button not found
        return false;
    };
}).component('clToolbar', {
    template: `
    <md-button ng-repeat="btn in $ctrl.toolbar.buttons" hide="" show-gt-xs="" ng-href="{{ btn.href }}" ng-click="$ctrl.onToolbarClick(btn)" ng-class="['md-raised', btn.color]">
        <cl-icon cl-icon="{{ btn.icon }}"></cl-icon>
        {{ btn.label }}
    </md-button>
    <md-button ng-repeat="btn in $ctrl.toolbar.buttons" hide-gt-xs="" ng-href="{{ btn.href }}" ng-click="$ctrl.onToolbarClick(btn)" ng-class="['md-raised', 'cl-button-sm', btn.color]">
        <cl-icon cl-icon="{{ btn.icon }}"></cl-icon>
    </md-button>
    `,
    controller: function(cleepToolbarService) {
        const ctrl = this;
        ctrl.toolbar = cleepToolbarService;

        ctrl.onToolbarClick = function(button) {
            if (button.href) {
                return;
            }
    
            if (angular.isFunction(button.click)) {
                button.click();
            }
        };
    }
});

