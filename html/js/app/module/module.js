/*global angular*/

/**
 * Configuration directive
 * Handle all module configuration
 */
angular
.module('Cleep')
.directive('moduleDirective', ['$q', 'cleepService', '$compile', '$timeout', '$routeParams', '$ocLazyLoad', '$templateCache', '$http',
function($q, cleepService, $compile, $timeout, $routeParams, $ocLazyLoad, $templateCache, $http) {

    var moduleController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.modulesPath = 'js/modules/';
        self.module = '';
        self.label = '';
        self.moduleUrls = {};
        self.version = '';
        self.error = false;

        /**
         * Get list of config files to lazy load
         * @param desc: desc file content (json)
         * @param module: module name
         */
        self.__getConfigFilesToLoad = function(desc, module) {
            // init
            var url = self.modulesPath + module + '/';
            var files = {
                'html': [],
                'jscss': []
            };
            var types = ['js', 'css', 'html'];

            // check desc config
            if( !desc || !desc.config ) {
                return files;
            }

            // append files by types
            for( var j=0; j<types.length; j++ ) {
                if( desc.config[types[j]] ) {
                    for( var i=0; i<desc.config[types[j]].length; i++) {
                        if( types[j]=='html' ) {
                            files['html'].push(url + desc.config[types[j]][i]);
                        } else {
                            files['jscss'].push(url + desc.config[types[j]][i]);
                        }
                    }
                }
            }

            return files;
        };

        /**
         * Load js and css files
         * @param files: list of js files
         */
        self.__loadJsCssFiles = function(files) {
            // load js files using lazy loader
            return $ocLazyLoad.load({
                'cache': false,
                'reconfig': false,
                'rerun': false,
                'files': files
            });
        };

        /**
         * Load html files as templates
         * @param htmlFile: list of html files
         */
        self.__loadHtmlFiles = function(htmlFiles) {
            // init
            var promises = [];
            var d = $q.defer();

            // fill templates promises
            for( var i=0; i<htmlFiles.length; i++ ) {
                // load only missing templates
                var templateName = htmlFiles[i].substring(htmlFiles[i].lastIndexOf('/')+1);
                promises.push($http.get(htmlFiles[i]));
            }

            // and execute them
            $q.all(promises)
                .then(function(templates) {
                    // check if templates available
                    if( !templates ) {
                        return;
                    }

                    // cache templates
                    for( var i=0; i<templates.length; i++ ) {
                        var templateName = htmlFiles[i].substring(htmlFiles[i].lastIndexOf('/')+1);
                        $templateCache.put(templateName, templates[i].data);
                    }
                }, function(err) {
                    console.error('Error occured loading html files:', err);
                })
                .finally(function() {
                    d.resolve();
                });
    
            return d.promise;
        };

        /**
         * Open app infos menu
         */
        self.openAppInfos = function($mdMenu, ev) {
            $mdMenu.open(ev);
        };

        /**
         * Init controller
         */
        self.init = function(module)
        {
            // save module name
            self.module = module;
            var files;

            // load module description
            cleepService.getModuleDescription(module)
                .then(function(desc) {
                    files = self.__getConfigFilesToLoad(desc, module);

                    // load html templates first
                    return self.__loadHtmlFiles(files.html);

                }, function(err) {
                    self.error = true;
                    console.error('Unable to get module "' + module + '" description');
                    return $q.reject('STOPCHAIN');
                })
                .then(function() {
                    // load js and css files
                    return self.__loadJsCssFiles(files.jscss);
                }, function(err) {
                    // remove rejection warning
                    self.error = true;
                    if( err!=='STOPCHAIN' ) {
                        console.error('error loading html files:', err);
                    }
                    return $q.reject('STOPCHAIN');
                })
                .then(function() {
                    // everything is loaded successfully, inject module component
                    var template = '<div ' + module + '-config-component=""></div>';
                    var component = $compile(template)($scope);
                    $element.append(component);

                    // save usefull infos
                    self.moduleUrls = cleepService.modules[module].urls;
                    self.version = cleepService.modules[module].version;
                    self.label = cleepService.modules[module].label;

                }, function(err) {
                    self.error = true;
                    if( err!=='STOPCHAIN' ) {
                        console.error('Error loading module js/css files:', err);
                    }
                });
        };
    }];

    var moduleLink = function(scope, element, attrs, controller) {
        controller.init($routeParams.name);
    };

    return {
        templateUrl: 'js/app/module/module.html',
        replace: true,
        controller: moduleController,
        controllerAs: 'moduleCtl',
        link: moduleLink
    };
}]);
