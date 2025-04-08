/*global angular*/

/**
 * RPC service is in charge :
 *  - to implements rpc commands (sendCommand, upload, download, ...),
 *  - to register client to rpc server 
 *  - and to handle connection loss (display an overlay with message)
 */
angular
.module('Cleep')
.service('rpcService', ['$http', '$q', 'toastService', '$base64', '$httpParamSerializer', '$window',
function($http, $q, toast, $base64, $httpParamSerializer, $window) {
    var self = this;
    self.uriCommand = window.location.protocol + '//' + window.location.host + '/command';
    self.uriUpload = window.location.protocol + '//' + window.location.host + '/upload';
    self.uriDownload = window.location.protocol + '//' + window.location.host + '/download';
    self.uriPoll = window.location.protocol + '//' + window.location.host + '/poll';
    self.uriRegisterPoll = window.location.protocol + '//' + window.location.host + '/registerpoll';
    self.uriModules = window.location.protocol + '//' + window.location.host + '/modules';
    self.uriDevices = window.location.protocol + '//' + window.location.host + '/devices';
    self.uriRenderers = window.location.protocol + '//' + window.location.host + '/renderers';
    self.uriDrivers = window.location.protocol + '//' + window.location.host + '/drivers';
    self.uriConfig = window.location.protocol + '//' + window.location.host + '/config';
    self.pollKey = null;
    self._uploading = false;
    self.invalidApplicationRegexp = /Invalid application ".*" \(not loaded or unknown\)/g;

    /**
     * send command
     * @param data: data to send
     * @param to: request destinated to specified module. If not specified
     *            message will be broadcasted to all modules
     * @param params: object of params to pass to command
     * @param timeout: specify command timeout (default is 3seconds)
     * @return promises
     */
    self.sendCommand = function(command, to, params, timeout) {
        var d = $q.defer();
        var data = {};

        // prepare data
        data.command = command;
        if (params!==undefined && params!==null) {
            data.params = params;
        } else {
            // no params
            data.params = {};
        }

        if (to!==undefined && to!==null) {
            // push command
            data.to = to;
        } else {
            // broadcast command
            data.to = null;
        }

        if (angular.isUndefined(timeout)) {
            data.timeout = null;
        } else {
            data.timeout = timeout;
        }

        $http({
            method: 'POST',
            url: self.uriCommand,
            data: data,
            responseType:'json'
        })
        .then(function(resp) {
            if (!self._handleRespErrors(resp, d)) {
                // display message if provided
                if (resp.data.message) {
                    toast.success(resp.data.message);
                }
                d.resolve(resp.data);
            }
        }, function(err) {
            console.error('Request failed: '+err);
            toast.error(err.statusText);
            d.reject(err.statusText);
        });

        return d.promise;
    };

    /**
     * Get loaded modules server side
     */
    self.getModules = function(installable) {
        var d = $q.defer();

        $http({
            method: 'POST',
            url: self.uriModules,
            data: {
                installable: installable===undefined ? false : installable
            },
            responseType: 'json'
        })
        .then(function(resp) {
            if (!self._handleRespErrors(resp, d)) {
                d.resolve(resp.data);
            }
        }, function(err) {
            console.error('Request failed: '+err);
            d.reject('request failed');
        });

        return d.promise;
    };

    /**
     * Get all devices
     */
    self.getDevices = function() {
        var d = $q.defer();

        $http({
            method: 'POST',
            url: self.uriDevices,
            responseType: 'json'
        })
        .then(function(resp) {
            if (!self._handleRespErrors(resp, d)) {
                d.resolve(resp.data);
            }
        }, function(err) {
            console.error('Request failed: '+err);
            d.reject('request failed');
        });

        return d.promise;
    };

    /**
     * Get all renderers
     */
    self.getRenderers = function() {
        var d = $q.defer();

        $http({
            method: 'POST',
            url: self.uriRenderers,
            responseType: 'json'
        })
        .then(function(resp) {
            if (!self._handleRespErrors(resp, d)) {
                d.resolve(resp.data);
            }
        }, function(err) {
            console.error('Request failed: '+err);
            d.reject('request failed');
        });

        return d.promise;
    };

    /**
     * Get all drivers
     */
    self.getDrivers = function() {
        var d = $q.defer();

        $http({
            method: 'POST',
            url: self.uriDrivers,
            responseType: 'json'
        })
        .then(function(resp) {
            if (!self._handleRespErrors(resp, d)) {
                d.resolve(resp.data);
            }
        }, function(err) {
            console.error('Request failed: '+err);
            deferred.reject('request failed');
        });

        return d.promise;
    };

    /**
     * Get config
     */
    self.getConfig = function() {
        var d = $q.defer();

        $http({
            method: 'POST',
            url: self.uriConfig,
            responseType: 'json'
        })
        .then(function(resp) {
            if (!self._handleRespErrors(resp, d)) {
                d.resolve(resp.data);
            }
        }, function(err) {
            console.error('Request failed: ' + err);
            d.reject('request failed');
        });

        return d.promise;
    };

    /**
     * Handle response errors
     * @param resp: request response (cleep RPC format)
     * @param promise: specify a promise to reject it
     * @return boolean: true if error was handled, false otherwise
     */
    self._handleRespErrors = function(resp, defer) {
        if (resp?.data?.error) {
            if (resp.data.message.match(self.invalidApplicationRegexp)) {
                // specific case with invalid app loaded, redirect to apps list
                $window.location.href = '#!/modules';
            }

            console.error('Request failed: ' + resp.data.message);
            toast.error(resp.data.message || 'No error message');
            if (defer) {
                defer.reject(resp.data.message || 'Request failed');
            }
            return true;
        }

        return false;
    };

    /**
     * Upload file
     * @param command: command that handles upload function
     * @param to: module that handles upload
     * @param file: file to upload (data from html form input type file)
     * @param data: more data to embed during upload
     * @return promise: success returns command data, failure returns error message
     */
    self.upload = function(command, to, file, data) {
        if (!file) {
            return;
        }

        // prepare data
        var formData = new FormData();
        formData.append('file', file);
        formData.append('filename', file.name);
        formData.append('to', to);
        formData.append('command', command);
        if (angular.isObject(data)) {
            // append extra parameters
            angular.forEach(data, function(value, key) {
                formData.append(key, value);
            });
        }

        // flag to reset upload directive
        self._uploading = true;

        // post data
        var deferred = $q.defer();
        $http.post(self.uriUpload, formData, {
            transformRequest: angular.identity,
            headers: {'Content-Type': undefined }
        }).then(function(resp) {
            if (resp && resp.data && typeof(resp.data.error)!=='undefined' && resp.data.error===false) {
                deferred.resolve(resp.data);
            } else if (resp && resp.data && typeof(resp.data.error)!=='undefined' && resp.data.error===true) {
                deferred.reject(resp.data.message);
                toast.error('Upload failed: ' + resp.data.message);
            } else {
                deferred.reject('Unknown error');
                toast.error('Upload failed: unknown error');
            }
        }, function(err) {
            toast.error('Upload failed: network error');
            deferred.reject(err);
        })
        .finally(function() {
            self._uploading = false;
        });

        return deferred.promise;
    };

    /**
     * Download file
     * Open new blank window and return specified file for download
     * @param command: command to download file (depends on module you want to perform download)
     * @param to: module to request a file download
     * @param params: parameters to command (typically a filename)
     */
    self.download = function(command, to, params) {
        if (angular.isUndefined(params)) {
            params = {};
        }
        params = angular.extend(params, {'to':to, 'command':command});
        var queryString = $httpParamSerializer(params);
        $window.open(self.uriDownload + '?' + queryString, '_blank');
    };

    /**
     * Poll
     */
    self.poll = function() {
        if (self.pollKey===null) {
            // not registered yet to server, get poll key
            return self.__registerPoll();
        } else {
            // already registered
            return self.__poll();
        }
    };

    /**
     * Poll
     */
    self.__poll = function() {
        var d = $q.defer();

        $http({
            method: 'POST',
            data: {'pollKey': self.pollKey},
            url: self.uriPoll,
            responseType:'json',
            config: {
                ignoreLoadingBar: true
            }
        })
        .then(function(resp) {
            if (resp && resp.data.error!==undefined && resp.data.error===true) {
                // error occured
                if (resp.data.message==='Client not registered') {
                    // reset poll key
                    self.pollKey = null;
                }
                d.reject(resp.message);
            } else {
                d.resolve(resp.data);
            }
        }, function(resp) {
            d.reject('Connection problem');
        });

        return d.promise;
    };

    /**
     * Register polling
     */
    self.__registerPoll = function() {
        var d = $q.defer();

        $http({
            method: 'POST',
            url: self.uriRegisterPoll,
            responseType: 'json'
        })
        .then(function(resp) {
            // save registration
            self.pollKey = resp.data.pollKey;
            d.resolve('registered');
        }, function(resp) {
            d.reject('Connection problem');
        });

        return d.promise;
    };
}]);

