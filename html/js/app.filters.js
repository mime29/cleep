/*global angular*/
/**
 * Application filters definitions
 */

var Cleep = angular.module('Cleep');

/**
 * Capitalize filter
 * @source http://stackoverflow.com/a/30207330
 */
Cleep.filter('capitalize', function() {
    return function(str) {
        return (!!str) ? str.charAt(0).toUpperCase() + str.substring(1).toLowerCase() : '';
    };
});

/**
 * Service name filter
 */
Cleep.filter('serviceName', function() {
    return function(str) {
        var tmp = str.replace('Service','');
        return (!!tmp) ? tmp.charAt(0).toUpperCase() + tmp.substring(1).toLowerCase() : '';
    };
});

/**
 * Device type filter
 */
Cleep.filter('deviceType', function($filter) {
    return function(devices, type) {
        if (type) {
            return $filter("filter")(devices, function(device) {
                return device.__type === type;
            });
        }
    };
});

/**
 * Device module filter
 */
Cleep.filter('filterDeviceByModule', function($filter) {
    return function(devices, module) {
        if (module) {
            return $filter("filter")(devices, function(device) {
                return device.module === module;
            });
        }
    };
});

/**
 * Timestamp to human readable string
 */
Cleep.filter('hrDatetime', function($filter) {
    return function(ts, shortYear) {
        if (angular.isUndefined(ts) || !ts) {
            return '-';
        }
        if (angular.isUndefined(shortYear)) {
            return moment.unix(ts).format('DD/MM/YYYY HH:mm:ss');
        }
        return moment.unix(ts).format('DD/MM/YY HH:mm:ss');
    };
});

/**
 * Time to human readable string
 */
Cleep.filter('hrTime', function($filter) {
    return function(ts, withSeconds) {
        if (angular.isUndefined(ts) || !ts) {
            return '-';
        }
        if (!angular.isUndefined(withSeconds)) {
            return moment.unix(ts).format('HH:mm:ss');
        }
        return moment.unix(ts).format('HH:mm');
    };
});

/**
 * Timestamp in milliseconds to human readable string
 */
Cleep.filter('hrMilliseconds', function($filter) {
    return function(ts) {
        if (angular.isUndefined(ts) || !ts) {
            return '-';
        }
        return moment.unix(ts).format('HH:mm:ss.SSS');
    };
});

/**
 * Temperature to string (with unit)
 */
Cleep.filter('hrTemperature', function($filter) {
    return function(temperature, unit) {
        result = '';

        if (angular.isUndefined(temperature) || temperature===null) {
            result = '-';
        } else {
            result = Number(temperature).toFixed(1);
        }

        if (angular.isUndefined(unit) || unit===null) {
            result += '?';
        } else if (unit == 'celsius') {
            result += '°C';
        } else if (unit == 'fahrenheit') {
            result += '°F';
        } else {
            result += '?';
        }

        return result;
    };
});

/**
 * Return graph dialog title
 */
Cleep.filter('graphDialogTitle', function($filter) {
    return function(device) {
        if (angular.isUndefined(device) || device===null) {
            return 'Sensor graph';
        }
        result = device.type + ' chart of ' + device.name;
        return result.firstUpperCase();
    };
});

/**
 * Return string lowered with first char in upper case
 */
Cleep.filter('firstUpper', function($filter) {
    return function(string) {
        if (angular.isUndefined(string) || string===null) {
            return '';
        }
        return string.firstUpperCase();
    };
});

/**
 * Order specified object by member key
 */
Cleep.filter('orderObjByKey', function() {
    return function(items, field, reverse) {
        if (!angular.isObject(items)) {
            return items;
        }
        var filtered = Object.keys(items).sort().reduce(function(a,v) {a[v] = items[v]; return a;}, {});
        if (reverse) {
            filtered.reverse();
        }
        return filtered;
    };
});

/**
 * Add leading zero
 */
Cleep.filter('padzero', function($filter) {
    return function(value, length, max) {
        return ('0'.repeat(max || 2)+value).slice(-length || -2);
    };
});

