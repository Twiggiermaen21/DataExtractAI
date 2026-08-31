// ==================== AUTH MODULE ====================
// Zarządza tokenami JWT, automatycznie dodaje Authorization header
// do wszystkich fetch() requestów i obsługuje wylogowanie.

(function () {
    'use strict';

    // ---- Token management ----

    window.Auth = {
        getAccessToken() {
            return localStorage.getItem('access_token');
        },

        getRefreshToken() {
            return localStorage.getItem('refresh_token');
        },

        getUser() {
            try {
                return JSON.parse(localStorage.getItem('user'));
            } catch {
                return null;
            }
        },

        isLoggedIn() {
            return !!this.getAccessToken();
        },

        /** Wyloguj i przekieruj na stronę logowania */
        logout() {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            window.location.replace('/login');
        },

        /** Zapisz nowe tokeny (np. po refresh) */
        saveTokens(access, refresh) {
            if (access) localStorage.setItem('access_token', access);
            if (refresh) localStorage.setItem('refresh_token', refresh);
        },
    };

    // ---- Redirect is handled by inline script in <head> of index.html ----
    // ---- auth.js only patches fetch() and manages UI ----

    // ---- Intercept fetch() to inject Authorization header ----

    const _originalFetch = window.fetch;
    let _isRefreshing = false;
    let _refreshQueue = [];

    function _getSentAccessToken(input, init) {
        let authorization = null;

        if (init.headers !== undefined) {
            authorization = new Headers(init.headers).get('Authorization');
        } else if (input instanceof Request) {
            authorization = input.headers.get('Authorization');
        }

        const match = authorization && authorization.match(/^Bearer\s+(.+)$/i);
        return match ? match[1] : null;
    }

    function _logSentAccessToken(input, init, url, isRetry = false) {
        const label = isRetry ? 'Access token wysyłany ponownie' : 'Access token wysyłany';
        const token = _getSentAccessToken(input, init);

        if (token) {
            console.log(`[Auth] ${label} do ${url}:`, token);
        } else {
            console.warn(`[Auth] Endpoint ${url} wywołany bez access tokenu. Token: <PUSTY>`);
        }
    }

    async function _tryRefreshToken() {
        const refreshToken = Auth.getRefreshToken();
        if (!refreshToken) {
            Auth.logout();
            return null;
        }

        try {
            // Use original fetch to avoid infinite loop
            const response = await _originalFetch('/api/auth/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: refreshToken }),
            });

            if (response.ok) {
                const data = await response.json();
                if (data.access) {
                    Auth.saveTokens(data.access);
                    return data.access;
                }
            }
        } catch (err) {
            console.error('[Auth] Token refresh failed:', err);
        }

        // Refresh failed — logout
        Auth.logout();
        return null;
    }

    window.fetch = async function (input, init) {
        init = init || {};

        // Determine URL
        const url = typeof input === 'string' ? input : (input instanceof Request ? input.url : String(input));

        // Only add token to same-origin /api/ requests (skip login/refresh)
        const isApiCall = url.startsWith('/api/') || url.startsWith(window.location.origin + '/api/');
        const isAuthEndpoint = url.includes('/api/auth/login') || url.includes('/api/auth/refresh');

        if (isApiCall && !isAuthEndpoint) {
            const token = Auth.getAccessToken();
            if (token) {
                if (!init.headers) {
                    init.headers = {};
                }
                // Support both Headers object and plain object
                if (init.headers instanceof Headers) {
                    if (!init.headers.has('Authorization')) {
                        init.headers.set('Authorization', 'Bearer ' + token);
                    }
                } else {
                    if (!init.headers['Authorization']) {
                        init.headers['Authorization'] = 'Bearer ' + token;
                    }
                }
            }
        }

        // Make the request
        if (isApiCall && !isAuthEndpoint) {
            _logSentAccessToken(input, init, url);
        }
        let response = await _originalFetch(input, init);

        // If 401 on an API call, try to refresh the token once
        if (response.status === 401 && isApiCall && !isAuthEndpoint) {
            if (!_isRefreshing) {
                _isRefreshing = true;

                const newToken = await _tryRefreshToken();

                _isRefreshing = false;

                // Resolve queued requests
                _refreshQueue.forEach(cb => cb(newToken));
                _refreshQueue = [];

                if (newToken) {
                    // Retry the original request with new token
                    if (init.headers instanceof Headers) {
                        init.headers.set('Authorization', 'Bearer ' + newToken);
                    } else {
                        init.headers = init.headers || {};
                        init.headers['Authorization'] = 'Bearer ' + newToken;
                    }
                    _logSentAccessToken(input, init, url, true);
                    response = await _originalFetch(input, init);
                }
            } else {
                // Another refresh is in progress — wait for it
                const newToken = await new Promise(resolve => {
                    _refreshQueue.push(resolve);
                });

                if (newToken) {
                    if (init.headers instanceof Headers) {
                        init.headers.set('Authorization', 'Bearer ' + newToken);
                    } else {
                        init.headers = init.headers || {};
                        init.headers['Authorization'] = 'Bearer ' + newToken;
                    }
                    _logSentAccessToken(input, init, url, true);
                    response = await _originalFetch(input, init);
                }
            }
        }

        return response;
    };

    // ---- Populate user info in UI ----

    document.addEventListener('DOMContentLoaded', function () {
        const user = Auth.getUser();
        
        if (user) {
            console.log("✅ Pomyślnie załadowano dane użytkownika z bazy:");
            console.table(user);
        }

        // Update profile menu header if exists
        const profileHeader = document.querySelector('#menu-profile .dropdown-header');
        if (profileHeader && user) {
            const displayName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username;
            profileHeader.textContent = displayName;
        }

        // Wire up logout button
        const logoutLink = document.getElementById('btn-logout');
        if (logoutLink) {
            logoutLink.addEventListener('click', function (e) {
                e.preventDefault();
                Auth.logout();
            });
        }
    });

})();
