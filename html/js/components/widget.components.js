/*global angular*/

angular.module('Cleep').component('widgetBasic', {
    transclude: {
        content: '?widgetContent',
        footer: '?widgetFooter',
    },
    template: `
        <md-card class="widget-bg-color" flex="100" style="height:100%; margin:0px;">
            <md-card-header ng-if="$ctrl.clTitle">
                <md-card-avatar ng-if="$ctrl.clIcon">
                    <cl-icon class="md-avatar-icon" cl-icon="{{ $ctrl.clIcon }}"></cl-icon>
                </md-card-avatar>
                <md-card-header-text>
                    <span ng-if="$ctrl.clTitle" class="md-title">{{ $ctrl.clTitle }}</span>
                    <span ng-if="$ctrl.clSubtitle" class="md-subhead">{{ $ctrl.clSubtitle }}</span>
                </md-card-header-text>
            </md-card-header>
            <img ng-if="$ctrl.clImage" ng-src="{{ $ctrl.clImage }}" class="md-card-image">
            <md-card-content layout="row" layout-align="center center" md-colors="{{ $ctrl.contentBgColor }}" style="height:100%">
                <ng-transclude ng-transclude-slot="content" flex></ng-transclude>
            </md-card-content>
            <md-card-actions ng-if="$ctrl.hasFooterTranscluded" layout="row" flex>
                <ng-transclude ng-transclude-slot="footer" flex></ng-transclude>
            </md-card-actions>
            <md-card-actions ng-if="$ctrl.hasFooter" layout="row" layout-align="space-between center">
                <div ng-repeat="footer in $ctrl.footer" hide="" show-gt-xs="" ng-if="footer.condition($ctrl)">
                    <div ng-if="footer.type === 'text'">
                        <cl-icon ng-if="footer.icon" cl-icon="{{ footer.icon }}" cl-tooltip="{{ footer.tooltip }}"></cl-icon>
                        <span ng-if="footer.label" class="{{ footer.style }}" flex="100">{{ footer.label }}</span>
                    </div>
                    <div ng-if="footer.type === 'button'">
                        <md-button ng-click="$ctrl.onActionClick($event, footer)" class="md-raised {{ footer.style }} {{ $ctrl.clButtonSm }}">
                            <cl-icon ng-if="footer.icon" cl-icon="{{ footer.icon }}"></cl-icon>
                            <md-tooltip ng-if="footer.tooltip">{{ footer.tooltip }}</md-tooltip>
                            {{ footer.label }}
                        </md-button>
                    </div>
                    <div ng-if="footer.type === 'chart'">
                        <chart-button
                            cl-device="$ctrl.clDevice" cl-options="footer.options" cl-tooltip="{{ footer.tooltip }}"
                            cl-btn-label="{{ footer.label }}" cl-btn-style="{{ footer.style }}" cl-btn-icon="{{ footer.icon }}"
                        ></chart-button>
                    </div>
                </div>

                <div ng-repeat="footer in $ctrl.footer" hide-gt-xs="" ng-if="footer.condition($ctrl)">
                    <div ng-if="footer.type === 'text'">
                        <cl-icon ng-if="footer.icon" cl-icon="{{ footer.icon }}" cl-tooltip="footer.tooltip"></cl-icon>
                        <span ng-if="footer.label" class="{{ footer.style }}" flex="100">{{ footer.label }}</span>
                    </div>
                    <div ng-if="footer.type === 'button'">
                        <md-button ng-click="$ctrl.onActionClick($event, footer)" class="{{ footer.style }} md-raised cl-button-sm">
                            <cl-icon ng-if="footer.icon" cl-icon="{{ footer.icon }}"></cl-icon>
                            <md-tooltip ng-if="footer.tooltip">{{ footer.tooltip }}</md-tooltip>
                        </md-button>
                    </div>
                    <div ng-if="footer.type === 'chart'">
                        <chart-button
                            cl-device="$ctrl.clDevice" cl-options="footer.options" cl-tooltip="{{ footer.tooltip }}"
                            cl-btn-label="{{ footer.label }}" cl-btn-style="{{ footer.style }} cl-button-sm" cl-btn-icon="{{ footer.icon }}"
                        ></chart-button>
                    </div>
                </div>
            </md-card-actions>
        </md-card>
    `,
    bindings: {
        clDevice: '<',
        clIcon: '<',
        clTitle: '<',
        clSubtitle: '<',
        clFooter: '<',
        clImage: '<',
    },
    controller: function ($transclude) {
        const ctrl = this;
        ctrl.footer = [];
        ctrl.hasFooter = false;
        ctrl.BG_OFF_COLOR = {
            background: 'default-primary-300',
        };
        ctrl.BG_ON_COLOR = {
            background: 'default-accent-400',
        };
        ctrl.contentBgColor = ctrl.BG_OFF_COLOR;
        ctrl.hasFooterTranscluded = false;

        ctrl.$onInit = function () {
            ctrl.hasFooterTranscluded = $transclude.isSlotFilled('footer');
            if (!ctrl.hasFooterTranscluded) {
                ctrl.prepareFooter(ctrl.clFooter);
            }
        };

        ctrl.$onChanges = function (newVal, oldVal) {
            ctrl.contentBgColor = newVal.clDevice?.on
                ? ctrl.BG_ON_COLOR
                : ctrl.BG_OFF_COLOR;
        };

        ctrl.prepareFooter = function (footers) {
            if (!footers?.length) {
                return;
            }
            ctrl.hasFooter = true;

            for (const footer of footers) {
                const isButton = Boolean(footer.click);
                ctrl.footer.push({
                    type: footer.type ?? 'text',
                    icon: footer.icon,
                    tooltip: footer.tooltip,
                    label: footer.label || '',
                    style: isButton ? footer.style : footer.style || 'md-raised',
                    click: isButton ? footer.click : undefined,
                    condition: footer.condition,
                    clButtonSm: isButton
                        ? !footer.label?.length
                            ? 'cl-button-sm'
                            : ''
                        : undefined,
                    options: footer.options,
                });
            }
        };

        ctrl.onActionClick = (ev, action) => {
            if (action.click) {
                action.click();
            }
        };
    },
});

angular.module('Cleep').component('widgetConf', {
    template: `
        <widget-basic
            cl-title="$ctrl.title" cl-subtitle="$ctrl.subtitle" cl-icon="$ctrl.icon"
            cl-image="$ctrl.image" cl-footer="$ctrl.footer" cl-device="$ctrl.clDevice" layout-fill>
            <widget-content layout="{{ $ctrl.content.layout.mode }}" layout-align="{{ $ctrl.content.layout.align }}">
                <div ng-if="$ctrl.content.raw" ng-bind-html="$ctrl.getContent()"></div>
                <div ng-repeat="attr in $ctrl.content.attrs" ng-if="attr.condition($ctrl)">
                    <cl-icon ng-if="attr.type == 'icon'" cl-class="{{ attr.style }}" cl-icon="{{ attr.icon }}"></cl-icon>
                    <div ng-if="attr.type == 'attr'" ng-bind="$ctrl.getAttr(attr)" class="{{ attr.style }}"></div>
                    <div ng-if="attr.type == 'text'" ng-bind="attr.text" class="{{ attr.style }}"></div>
                </div>
            </widget-content>
        </widget-basic>
    `,
    bindings: {
        clDevice: '<',
        clWidgetConf: '<',
        clAppIcon: '@',
    },
    controller: [
        '$interpolate',
        '$scope',
        'cleepService',
        'rpcService',
        '$parse',
        function (
            $interpolate,
            $scope,
            cleepService,
            rpcService,
            $parse
        ) {
            const ctrl = this;
            ctrl.icon = undefined;
            ctrl.title = undefined;
            ctrl.subtitle = undefined;
            ctrl.content = {
                raw: undefined,
                attrs: [],
                layout: {
                    mode: 'row',
                    align: 'space-around center'
                },
                bgColor: undefined,
            };
            ctrl.footer = [];
            ctrl.image = undefined;
            ctrl.deviceRegexp = /device\./g;
            ctrl.commandTo = undefined;

            ctrl.$onInit = function () {
                ctrl.prepareVariables(ctrl.clWidgetConf, ctrl.clAppIcon);
            };

            ctrl.prepareVariables = function (conf, appIcon) {
                ctrl.icon = conf.header?.icon ?? appIcon;
                ctrl.title = conf.header?.title ?? ctrl.clDevice.name;
                ctrl.subtitle = conf.header?.subtitle ?? ctrl.clDevice.type;
                ctrl.image = conf.image;
                ctrl.prepareContent(conf);
                ctrl.prepareFooter(conf);
            };

            ctrl.prepareContent = function (conf) {
                ctrl.prepareContentConfig(conf.content);

                if (angular.isString(conf.content)) {
                    ctrl.content.raw = ctrl.prepareForInterpolate(conf.content, 'Please add widget content');
                } else if (angular.isArray(conf.content)) {
                    ctrl.prepareContentItems(conf.content);
                } else if (angular.isObject(conf.content)) {
                    ctrl.prepareContentItems(conf.content?.items || []);
                } else {
                    console.warn('Invalid content for "' + ctrl.clDevice.type + '" widget template');
                }
            };

            ctrl.prepareContentConfig = function (content) {
                if (content.layout?.mode) {
                    ctrl.content.layout.mode = content.layout.mode;
                }
                if (content.layout?.align) {
                    ctrl.content.layout.align = content.layout.align;
                }
            };

            ctrl.prepareContentItems = function (items) {
                for (const item of items) {
                    if (item.icon) {
                        ctrl.content.attrs.push(ctrl.prepareIconContent(item));
                    } else if (item.attr) {
                        ctrl.content.attrs.push(ctrl.prepareAttrContent(item));
                    } else if (item.text) {
                        ctrl.content.attrs.push(ctrl.prepareTextContent(item));
                    }
                }
            };

            ctrl.prepareTextContent = function (content) {
                return {
                    type: 'text',
                    text: content.text || '',
                    style: content.style || 'md-display-1',
                    condition: ctrl.prepareCondition(content.condition),
                };
            };

            ctrl.prepareIconContent = function (content) {
                return {
                    type: 'icon',
                    icon: content.icon,
                    style: content.style || 'icon-lg',
                    condition: ctrl.prepareCondition(content.condition),
                };
            };

            ctrl.prepareAttrContent = function (content) {
                const filterStr = content.filter ? ' | ' + content.filter : '';
                const attrStr = '{{ device.' + content.attr + filterStr + ' }}';
                const attr = {
                    type: 'attr',
                    attr: ctrl.prepareForInterpolate(attrStr),
                    name: content.attr,
                    style: content.style || 'md-display-1',
                    condition: ctrl.prepareCondition(content.condition),
                };

                if (angular.isString(content)) {
                    // simply attribute name
                    return attr;
                } else {
                    // advanced attribute
                    return {
                        ...attr,
                        ...(content?.trueLabel && { trueLabel: content.trueLabel }),
                        ...(content?.falseLabel && { falseLabel: content.falseLabel }),
                    };
                }

                return {
                    type: 'attr',
                    falseLabel: conf.content?.attrFalseLabel,
                };
            };

            ctrl.prepareFooter = function (conf) {
                for (const footer of conf.footer || []) {
                    switch (footer.type) {
                        case 'button':
                            ctrl.footer.push(ctrl.getButtonFooterItem(footer));
                            break;
                        case 'chart':
                            ctrl.footer.push(ctrl.getChartFooterItem(footer));
                            break;
                        default:
                            ctrl.footer.push(ctrl.getTextFooterItem(footer));
                    }
                }
            };

            ctrl.getTextFooterItem = function (footer) {
                const filterStr = footer.filter ? ' | ' + footer.filter : '';
                const unitStr = footer.unit || '';
                const attrStr = footer.attr ? '{{ device.' + footer.attr + filterStr + ' }}' + unitStr : undefined || footer.label

                return {
                    type: 'text',
                    icon: footer?.icon,
                    label: $interpolate(ctrl.prepareForInterpolate(attrStr))($scope),
                    style: footer?.style,
                    tooltip: footer?.tooltip,
                    condition: ctrl.prepareCondition(footer.condition),
                };
            };

            ctrl.getButtonFooterItem = function (footer) {
                return {
                    type: 'button',
                    icon: footer?.icon,
                    label: $interpolate(ctrl.prepareForInterpolate(footer?.label))($scope),
                    click: footer?.action && ctrl.getActionClick(footer.action),
                    style: footer?.style,
                    tooltip: footer?.tooltip,
                    condition: ctrl.prepareCondition(footer.condition),
                };
            };

            ctrl.getChartFooterItem = function (footer) {
                return {
                    type: 'chart',
                    icon: footer?.icon || 'chart-areaspline',
                    label: $interpolate(ctrl.prepareForInterpolate(footer?.label))($scope),
                    style: footer?.style,
                    tooltip: footer?.tooltip,
                    condition: ctrl.prepareCondition(footer.condition),
					options: footer?.options,
                };
            };

            ctrl.prepareCondition = function (condition) {
                if (!condition) {
                    return () => true;
                }

                if (condition.attr == null || !condition.value == null) {
                    console.error('Invalid condition specified in widget "' + ctrl.clDevice.type + '"');
                }

                const variable = 'clDevice.' + condition.attr;
                const operator = condition.operator ?? '===';
                const value = angular.isString(condition.value) ? '"' + condition.value + '"' : condition.value;

                const cond = '' + variable + ' ' + operator + ' ' + value;
                return $parse(cond);
            };

            ctrl.prepareForInterpolate = function (str, defaultStr = '') {
                if (!str?.length) {
                    return defaultStr;
                }
                return str.replace(ctrl.deviceRegexp, '$ctrl.clDevice.');
            };

            ctrl.getActionClick = function (action) {
                return () => {
                    const uuidParamName = action.uuid ?? 'uuid';
                    const params = {
                        [uuidParamName]: ctrl.clDevice.uuid,
                        ...action.params,
                    };
                    rpcService
                        .sendCommand(action.command, action.to, params, action.timeout)
                        .then((resp) => {
                            cleepService.reloadDevices();
                        });
                };
            };

            ctrl.getAttr = function (attr) {
                if (attr.trueLabel && Boolean(ctrl.clDevice[attr.name])) {
                    return attr.trueLabel;
                } else if (attr.falseLabel && !Boolean(ctrl.clDevice[attr.name])) {
                    return attr.falseLabel;
                }
                return $interpolate(attr.attr)($scope);
            };

            ctrl.getContent = function () {
                if (!ctrl.content.raw?.length) {
                    return '';
                }
                return $interpolate(ctrl.content.raw)($scope);
            };
        },
    ],
});
