/*global angular*/

/**
 * Configuration directive
 * Handle all module configuration
 */
angular
.module('Cleep')
.directive('moduleDirective', ['$q', 'cleepService', '$compile', '$timeout', '$routeParams', '$ocLazyLoad', '$templateCache', '$http',
function($q, cleepService, $compile, $timeout, $routeParams, $ocLazyLoad, $templateCache, $http) {

    const moduleController = ['$scope','$element', function($scope, $element) {
        const self = this;
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
            const url = self.modulesPath + module + '/';
            const files = {
                'html': [],
                'jscss': []
            };
            const types = ['js', 'css', 'html'];

            // check desc config
            if( !desc || !desc.config ) {
                return files;
            }

            // append files by types
            for (const j=0; j<types.length; j++) {
                if (desc.config[types[j]]) {
                    for (const i=0; i<desc.config[types[j]].length; i++) {
                        if (types[j]=='html') {
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
        self.__loadHtmlFiles = function(modulePath, htmlFiles) {
            const promises = [];
            const d = $q.defer();

            // fill templates promises
            for (const htmlFile of htmlFiles) {
                // load only missing templates
                const templateName = htmlFile.replace(modulePath, '').split('?')[0];
                if (!$templateCache.get(templateName)) {
                    promises.push($http.get(htmlFile));
                }
            }

            // and execute them
            $q.all(promises)
                .then(function(templates) {
                    if (!templates) {
                        return;
                    }

                    // cache templates
                    for (const template of templates.values()) {
                        const templateName = template.config?.url.replace(modulePath, '').split('?')[0];
                        $templateCache.put(templateName, template.data);
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
        self.init = function(module) {
            // save module name
            self.module = module;
            const modulePath = self.module + module + '/';
            let files;

            // load module description
            cleepService.getModuleDescription(module)
                .then(function(desc) {
                    files = self.__getConfigFilesToLoad(desc, module);

                    // load html templates first
                    return self.__loadHtmlFiles(modulePath, files.html);

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
                    const template = '<div ' + module + '-config-component=""></div>';
                    const component = $compile(template)($scope);
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

    const moduleLink = function(scope, element, attrs, controller) {
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
