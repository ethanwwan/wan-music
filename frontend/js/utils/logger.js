(function(global) {
    'use strict';

    const Logger = (function() {
        function isDevEnv() {
            try {
                return localStorage.getItem('app_env') === 'dev' ||
                       window.APP_ENV === 'dev' ||
                       !localStorage.getItem('app_env');
            } catch (e) {
                return true;
            }
        }

        const levels = {
            DEBUG: 0,
            INFO: 1,
            WARN: 2,
            ERROR: 3
        };

        const currentLevel = isDevEnv() ? levels.DEBUG : levels.WARN;

        function formatMessage(level, message, data) {
            const prefix = isDevEnv() ? `[${level}]` : `[${level}]`;
            return data !== undefined ? `${prefix} ${message}` : `${prefix} ${message}`;
        }

        function log(method, level, message, data) {
            if (levels[level] < currentLevel) return;

            const formattedMessage = formatMessage(level, message, data);

            if (data !== undefined) {
                console[method](formattedMessage, data);
            } else {
                console[method](formattedMessage);
            }
        }

        return {
            isDev: isDevEnv,

            debug: function(message, data) {
                log('debug', 'DEBUG', message, data);
            },

            info: function(message, data) {
                log('log', 'INFO', message, data);
            },

            warn: function(message, data) {
                log('warn', 'WARN', message, data);
            },

            error: function(message, data) {
                log('error', 'ERROR', message, data);
            },

            group: function(label) {
                if (!isDevEnv()) return;
                console.group?.(label);
            },

            groupEnd: function() {
                if (!isDevEnv()) return;
                console.groupEnd?.();
            },

            time: function(label) {
                if (!isDevEnv()) return;
                console.time?.(label);
            },

            timeEnd: function(label) {
                if (!isDevEnv()) return;
                console.timeEnd?.(label);
            },

            setEnv: function(env) {
                try {
                    localStorage.setItem('app_env', env);
                    window.APP_ENV = env;
                    console.log(`Logger environment changed to: ${env}. Please refresh the page.`);
                } catch (e) {
                    this.warn('Failed to set environment:', e);
                }
            },

            getEnv: function() {
                return isDevEnv() ? 'dev' : 'prod';
            },

            enableLogs: function() {
                this.setEnv('dev');
            },

            disableLogs: function() {
                this.setEnv('prod');
            },

            toggleLogs: function() {
                if (isDevEnv()) {
                    this.disableLogs();
                } else {
                    this.enableLogs();
                }
            },

            isLogsEnabled: function() {
                return isDevEnv();
            }
        };
    })();

    global.Logger = Logger;

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = Logger;
    }
})(typeof window !== 'undefined' ? window : global);
