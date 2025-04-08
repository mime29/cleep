/*global angular*/

angular
.module('Cleep')
.directive('dashboardDirective', ['$rootScope', 'cleepService',
function ($rootScope, cleepService) {
    var dashboardController = function() {
        var self = this;
        self.loading = true;
        self.devices = [];

        self.prepareDevices = function () {
            self.devices.splice(0, self.devices.length);
            for (const device of cleepService.devices) {
                if (device.hidden) {
                    continue;
                }
                device.__renderer = cleepService.deviceRenderer(device.type);
                if (device.__renderer) {
                    self.devices.push(device);
                } else {
                    console.warn('Device of type "' + device.type + '" has no renderable widget');
                }
            }
        };

        // prepare devices when config loaded
        $rootScope.$watchCollection(
            () => cleepService.devices,
            (devices) => {
                if (!devices?.length) {
                    return;
                }

                self.prepareDevices();
                self.loading = false;
            }
        );

        setTimeout(() => {
            self.loading = false;
        }, 10000);
    };

    return {
        templateUrl: 'js/app/dashboard/dashboard.html',
        replace: true,
        scope: true,
        controller: dashboardController,
        controllerAs: 'dashboardCtl'
    };
}]);

angular
.module('Cleep')
.directive('dashboardWidget', ['$compile', '$injector', 'cleepService',
function($compile, $injector, cleepService) {
    var dashboardWidgetLink = function(scope, element, attr) {
        cleepService.getModuleDescription(scope.device.module)
            .then((conf) => {
                const isAngularWidget = scope.device.__renderer.startsWith('angular');
                const directiveName = isAngularWidget ? scope.device.__renderer.split('|')[1] : '';
                const template = isAngularWidget ?
                    '<div ' + directiveName.toKebab() + ' device="device"></div>' :
                    '<widget-conf cl-device="device" cl-widget-conf="conf" cl-app-icon="' + conf.icon + '"></widget-conf>';

                if (!isAngularWidget) {
                    // apply custom widget footer if any
                    const widgetConf = cleepService.getWidgetConfig(scope.type);
                    const customFooter = conf.widgets?.[scope.type]?.footer
                    if (customFooter) {
                        widgetConf.footer = customFooter;
                    }
                    scope.conf = widgetConf;
                }

                const widget = $compile(template)(scope);
                element.append(widget);
            });
    };

    return {
        restrict: 'E',
        scope: {
            type: '@',
            device: '<'
        },
        link: dashboardWidgetLink
    }
}]);

