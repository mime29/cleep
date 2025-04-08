/*global angular*/

angular
.module('Cleep')
.directive('pageDirective', ['$q', 'cleepService', '$compile', '$timeout', '$routeParams', '$ocLazyLoad', '$templateCache', '$http',
function($q, cleepService, $compile, $timeout, $routeParams, $ocLazyLoad, $templateCache, $http) {

    var pageController = ['$scope','$element', function($scope, $element) {
        var self = this;
        self.modulesPath = 'js/modules/';
        self.module = '';
        self.page = '';
        self.error = false;
        // custom settings that page can update
        self.title = null;
        self.tools = []; // must contains item with { label:string, click:function, icon:mdi icon string }

        /**
         * Configure toolbar
         * @param title (string): title to display on toolbar (near back button)
         * @param tools (array): array of tool. A tool is an object like:
         *      {
         *          label (string): button label,
         *          icon (string): button mdi icon,
         *          click (function): on click event
         *          tooltip (string): button tooltip
         *      }
         */
        self.setToolbar = function(title, tools) {
            self.title = title || '';
            if (tools) {
                self.tools = tools;
            }
        };

        self.onToolClick = function(tool) {
            if (tool.click) {
                tool.click();
            }
        };

        /**
         * Get list of custom page files to lazy load
         * @param desc: desc file content (json)
         * @param module: module name
         * @param page: page name
         */
        self.__getPageFilesToLoad = function(desc, module, page) {
            // init
            var url = self.modulesPath + module + '/';
            var files = {
                'html': [],
                'jscss': []
            };
            var types = ['js', 'css', 'html'];

            // check desc content
            const pageDesc = desc?.pages?.[self.page];
            if (!pageDesc) {
                self.error = true;
                return null;
            }

            for (const type of types) {
                if (pageDesc[type]) {
                    const typeFiles = [];
                    if (!Array.isArray(pageDesc[type])) {
                        typeFiles.push(pageDesc[type]);
                    } else {
                        typeFiles.push(...pageDesc[type]);
                    }

                    if (type === 'html') {
                        files.html.push(...typeFiles.map((file) => url + file));
                    } else {
                        files.jscss.push(...typeFiles.map((file) => url + file));
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
            for (var i=0; i<htmlFiles.length; i++) {
                // load only missing templates
                var templateName = htmlFiles[i].substring(htmlFiles[i].lastIndexOf('/')+1);
                if (!$templateCache.get(templateName)) {
                    promises.push($http.get(htmlFiles[i]));
                }
            }

            // and execute them
            $q.all(promises)
                .then(function(templates) {
                    // check if templates available
                    if (!templates) {
                        return;
                    }
    
                    // cache templates
                    for (var i=0; i<templates.length; i++) {
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
         * Init controller
         * @param module (string): module name
         * @param page (string): module page
         */
        self.init = function(module, page) {
            // save module name
            self.module = module;
            self.page = page;
            var files;

            // load module description
            cleepService.getModuleDescription(module)
                .then(function(desc) {
                    files = self.__getPageFilesToLoad(desc, module, page);
                    if (files === null) {
                        return $q.reject('Page "'+page+'" not found');
                    }

                    // load html templates first
                    return self.__loadHtmlFiles(files.html);

                }, function(err) {
                    console.error('Unable to get module "' + module + '" description');
                    return $q.reject('STOPCHAIN');
                })
                .then(function() {
                    // load js and css files
                    return self.__loadJsCssFiles(files.jscss);

                }, function(err) {
                    // remove rejection warning
                    if (err !== 'STOPCHAIN') {
                        console.error('error loading html files:', err);
                    }
                    return $q.reject('STOPCHAIN');
                })
                .then(function() {
                    // everything is loaded successfully, inject page directive
                    var template = '<div ' + page.toKebab() + '-page-directive=""></div>';
                    var directive = $compile(template)($scope);
                    $element.append(directive);

                }, function(err) {
                    if (err !== 'STOPCHAIN') {
                        console.error('Error loading module js/css files:', err);
                    }
                });
        };
    }];

    var pageLink = function(scope, element, attrs, controller) {
        controller.init($routeParams.name, $routeParams.page);
    };

    return {
        templateUrl: 'js/app/page/page.html',
        replace: true,
        controller: pageController,
        controllerAs: 'pageCtl',
        link: pageLink
    };
}]);
