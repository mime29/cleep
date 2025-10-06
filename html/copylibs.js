var fs = require('fs');
var { exec } = require("child_process");
const path = require('path');

// unzip angularjs minified file
/*exec('cd "node_modules/angular/"; mv "angular.min.js.gzip" "angular.min.js.gz"; gunzip "angular.min.js.gz"',
    (error, stdout, stderr) => {
        if (error) throw error;
    }
);*/

// HOWTO
// Update package.json to update dependencies
// Launch npm install
// Run this script to get copy of node_modules/xxx dependencies in js/css/fonts Cleep html folder

var files = {
    // angularjs
    'node_modules/angular/angular.min.js': 'js/libs/angular.min.js',
    'node_modules/angular-messages/angular-messages.min.js': 'js/libs/angular-messages.min.js',
    'node_modules/angular-route/angular-route.min.js': 'js/libs/angular-route.min.js',
    'node_modules/angular-aria/angular-aria.min.js': 'js/libs/angular-aria.min.js',
    'node_modules/angular-animate/angular-animate.min.js': 'js/libs/angular-animate.min.js',
    'node_modules/angular-sanitize/angular-sanitize.min.js': 'js/libs/angular-sanitize.min.js',
    // angular material
    'node_modules/angular-material/angular-material.min.js': 'js/libs/angular-material.min.js',
    'node_modules/angular-material/angular-material.min.css': 'css/angular-material.min.css',
    // konami
    // FIXED BY TANG 'node_modules/angular-konami/angular-konami.min.js': 'js/libs/angular-konami.min.js',
    // daterangepicker
    'node_modules/angular-daterangepicker/js/angular-daterangepicker.min.js': 'js/libs/angular-daterangepicker.min.js',
    // blockui
    'node_modules/angular-block-ui/dist/angular-block-ui.min.js': 'js/libs/angular-block-ui.min.js',
    'node_modules/angular-block-ui/dist/angular-block-ui.min.css': 'css/angular-block-ui.min.css',
    // base64
    'node_modules/angular-base64/angular-base64.min.js': 'js/libs/angular-base64.min.js',
    // jquery
    'node_modules/jquery/dist/jquery.min.js': 'js/libs/jquery.min.js',
    // codemirror
    'node_modules/codemirror-minified/lib/codemirror.js': 'js/libs/codemirror.min.js',
    'node_modules/codemirror-minified/mode/python/python.js': 'js/libs/codemirror-python.min.js',
    // ABANDONED 'node_modules/ui-codemirror/src/ui-codemirror.js': 'js/libs/ui-codemirror.js',
    'node_modules/codemirror-minified/lib/codemirror.css': 'css/codemirror.min.css',
    // data-table
    'node_modules/angular-material-data-table/dist/md-data-table.min.js': 'js/libs/md-data-table.min.js',
    'node_modules/angular-material-data-table/dist/md-data-table.min.css': 'css/md-data-table.min.css',
    // moment
    'node_modules/moment/min/moment-with-locales.min.js': 'js/libs/moment.min.js',
    // lazyload
    'node_modules/oclazyload/dist/ocLazyLoad.min.js': 'js/libs/ocLazyLoad.min.js',
    // markdown https://github.com/Hypercubed/angular-marked
    'node_modules/angular-marked/dist/angular-marked.min.js': 'js/libs/angular-marked.min.js',
    'node_modules/marked/lib/marked.js': 'js/libs/marked.js',
    // ABADONNED badge https://github.com/jmouriz/angular-material-badge
    // REPLACED BY https://github.com/CleepDevice/angular-material-badge
    // 'node_modules/angular-material-badge/source/angular-material-badge.js': 'js/libs/angular-material-badge.js',
    // 'node_modules/angular-material-badge/source/angular-material-badge.css': 'css/angular-material-badge.css',
    // angularjs-gauge
    'node_modules/angularjs-gauge/dist/angularjs-gauge.min.js': 'js/libs/angularjs-gauge.min.js',
    // material design icons
    'node_modules/@mdi/font/fonts/materialdesignicons-webfont.eot': 'fonts/materialdesignicons-webfont.eot',
    'node_modules/@mdi/font/fonts/materialdesignicons-webfont.ttf': 'fonts/materialdesignicons-webfont.ttf',
    'node_modules/@mdi/font/fonts/materialdesignicons-webfont.woff': 'fonts/materialdesignicons-webfont.woff',
    'node_modules/@mdi/font/fonts/materialdesignicons-webfont.woff2': 'fonts/materialdesignicons-webfont.woff2',
    'node_modules/@mdi/font/css/materialdesignicons.min.css': 'css/materialdesignicons.min.css',
    'node_modules/@mdi/font/css/materialdesignicons.min.css.map': 'css/materialdesignicons.min.css.map',
};

for(var file in files) {
    var src = file;
    var dst = files[file];
    var alreadyMinifed = [
        'node_modules/codemirror-minified/lib/codemirror.js',
        'node_modules/codemirror-minified/mode/python/python.js',
        'node_modules/codemirror-minified/lib/codemirror.css',
    ];
        
    if (src.indexOf('.min') === -1 && !alreadyMinifed.includes(src) && src.search(/css|eot|woff|ttf/g) === -1) {
        // minify file
        var minDst = files[src].replace(path.extname(files[src]), '.min'+path.extname(files[src]));
        console.log('npx uglify --compress --mangle --output ' + minDst + ' -- ' + src);
        exec('npx uglifyjs --compress --mangle --output "' + minDst + '" -- "' + src + '"',
            (error, stdout, stderr) => {
                if (error) throw error;
            }
        );
    } else {
        // copy file
        console.log('copy ' + src + ' ==> ' + dst);
        fs.copyFile(src, dst, function (err) {
            if (err) throw err;
        });
    }
}

