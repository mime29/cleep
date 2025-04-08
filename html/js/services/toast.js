/*global angular*/

angular
.module('Cleep')
.service('toastService', ['$mdToast', '$mdDialog',
function($mdToast, $mdDialog) {
    var self = this;

    /**
     * Error message
     * @param message: message to display
     * @param duration: message duration
     */
    self.error = function(message, duration) {
        self.__toast(message, duration || 6000, 'error');
    };

    /**
     * Warning message
     * @param message: message to display
     * @param duration: message duration
     */
    self.warning = function(message, duration) {
        self.__toast(message, duration || 3000, 'warning');
    };

    /**
     * Success message
     * @param message: message to display
     * @param duration: message duration
     */
    self.success = function(message, duration) {
        self.__toast(message, duration || 3000, 'success');
    };

    /**
     * Info message
     * @param message: message to display
     * @param duration: message duration
     */
    self.info = function(message, duration) {
        self.__toast(message, duration || 3000, 'info');
    };

    /**
     * Fatal message. Add link to open stack
     * @param message: message to display
     * @param cause: error cause
     * @param stack: exception stack trace
     */
    self.fatal = function(message, cause, stack, duration) {
        self.__toast(message, duration || 10000, 'fatal');
    };

    /**
     * Toast message (internal use)
     * @param message: message to display
     * @param duration: message duration
     * @param class_: bubble class (success, error, warning or info). If not specified setted to info
     */
    self.__toast = function(message, duration, class_) {
        $mdToast.show(
            $mdToast.simple()
                .textContent(message)
                .toastClass(class_)
                .position('bottom right')
                .hideDelay(duration)
        );
    };

    /**
     * Loading message. Add a spinner near message
     * @param message: message to display
     * @param class_: bubble class (success, error, warning or info). If not specified setted to info
     */
    self.loading = function(message, class_) {
        if( angular.isUndefined(class_) )
        {
            class_ = 'info';
        }

        $mdToast.show({
            template: '<md-toast><span class="md-toast-text">'+message+'</span><md-progress-circular md-mode="indeterminate" md-diameter="20" class="progress-circular-white"></md-progress-circular></md-toast>',
            position: 'bottom right',
            toastClass: class_,
            hideDelay: 0
        });
    };

    /**
     * Hide current toast message
     * Useful to hide loading message
     */
    self.hide = function() {
        $mdToast.hide();
    };
    self.close = function() {
        self.hide();
    };
}]);

