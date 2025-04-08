/*global angular*/
/**
 * Application modules configuration
 * This file configures:
 *  - router
 *  - theme
 *  - fonts provider
 */

var Cleep = angular.module('Cleep');
var currentTimestamp = Date.now();

/**
 * Routes configuration
 */
Cleep.config([
    '$routeProvider',
    '$locationProvider',
    function ($routeProvider, $locationProvider) {
        $locationProvider.hashPrefix('!');
        $routeProvider
            .when('/dashboard', {
                template: '<div dashboard-directive></div>',
            })
            .when('/modules', {
                template: '<div modules-directive></div>',
            })
            .when('/install', {
                template: '<div install-directive></div>',
            })
            .when('/module/:name', {
                template: '<div module-directive></div>',
            })
            .when('/module/:name/:page', {
                template: '<div page-directive></div>',
            })
            .otherwise({
                redirectTo: '/dashboard',
            });
    },
]);

/**
 * Disable aria warnings
 */
Cleep.config(function ($mdAriaProvider) {
    $mdAriaProvider.disableWarnings();
});

/**
 * Http interceptor to resolve cache problems
 */
Cleep.config(function ($templateRequestProvider) {
    $templateRequestProvider.httpOptions({ _isTemplate: true });
}).factory('noCacheInterceptor', function ($templateCache) {
        const NO_CACHE_REGEX = /(?:json|html|svg|jpg)/;
        return {
            request: function (config) {
                if (config._isTemplate) {
                    return config;
                }
                if (NO_CACHE_REGEX.test(config.url)) {
                    config.url = config.url + '?t=' + currentTimestamp;
                }
                return config;
            },
        };
    })
    .config(function ($httpProvider) {
        $httpProvider.interceptors.push('noCacheInterceptor');
    });

Cleep.factory('$exceptionHandler', [
    '$log',
    '$injector',
    function ($log, $injector) {
        const cache = {};
        const TIMEOUT = 2000; // 2 seconds

        return function myExceptionHandler(exception, cause) {
            $log.error(exception, cause);

            const toastService = $injector.get('toastService');
            const locationService = $injector.get('$location');

            if (typeof exception === 'string' && exception.startsWith('Possibly')) {
                // should be already handled by a service
                return;
            }
            if (!toastService || !locationService) {
                return;
            }

            if (locationService.url().startsWith('/module/')) {
                const appName = locationService.url().split('/').pop();
                const now = new Date().getTime();
                if (((cache[appName] || 0) + TIMEOUT) < now) {
                    cache[appName] = now;
                    toastService.fatal(`Error with ${appName} application`);
                }
            }
        };
    },
]);

/**
 * Theme configuration
 */
Cleep.config([
    '$mdThemingProvider',
    '$provide',
    function ($mdThemingProvider, $provide) {
        $mdThemingProvider
            .theme('default')
            .primaryPalette('blue-grey')
            .accentPalette('red')
            .backgroundPalette('grey');
        $mdThemingProvider
            .theme('dark')
            .dark();
        $mdThemingProvider.alwaysWatchTheme(true);

        $provide.value('themeProvider', $mdThemingProvider);

        /*$mdThemingProvider
        .theme('default')
        .primaryPalette('blue')
        .accentPalette('orange')
        .backgroundPalette('grey');
    $mdThemingProvider
        .theme('dark')
        .primaryPalette('blue')
        .accentPalette('orange')
        .backgroundPalette('grey')
        .dark();*/
    },
]);

/**
 * Font configuration
 * Disabled for now, ligatures are not supported by typicons
 */
/*Cleep.config(['$mdIconProvider', function($mdIconProvider) {
    $mdIconProvider
        .iconSet('typicons', 'fonts/typicons.svg', 24)
}]);*/

/**
 * Blockui configuration
 */
Cleep.config([
    'blockUIConfig',
    function (blockUIConfig) {
        tmpl = '<div class="block-ui-overlay"></div>';
        tmpl +=
            '<div layout="column" layout-align="center center" class="block-ui-message-container">';
        tmpl +=
            '  <md-card style="display: inline-block; text-align: left;" md-colors="::{backgroundColor: \'default-primary-100\'}">';
        tmpl += '    <md-card-title>';
        tmpl += '      <md-card-title-media>';
        tmpl += '        <div class="md-media-sm card-media" layout>';
        tmpl +=
            '          <cl-icon ng-if="state.icon!==undefined && state.icon!==null" cl-class="icon-xl" cl-icon="{{ state.icon }}"></cl-icon>';
        tmpl +=
            '          <md-progress-circular ng-if="state.spinner===undefined || state.spinner===true" md-mode="indeterminate" style="margin-top:14px; margin-left:10px;">';
        tmpl += '        </div>';
        tmpl += '      </md-card-title-media>';
        tmpl += '      <md-card-title-text>';
        tmpl += '        <span class="md-headline">{{state.message}}</span>';
        tmpl +=
            '        <span ng-if="state.submessage" class="md-subhead">{{state.submessage}}</span>';
        tmpl += '      </md-card-title-text>';
        tmpl += '    </md-card-title>';
        tmpl += '  </md-card>';
        tmpl += '</div>';
        blockUIConfig.template = tmpl;
        blockUIConfig.autoBlock = false;
    },
]);

/**
 * Lazyload configuration
 */
Cleep.config([
    '$ocLazyLoadProvider',
    function ($ocLazyLoadProvider) {
        $ocLazyLoadProvider.config({
            debug: false,
            events: false,
        });
    },
]);
