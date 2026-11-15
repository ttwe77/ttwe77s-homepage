/* ==================================================================
校园睡 · Service Worker
负责 PWA 离线缓存：页面数据本身存在 localStorage，这里只缓存应用外壳。
================================================================== */

var CACHE_NAME = 'campus-sleep-v1';

/* 应用外壳：安装时预缓存 */
var PRECACHE_URLS = [
    './campus-sleep.html',
    './manifest.json',
    './icons/icon-192.png',
    './icons/icon-512.png',
    './icons/icon-maskable-512.png',
    './icons/icon-180.png',
    './src/campus-sleep.svg',
    '/libs/ba-click-fx.js',
    '/src/beian.png'
];

/* 页面导航时的离线兜底页面 */
var APP_SHELL = new URL('./campus-sleep.html', self.location).pathname;

self.addEventListener('install', function (event) {
    event.waitUntil((async function () {
        var cache = await caches.open(CACHE_NAME);
        // 逐个缓存，单个资源失败不影响整体安装
        await Promise.all(PRECACHE_URLS.map(function (url) {
            return cache.add(new Request(url, { cache: 'reload' })).catch(function () { });
        }));
        await self.skipWaiting();
    })());
});

self.addEventListener('activate', function (event) {
    event.waitUntil((async function () {
        var keys = await caches.keys();
        await Promise.all(keys.map(function (key) {
            if (key !== CACHE_NAME) return caches.delete(key);
        }));
        await self.clients.claim();
    })());
});

self.addEventListener('fetch', function (event) {
    var req = event.request;
    if (req.method !== 'GET') return;

    var url = new URL(req.url);
    if (url.origin !== self.location.origin) return;
    // 接口类请求（如 /api/status）始终走网络，不缓存
    if (url.pathname.indexOf('/api/') === 0) return;

    /* 页面导航：网络优先，离线回退缓存 */
    if (req.mode === 'navigate') {
        event.respondWith((async function () {
            try {
                var fresh = await fetch(req);
                if (fresh && fresh.ok) {
                    var cache = await caches.open(CACHE_NAME);
                    cache.put(req, fresh.clone());
                }
                return fresh;
            } catch (err) {
                var hit = await caches.match(req, { ignoreSearch: true });
                if (hit) return hit;
                hit = await caches.match(APP_SHELL);
                return hit || Response.error();
            }
        })());
        return;
    }

    /* 静态资源：缓存优先，未命中则请求并写入缓存 */
    event.respondWith((async function () {
        var hit = await caches.match(req, { ignoreSearch: true });
        if (hit) return hit;
        try {
            var res = await fetch(req);
            if (res && res.ok && res.type === 'basic') {
                var cache = await caches.open(CACHE_NAME);
                cache.put(req, res.clone());
            }
            return res;
        } catch (err) {
            return Response.error();
        }
    })());
});
