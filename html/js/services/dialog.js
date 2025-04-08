/*global angular*/

/**
 * Dialog service
 * Used to open a material dialog
 */
angular
.module('Cleep')
.service('dialogService', ['$mdDialog', function($mdDialog) {
    var self = this;

    self.dialogController = ['$scope', '$mdDialog', function($scope, $mdDialog) {
        var self = this;
        self.cancel = function() {
            $mdDialog.cancel();
        };

        self.valid = function() {
            $mdDialog.hide();
        };
    }];

    /**
     * Open dialog
     * @param controller: controller object. Usually dialogService caller (object)
     * @param controllerAs: name of controller (string)
     * @param templateUrl: dialog content url (string)
     */
    self.open = function(options, controllerAs, templateUrl) {
        // extend specified controller with dialog function helpers
        var controller = angular.extend(self.dialogController, options || {});
        return $mdDialog.show({
            controller: controller,
            controllerAs: controllerAs,
            templateUrl: templateUrl,
            parent: angular.element(document.body),
            clickOutsideToClose: false,
        });
    };
}]);
