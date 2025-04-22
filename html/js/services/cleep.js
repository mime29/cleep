/*global angular*/

/**
 * Cleep services
 * Handles :
 *  - installed modules: module and module helpers (reload config, get config...)
 *  - devices: all devices and devices helpers (reload devices)
 */
angular
.module('Cleep')
.service('cleepService', ['$injector', '$q', 'toastService', 'rpcService', '$http', '$ocLazyLoad', '$templateCache', '$rootScope',
function($injector, $q, toast, rpcService, $http, $ocLazyLoad, $templateCache, $rootScope) {

    const self = this;
    self.__deferredModules = $q.defer();
    self.__deferredEvents = $q.defer();
    self.__deferredRenderers = $q.defer();
    self.__deferredDrivers = $q.defer();
    self.devices = [];
    self.modules = {};
    self.installableModules = {};
    self.modulesUpdates = {};
    self.renderers = {};
    self.events = {};
    self.drivers = {};
    self.modulesPath = 'js/modules/';
    self.widgetConfigs = {};

    /**
     * Load Cleep config
     */
    self.loadConfig = function() {
        let config;

        return rpcService.getConfig()
            .then(function(resp) {
                config = resp.data;
                return self.refreshModulesUpdates();
            })
            .then(function() {
                return self._setModules(config.modules);
            })  
            .then(function() {
                // set other stuff
                self._setDevices(config.devices);
                self._setRenderers(config.renderers);
                self._setEvents(config.events);
                self._setDrivers(config.drivers);

                // load installable modules if necessary
                if(Object.keys(self.installableModules).length>0) {
                    return self.getInstallableModules();
                } else {
                    return Promise.resolve(null);
                }
            })
            .then(function(installableModules) {
                if(installableModules) {
                    self.installableModules = installableModules;
                }
            });
    };

    /**
     * Build list of system files
     * @param module: module name
     * @param desc: description content file (json)
     * @return object { js:[], html:[] }
     */
    self.__getModuleGlobalFiles = function(module, desc) {
        const files = {
            'js': [],
            'html': [],
            'css': []
        };

        if (!desc || !desc.global) {
            return files;
        }

        // get global files
        if (desc.global && desc.global.js) {
            for (const globalJs of desc.global.js) {
                files.js.push(self.modulesPath + module + '/' + globalJs);
            }
        }
        if (desc.global && desc.global.html) {
            for (const globalHtml of desc.global.html) {
                files.html.push(self.modulesPath + module + '/' + globalHtml);
            }
        }
        if (desc.global && desc.global.css) {
            for (const globalCss of desc.global.css) {
                files.css.push(self.modulesPath + module + '/' + globalCss);
            }
        }

        return files;
    };

    /**
     * Load js files
     * Use oclazyloader to inject automatically angular stuff
     * @param jsFiles: list of js files (with full path)
     * @return promise
     */
    self.__loadJsFiles = function(jsFiles) {
        return $ocLazyLoad.load({
            'cache': false,
            'reconfig': true,
            'rerun': true,
            'serie': true,
            'files': jsFiles
        });
    };

    /**
     * Load css files
     * Use oclazyloader to inject automatically css
     * @param cssFiles: list of css files (with full path)
     * @return promise
     */
    self.__loadCssFiles = function(cssFiles) {
        return $ocLazyLoad.load(cssFiles, {
            cache: false
        });
    };

    /**
     * Load html files
     * Html are considerated as templates and saved in angular templateCache for easier usage
     * @param modulePath: module path
     * @param htmlFiles: list of html files (with full path)
     * @return promise
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
                    return $q.resolve();
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
     * Convert to camelcase specified string (with dot)
     */
    self.__camelize = function(str) {
        return str.replace(/^[_.\- ]+/, '')
                .toLowerCase()
                .replace(/[_.\- ]+(\w|$)/g, (m, p1) => p1.toUpperCase());
    };

    /**
     * Load module
     * @return promise
     */
    self.__loadModule = function(module) {
        const modulePath = self.modulesPath + module + '/';
        const url = modulePath + 'desc.json';
        let desc = null;
        const d = $q.defer();
        let files = null;

        // do not load data of modules with pending status
        if (self.modulesUpdates[module] && self.modulesUpdates[module].pending) {
            return;
        }

        // load desc.json file from module folder
        $http.get(url)
            .then(function(resp) {
                // save desc content
                self.modules[module].desc = resp.data;

                // set module icon
                self.modules[module].icon = resp.data?.icon ?? 'bookmark';

                // store widget configs
                for (const [deviceType, config] of Object.entries(resp.data.widgets || {})) {
                    self.__storeWidgetConfig(deviceType, config);
                }

                // module "has config" flag
                self.modules[module].hasConfig = Object.keys(resp.data.config).length !== 0;

                // load module global objects (components, widgets and services)
                files = self.__getModuleGlobalFiles(module, resp.data);
                if (files.js.length === 0 && files.html.length === 0) {
                    // no file to lazyload, stop chain here
                    return $q.reject('stop-chain');
                };

                // load css files asynchronously (no further process needed)
                if (files.css.length > 0) {
                    self.__loadCssFiles(files.css);
                }

                // load html files
                return self.__loadHtmlFiles(modulePath, files.html);

            }, function(err) {
                // save empty desc for module
                self.modules[module].desc = {};

                // and reject promise
                console.error('Error occured loading "' + module + '" description file', err);

                // reject final promise
                return $q.reject('stop-chain');
            })
            .then(function(resp) {
                // load js files
                return self.__loadJsFiles(files.js);

            }, function(err) {
                if (err !== 'stop-chain') {
                    // error occured during html or css files loading
                    console.error('Error loading modules html files:', err);
                } else {
                    return $q.reject('stop-chain');
                }
            })
            .then(function() {
                // force getting service from injector to make them executed as soon as possible
                for (const fileJs of files.js) {
                    if (fileJs.indexOf('service') >= 0) {
                        // guess service name from filename
                        serviceName = fileJs.replace(/^.*[\\\/]/, '');
                        serviceName = serviceName.replace('.js', '');
                        serviceName = self.__camelize(serviceName);

                        // make sure
                        if ($injector.has(serviceName)) {
                            $injector.get(serviceName, function(err) {
                                console.error('Error occured during service loading:', err)
                            });
                        }
                    }
                }

            }, function(err) {
                if (err != 'stop-chain') {
                    // error occured during js files loading
                    console.error('Error loading modules js files:', err);
                } else {
                    return $q.reject('stop-chain');
                }
            })
            .then(function() {
                // all chain was good
                d.resolve();
            },
            function(err) {
                // error occured during chain but resolve chain otherwise devices can be loaded properly
                d.resolve();
            });

        return d.promise;
    };

    /**
     * Return module description (desc.json file content)
     * @return promise<json|null>
     */
    self.getModuleDescription = function(module) {
        const deferred = $q.defer();

        if (self.__deferredModules === null) {
            // module config already loaded, resolve it if available
            if (self.modules[module]) {
                deferred.resolve(self.modules[module].desc);
            } else {
                console.error('Unable to get description of unknown module "' + module + '"');
                deferred.reject(null);
            }
        }
        else {
            // module not loaded, wait for it
            self.__deferredModules.promise
                .then(function() {
                    if (self.modules[module]) {
                        deferred.resolve(self.modules[module].desc);
                    } else {
                        deferred.reject('Module "' + module + '" does not exist');
                    }
                }, function() {
                    deferred.reject(null);
                });
        }

        return deferred.promise;
    };

    /**
     * Set modules configurations as returned by rpcserver
     * Internal usage, do not use
     */
    self._setModules = function(modules) {
        // save modules
        self.modules = modules;

        // load description for each local modules
        const promises = [];
        for (const module of Object.values(self.modules)) {
            if (module.installed && module.started || module.library) {
                promises.push(self.__loadModule(module.name));
            }
        }

        // resolve deferred once all promises terminated
        // TODO sequentially chain promises https://stackoverflow.com/a/43543665 or https://stackoverflow.com/a/24262233
        // $q.all executes final statement as soon as one of promises is rejected
        return $q.all(promises)
            .then(function(resp) {
            }, function(err) {
                // necessary to avoid rejection warning
            })
            .finally(function() {
                // no deferred during reboot/restart, handle this case
                if (self.__deferredModules) {
                    self.__deferredModules.resolve();
                    self.__deferredModules = null;
                }
            });
    };

    /**
     * Get specified module configuration
     * @param module: module name to return configuration
     * @return promise: promise is resolved when configuration is loaded
     */
    self.getModuleConfig = function(module) {
        const deferred = $q.defer();

        if (self.__deferredModules === null) {
            // module config already loaded, resolve it if available
            if (self.modules[module]) {
                deferred.resolve(self.modules[module].config);
            } else {
                console.error('Specified module "' + module + '" has no configuration');
                deferred.reject();
            }
        } else {
            // module not loaded, wait for it
            self.__deferredModules.promise
                .then(function() {
                    deferred.resolve(self.modules[module].config);
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
    };

    /**
     * Reload configuration of specified module
     * @param module: module name
     * @return promise
     */
    self.reloadModuleConfig = function(module) {
        const deferred = $q.defer();

        if (self.modules[module]) {
            rpcService.sendCommand('get_module_config', module, null, 30)
                .then(function(resp) {
                    if (resp.error === false) {
                        // save new config
                        self.modules[module].config = resp.data;
                        deferred.resolve(resp.data);
                    } else {
                        console.error(resp.message);
                        toast.error(resp.message);
                        deferred.reject(resp.message);
                    }
                }, function(err) {
                    // error occured
                    toast.error('Unable to reload module "' + module + '" configuration');
                    console.error('Unable to reload module "' + module + '" configuration', err);
                    deferred.reject(err);
                });
        } else {
            console.error('Specified module "' + module + '" has no configuration');
            deferred.reject('module has no config');
        }

        return deferred.promise;
    };

    /**
     * Get list of installable modules
     */
    self.getInstallableModules = function(forceRefresh=false) {
        const deferred = $q.defer();

        if (Object.keys(self.installableModules).length > 0 && !forceRefresh) {
            deferred.resolve(self.installableModules);
        } else {
            // installable modules not loaded, load it
            rpcService.getModules(true)
                .then(function(resp) {
                    self.installableModules = resp.data;
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
    };

    /**
     * Refresh modules updates infos
     * Use cleepService.modulesUpdates to follow changes
     */
    self.refreshModulesUpdates = function() {
        return rpcService.sendCommand('get_modules_updates', 'update')
            .then(function(resp) {
                if(!resp.error) {
                    self.modulesUpdates = resp.data;
                }
            });
    };

    /**
     * Set devices
     * Prepare dashboard widgets and init device using associated module
     */
    self._setDevices = function(devices) {
        const newDevices = [];
        for (module in devices) {
            // add specific ui stuff
            for (const uuid in devices[module]) {
                // add module which handles this device
                devices[module][uuid].module = module;

                // update widget hidden status
                const hidden = self.modules[module].library ? true : Boolean(devices[module][uuid].hidden);
                devices[module][uuid].hidden = hidden;
            }

            // store device
            for (const uuid in devices[module]) {
                newDevices.push(devices[module][uuid]);
            }
        }

        self.devices = newDevices;
    };

    /**
     * Reload devices
     * Call getDevices command again and set devices
     */
    self.reloadDevices = function() {
        const deferred = $q.defer();

        rpcService.getDevices()
            .then(function(resp) {
                self._setDevices(resp.data);
                deferred.resolve(self.devices);
            }, function() {
                deferred.reject();
            });
        
        return deferred.promise;
    };

    /**
     * Return module devices
     */
    self.getModuleDevices = function(module) {
        return self.devices.filter(device => device.module === module);
    };

    /**
     * Set renderers
     * Just set renderers list
     */
    self._setRenderers = function(renderers) {
        self.renderers = renderers;
        // no deferred during reboot/restart, handle this case
        if (self.__deferredRenderers) {
            self.__deferredRenderers.resolve();
            self.__deferredRenderers = null;
        }
    };

    /**
     * Get renderers
     * @return promise
     */
    self.getRenderers = function() {
        const deferred = $q.defer();

        if (self.__deferredRenderers === null) {
            // renderers already loaded, return collection
            deferred.resolve(self.renderers);
        } else {
            self.__deferredRenderers.promise
                .then(function() {
                    deferred.resolve(self.renderers);
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
    };

    /**
     * Set events
     * Just set events list
     */
    self._setEvents = function(events) {
        self.events = events;
        // no deferred during reboot/restart, handle this case
        if (self.__deferredEvents) {
            self.__deferredEvents.resolve();
            self.__deferredEvents = null;
        }
    };

    /**
     * Get events
     * @return promise
     */
    self.getEvents = function() {
        const deferred = $q.defer();

        if (self.__deferredEvents === null) {
            // events already loaded, return collection
            deferred.resolve(self.events);
        } else {
            self.__deferredEvents.promise
                .then(function() {
                    deferred.resolve(self.events);
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
    };

    /**
     * Set drivers
     * Just set drivers list
     */
    self._setDrivers = function(drivers) {
        self.drivers = drivers;
        // no deferred during reboot/restart, handle this case
        if (self.__deferredDrivers) {
            self.__deferredDrivers.resolve();
            self.__deferredDrivers = null;
        }
    };

    /**
     * Get drivers
     * @return promise
     */
    self.getDrivers = function() {
        const deferred = $q.defer();

        if (self.__deferredDrivers === null) {
            // drivers already loaded, return collection
            deferred.resolve(self.drivers);
        } else {
            self.__deferredDrivers.promise
                .then(function() {
                    deferred.resolve(self.drivers);
                }, function() {
                    deferred.reject();
                });
        }

        return deferred.promise;
    };

    /**
     * Reload drivers
     * Call getDrivers command again and set drivers
     */
    self.reloadDrivers = function() {
        const deferred = $q.defer();

        rpcService.getDrivers()
            .then(function(resp) {
                self._setDrivers(resp.data);
                deferred.resolve(self.drivers);
            }, function() {
                deferred.reject();
            });
        
        return deferred.promise;
    };

    /**
     * Check if specified application is installed
     * @param app: application name (aka module name)
     * @return true if module is loaded, false otherwise
     */
    self.isAppInstalled = function(app) {
        for (const name in self.modules) {
            if (name === app && self.modules[name].installed) {
                return true;
            }
        }
        return false;
    };

    /**
     * Returns renderers of specified type
     */
    self.getRenderersOfType = function(type) {
        if (self.renderers[type]) {
            return self.renderers[type];
        }

        return {};
    };

    /** 
     * Get modules debug
     */
    self.getModulesDebug = function() {
        return rpcService.sendCommand('get_modules_debug', 'inventory', null, 20);
    };

    /**
     * Reboot device
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.reboot = function() {
        if (delay === null || delay === undefined) {
            delay = 0;
        }
        return rpcService.sendCommand('reboot_device', 'system', {'delay': delay});
    };

    /**
     * Poweroff device
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.poweroff = function() {
        if (delay === null || delay === undefined) {
            delay = 0;
        }
        return rpcService.sendCommand('poweroff_device', 'system', {'delay': delay});
    };

    /**
     * Restart Cleep
     * This function calls system module function to avoid adhesion of system service from angular app
     */
    self.restart = function(delay) {
        if (delay === null || delay === undefined) {
            delay = 0;
        }
        return rpcService.sendCommand('restart_cleep', 'system', {'delay': delay});
    };

    /**
     * Install module
     * This function calls system module function to avoid adhesion of update service from angular app
     */
    self.installModule = function(module) {
        return rpcService.sendCommand('install_module', 'update', {
            'module_name': module
        });
    };

    /**
     * Uninstall module
     * This function calls system module function to avoid adhesion of update service from angular app
     */
    self.uninstallModule = function(module) {
        return rpcService.sendCommand('uninstall_module', 'update', {
            'module_name': module
        });
    };

    /**
     * Force uninstall module
     * This function calls system module function to avoid adhesion of update service from angular app
     */
    self.forceUninstallModule = function(module) {
        return rpcService.sendCommand('uninstall_module', 'update', {
            'module_name': module,
            'force':true
        });
    };

    /**
     * Update module
     * This function calls system module function to avoid adhesion of update service from angular app
     */
    self.updateModule = function(module) {
        return rpcService.sendCommand('update_module', 'update', {
            'module_name': module
        });
    };

    /**
     * Catch apps updated event
     */
    $rootScope.$on('core.apps.updated', function(event, uuid, params) {
		// refresh list of installable apps
        rpcService.getModules(true)
            .then(function(resp) {
                self.installableModules = resp.data;
            }, function() {
                deferred.reject();
            });
    });

    self.__storeWidgetConfig = function(deviceType, config) {
        if (self.widgetConfigs[deviceType]) {
            // do not override existing template
            return;
        }

        self.widgetConfigs[deviceType] = config;
    };

    self.getWidgetConfig = function(deviceType) {
        const config = self.widgetConfigs[deviceType];
        return config && JSON.parse(JSON.stringify(config));
    };

    self.deviceRenderer = function (deviceType) {
        const directiveName = deviceType + 'Widget';
        const isAngularWidget = $injector.has(directiveName+'Directive');
        if (isAngularWidget) {
            return 'angular|' + directiveName;
        }

        const hasWidgetConf = self.getWidgetConfig(deviceType);
        if (Boolean(hasWidgetConf)) {
            return 'conf'
        }

        return undefined
    };
}]);

