---
title: 前面的传感器区域，Safari 以后再来探索吧？
description: 为了实测快步配速，我从网页传感器接口一路折腾到方向事件、定位跑步记录和指南针式金属探测，最后发现苹果浏览器把传感器接口砍成了残血版。
date: 2026-11-06 23:47:30
category: 前端
readtime: 4
author: ttwe77
tags: 浏览器, 传感器, Web API, Safari, GPS, 跑步, 金属探测器
license: CC BY-NC 4.0
license_url: https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans
updated: 2026-11-06 23:47:30
---

# 前面的传感器区域，Safari 以后再来探索吧？

<span class="hover-hint">前面的传感器区域，Safari 以后再来探索吧？<span class="hover-hint__tooltip"><span class="hint-title">前面的传感器区域，Safari 以后再来探索吧？</span>化用自《原神》中派蒙的经典台词。当玩家走到地图未开放区域的边缘时，派蒙会跳出来说：“前面的区域，以后再来探索吧”。这句话常被用来调侃被硬性限制阻挡、当前无法访问某功能或内容。文章用它来吐槽Safari对Web传感器生态的封闭——很多能力不是做不到，而是苹果不让你做。该台词还有一个知名空耳：“前面的蛆，以后再来探索吧”。</span></span>

## 开头

最近在做校园课图项目的时候，因为做了个导航功能，我就**好奇浏览器还可以获取啥手机传感器的信息**。

我最初的目的是研究我平时**走快步的配速**，我先问了下配速以便于我参考：

| 活动        |        速度参考 |          配速参考 | 体感                       |
| ----------- | --------------: | ----------------: | -------------------------- |
| 走路/散步   |        4–5 km/h |      12–15 min/km | 能轻松聊天                 |
| 快步/快走   |      5.5–7 km/h |     8.5–11 min/km | 呼吸加快，但能说短句       |
| 慢跑        |       8–10 km/h |      6–7.5 min/km | 可边跑边说话               |
| 跑步/中速跑 |      10–13 km/h |      4.6–6 min/km | 说话较费力                 |
| 快跑/阈值跑 |      13–16 km/h |   3.75–4.6 min/km | 只能短句                   |
| 冲刺        | 18–25 km/h 左右 | 约 2.4–3.3 min/km | 全力，只能持续几秒到几十秒 |

嗯**8.5-11**？我有点不敢相信，具体是多少还是先去实测看看吧。

## 从配速到手机传感器

于是我闲着也是闲着，就问了下DeepSeek浏览器可以获取手机的哪些信息。

> <u>我</u>：网页可以拿到什么传感器？
>
> <u>DeepSeek</u>：
>
> ​	**核心传感器 (基于 <span class="hover-hint">Generic Sensor API<span class="hover-hint__tooltip"><span class="hint-title">Generic Sensor API</span>W3C制定的通用传感器接口规范，提供 Accelerometer、Gyroscope、Magnetometer 等构造函数，让网页统一读取设备传感器数据。Safari（macOS与iOS）至今没有实现其中任何一个接口，这是文章中传感器可视化代码在Safari上直接失败的根本原因。</span></span>)**
>
> ​	**加速度**、角速度、**磁场强度**、**环境光照水平**、去除了重力影响的加速度、设备当前受到的重力影响、设备相对于地球坐标系的绝对方向、设备相对于初始状态的方向变化
>
> ​	**其他相关传感器与数据接口**
>
> ​	**地理位置** 、摄像头与麦克风 、接近度传感器、电池状态、设备方向与运动事件

> [!note]
>
> 1. 几乎所有传感器数据都需要用户明确授权后才能读取
>
> 2. 传感器 API 通常仅在<span class="hover-hint">安全上下文<span class="hover-hint__tooltip"><span class="hint-title">HTTPS / 安全上下文（SecureContext）</span>Generic Sensor API和定位等敏感能力要求页面处于安全上下文（HTTPS或localhost）中。Accelerometer 等构造函数在非安全上下文中会抛出 SecurityError。文章反复强调“需要HTTPS环境”即指此。</span></span>（即 **HTTPS 页面**）中可用

之后我对传感器有点兴趣，就让DeepSeek写了个例子：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>设备传感器可视化</title>
<style>
    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

    body {
        margin: 0 auto;
        padding: 18px 14px 48px;
        max-width: 620px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
        background: radial-gradient(circle at 50% 0%, #1b2740 0%, #0b1019 65%) fixed;
        color: #e6edf7;
        min-height: 100vh;
    }

    h1 {
        font-size: 1.25rem;
        text-align: center;
        margin: 0 0 16px;
        letter-spacing: .5px;
        font-weight: 600;
    }

    .status {
        padding: 11px 14px;
        border-radius: 10px;
        font-size: .85rem;
        line-height: 1.5;
        margin: 0 0 16px;
        text-align: center;
        border: 1px solid transparent;
    }
    .status.info    { background: rgba(77,163,255,.12); color: #8cc4ff; border-color: rgba(77,163,255,.25); }
    .status.warn    { background: rgba(255,176,60,.12); color: #ffc46b; border-color: rgba(255,176,60,.25); }
    .status.error   { background: rgba(255,92,92,.12);  color: #ff8b8b; border-color: rgba(255,92,92,.25); }
    .status.success { background: rgba(74,222,128,.12); color: #7ee6a8; border-color: rgba(74,222,128,.25); }

    .card {
        background: linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.015));
        border: 1px solid rgba(255,255,255,.07);
        border-radius: 14px;
        padding: 14px;
        margin-bottom: 14px;
    }

    .card-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
    }

    .card h2 {
        font-size: .92rem;
        font-weight: 600;
        margin: 0;
        color: #a9b8d0;
    }

    canvas { display: block; width: 100%; border-radius: 10px; }
    #scene { aspect-ratio: 1 / 1; background: rgba(0,0,0,.22); }
    .chart { aspect-ratio: 5 / 2; background: rgba(0,0,0,.22); }

    .legend {
        display: flex;
        gap: 16px;
        justify-content: center;
        margin-top: 10px;
        font-size: .76rem;
        color: #8b98ad;
    }
    .legend span { display: inline-flex; align-items: center; gap: 5px; }
    .swatch { width: 14px; height: 3px; border-radius: 2px; display: inline-block; }

    .grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px 18px;
    }
    .axis-row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        padding: 5px 0;
        border-bottom: 1px solid rgba(255,255,255,.05);
        font-family: ui-monospace, "SF Mono", Menlo, monospace;
        font-size: .82rem;
    }
    .axis-label { color: #7c8aa0; font-weight: 600; }
    .axis-value { color: #e6edf7; font-weight: 600; }

    .btn-group { display: flex; gap: 10px; margin-top: 4px; }
    button {
        flex: 1;
        padding: 13px 10px;
        border: none;
        border-radius: 11px;
        font-size: .92rem;
        font-weight: 600;
        font-family: inherit;
        cursor: pointer;
        transition: transform .12s, opacity .2s;
    }
    button:active:not(:disabled) { transform: scale(.97); }
    button:disabled { opacity: .35; cursor: not-allowed; }
    .btn-start { background: linear-gradient(180deg,#4ade80,#22b65c); color: #06240f; }
    .btn-stop  { background: linear-gradient(180deg,#ff6b6b,#d93a3a); color: #2a0606; }
    .mini {
        flex: 0 0 auto;
        padding: 6px 12px;
        font-size: .75rem;
        border-radius: 8px;
        background: rgba(255,255,255,.08);
        color: #b9c6d8;
        font-weight: 500;
    }

    .hint {
        font-size: .74rem;
        color: #66748a;
        text-align: center;
        line-height: 1.7;
        margin: 18px 0 0;
    }
</style>
</head>
<body>

<h1>📱 设备传感器可视化</h1>
<p id="status" class="status info">正在检测传感器支持情况…</p>

<!-- 3D 姿态 -->
<section class="card">
    <div class="card-head">
        <h2>🧊 姿态 &amp; 重力方向</h2>
        <button id="btnReset" class="mini">重置姿态</button>
    </div>
    <canvas id="scene"></canvas>
    <div class="legend">
        <span><i class="swatch" style="background:#ffb454"></i>重力方向</span>
        <span><i class="swatch" style="background:#4da3ff"></i>陀螺仪积分姿态</span>
    </div>
</section>

<!-- 加速度折线图 -->
<section class="card">
    <h2 style="margin-bottom:10px">📈 加速度计 (m/s²)</h2>
    <canvas id="chartAccel" class="chart"></canvas>
    <div class="legend">
        <span><i class="swatch" style="background:#ff6b6b"></i>X</span>
        <span><i class="swatch" style="background:#4ade80"></i>Y</span>
        <span><i class="swatch" style="background:#4da3ff"></i>Z</span>
    </div>
</section>

<!-- 陀螺仪折线图 -->
<section class="card">
    <h2 style="margin-bottom:10px">📈 陀螺仪 (°/s)</h2>
    <canvas id="chartGyro" class="chart"></canvas>
    <div class="legend">
        <span><i class="swatch" style="background:#ff6b6b"></i>X</span>
        <span><i class="swatch" style="background:#4ade80"></i>Y</span>
        <span><i class="swatch" style="background:#4da3ff"></i>Z</span>
    </div>
</section>

<!-- 数值 -->
<section class="card">
    <h2 style="margin-bottom:10px">🔢 实时数值</h2>
    <div class="grid">
        <div class="axis-row"><span class="axis-label">加速度 X</span><span id="accel-x" class="axis-value">—</span></div>
        <div class="axis-row"><span class="axis-label">陀螺仪 X</span><span id="gyro-x" class="axis-value">—</span></div>
        <div class="axis-row"><span class="axis-label">加速度 Y</span><span id="accel-y" class="axis-value">—</span></div>
        <div class="axis-row"><span class="axis-label">陀螺仪 Y</span><span id="gyro-y" class="axis-value">—</span></div>
        <div class="axis-row"><span class="axis-label">加速度 Z</span><span id="accel-z" class="axis-value">—</span></div>
        <div class="axis-row"><span class="axis-label">陀螺仪 Z</span><span id="gyro-z" class="axis-value">—</span></div>
    </div>
</section>

<div class="btn-group">
    <button id="btnStart" class="btn-start" disabled>开始读取</button>
    <button id="btnStop"  class="btn-stop"  disabled>停止读取</button>
</div>

<p class="hint">
    需要 <strong>HTTPS</strong> 环境。iOS Safari 首次使用必须在按钮点击后授权。<br>
    iOS 只稳定提供“含重力”的加速度，陀螺仪来自 rotationRate。
</p>

<script>
(function () {
    'use strict';

    /* ==================== 工具 ==================== */
    const $ = (id) => document.getElementById(id);
    const RAD2DEG = 180 / Math.PI;

    const statusEl = $('status');
    const setStatus = (msg, type = 'info') => {
        statusEl.textContent = msg;
        statusEl.className = 'status ' + type;
    };

    const fmt = (v, unit = '') =>
        (v === null || v === undefined || !isFinite(v)) ? '—' : v.toFixed(2) + unit;

    const safe = (o, k) =>
        (o && o[k] !== null && o[k] !== undefined && isFinite(o[k])) ? o[k] : null;

    /* ==================== 画布自适应（带缓存） ==================== */
    const sizeCache = new WeakMap();

    function fit(canvas) {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        let s = sizeCache.get(canvas);
        if (!s) {
            const r = canvas.getBoundingClientRect();
            s = { w: Math.max(r.width, 10), h: Math.max(r.height, 10) };
            sizeCache.set(canvas, s);
        }
        const W = Math.round(s.w * dpr);
        const H = Math.round(s.h * dpr);
        if (canvas.width !== W || canvas.height !== H) {
            canvas.width = W;
            canvas.height = H;
        }
        const ctx = canvas.getContext('2d');
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        return { ctx, w: s.w, h: s.h };
    }

    window.addEventListener('resize', () => {
        sizeCache.delete($('scene'));
        sizeCache.delete($('chartAccel'));
        sizeCache.delete($('chartGyro'));
    });

    /* ==================== 传感器状态 ==================== */
    const state = {
        accel: { x: null, y: null, z: null }, // m/s²
        gyro:  { x: null, y: null, z: null }  // rad/s
    };

    /* ==================== 四元数姿态 ==================== */
    let quat = [1, 0, 0, 0]; // w, x, y, z

    function quatMul(a, b) {
        const [aw, ax, ay, az] = a, [bw, bx, by, bz] = b;
        return [
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw
        ];
    }

    function quatNorm(q) {
        const n = Math.hypot(q[0], q[1], q[2], q[3]) || 1;
        return [q[0] / n, q[1] / n, q[2] / n, q[3] / n];
    }

    function quatToMat(q) {
        const [w, x, y, z] = q;
        return [
            1 - 2 * (y * y + z * z), 2 * (x * y - w * z),       2 * (x * z + w * y),
            2 * (x * y + w * z),     1 - 2 * (x * x + z * z),   2 * (y * z - w * x),
            2 * (x * z - w * y),     2 * (y * z + w * x),       1 - 2 * (x * x + y * y)
        ];
    }

    function mv(m, v) {
        return [
            m[0] * v[0] + m[1] * v[1] + m[2] * v[2],
            m[3] * v[0] + m[4] * v[1] + m[5] * v[2],
            m[6] * v[0] + m[7] * v[1] + m[8] * v[2]
        ];
    }

    // 用设备坐标系角速度（rad/s）右乘积分
    function integrateQuat(q, omega, dt) {
        const [wx, wy, wz] = omega;
        const mag = Math.hypot(wx, wy, wz);
        if (mag < 1e-5 || dt <= 0) return q;
        const half = mag * dt / 2;
        const s = Math.sin(half) / mag;
        const dq = [Math.cos(half), wx * s, wy * s, wz * s];
        return quatNorm(quatMul(q, dq));
    }

    /* ==================== 3D 立方体数据 ==================== */
    const CUBE_V = [
        [-1, -1, -1], [ 1, -1, -1], [ 1,  1, -1], [-1,  1, -1],
        [-1, -1,  1], [ 1, -1,  1], [ 1,  1,  1], [-1,  1,  1]
    ];
    const CUBE_FACES = [
        { idx: [4, 5, 6, 7], n: [ 0,  0,  1] }, // 前
        { idx: [1, 0, 3, 2], n: [ 0,  0, -1] }, // 后
        { idx: [5, 1, 2, 6], n: [ 1,  0,  0] }, // 右
        { idx: [0, 4, 7, 3], n: [-1,  0,  0] }, // 左
        { idx: [7, 6, 2, 3], n: [ 0,  1,  0] }, // 上
        { idx: [0, 1, 5, 4], n: [ 0, -1,  0] }  // 下
    ];

    const VIEW_AX = 0.32;   // 视角绕 X
    const VIEW_AY = -0.55;  // 视角绕 Y

    function applyView(p) {
        const cx = Math.cos(VIEW_AX), sx = Math.sin(VIEW_AX);
        const cy = Math.cos(VIEW_AY), sy = Math.sin(VIEW_AY);
        // 绕 X
        const y1 = p[1] * cx - p[2] * sx;
        const z1 = p[1] * sx + p[2] * cx;
        // 绕 Y
        const x2 = p[0] * cy + z1 * sy;
        const z2 = -p[0] * sy + z1 * cy;
        return [x2, y1, z2];
    }

    const CAM_D = 4.5;
    function project(p, w, h) {
        const f = Math.min(w, h) * 1.5;
        const z = Math.max(p[2] + CAM_D, 0.2);
        const s = f / z;
        return [w / 2 + p[0] * s, h / 2 - p[1] * s, z];
    }

    const LIGHT = (() => {
        const v = [-0.35, 0.78, 0.52];
        const n = Math.hypot(v[0], v[1], v[2]);
        return [v[0] / n, v[1] / n, v[2] / n];
    })();

    /* ==================== 绘制：3D 场景 ==================== */
    const sceneCv = $('scene');

    function drawScene() {
        const { ctx, w, h } = fit(sceneCv);
        ctx.clearRect(0, 0, w, h);

        const R = quatToMat(quat);
        const worldV = CUBE_V.map(v => mv(R, v));
        const projV = worldV.map(v => project(applyView(v), w, h));

        // 面排序（画家算法：远 → 近）
        const faces = CUBE_FACES.map(f => {
            const pts = f.idx.map(i => projV[i]);
            const wn = mv(R, f.n);
            const zc = f.idx.reduce((s, i) => s + applyView(worldV[i])[2], 0) / 4;
            const lit = Math.max(0, wn[0] * LIGHT[0] + wn[1] * LIGHT[1] + wn[2] * LIGHT[2]);
            return { pts, z: zc, lum: 0.30 + 0.70 * lit };
        }).sort((a, b) => b.z - a.z);

        for (const f of faces) {
            ctx.beginPath();
            ctx.moveTo(f.pts[0][0], f.pts[0][1]);
            for (let i = 1; i < f.pts.length; i++) ctx.lineTo(f.pts[i][0], f.pts[i][1]);
            ctx.closePath();
            const l = Math.round(20 + 48 * f.lum);
            ctx.fillStyle = `hsl(208, 82%, ${l}%)`;
            ctx.fill();
            ctx.strokeStyle = 'rgba(150, 205, 255, .35)';
            ctx.lineWidth = 1.2;
            ctx.stroke();
        }

        // 重力方向箭头
        const a = state.accel;
        if (a.x !== null && a.y !== null && a.z !== null) {
            const len = Math.hypot(a.x, a.y, a.z);
            if (len > 0.3) {
                // 设备坐标系中"重力指向"的方向
                const dn = [-a.x / len, -a.y / len, -a.z / len];
                const wd = mv(R, dn);
                const p0 = project(applyView([0, 0, 0]), w, h);
                const p1 = project(applyView([wd[0] * 2.0, wd[1] * 2.0, wd[2] * 2.0]), w, h);

                const dx = p1[0] - p0[0], dy = p1[1] - p0[1];
                const dl = Math.hypot(dx, dy) || 1;

                ctx.save();
                ctx.strokeStyle = '#ffb454';
                ctx.lineWidth = 3;
                ctx.lineCap = 'round';
                ctx.shadowColor = 'rgba(255,180,84,.85)';
                ctx.shadowBlur = 10;
                ctx.beginPath();
                ctx.moveTo(p0[0], p0[1]);
                ctx.lineTo(p1[0], p1[1]);
                ctx.stroke();

                // 箭头
                const ux = dx / dl, uy = dy / dl;
                const ah = 13, aw = 6.5;
                ctx.beginPath();
                ctx.moveTo(p1[0], p1[1]);
                ctx.lineTo(p1[0] - ux * ah - uy * aw, p1[1] - uy * ah + ux * aw);
                ctx.lineTo(p1[0] - ux * ah + uy * aw, p1[1] - uy * ah - ux * aw);
                ctx.closePath();
                ctx.fillStyle = '#ffb454';
                ctx.fill();
                ctx.restore();
            }
        }
    }

    /* ==================== 折线图 ==================== */
    const MAX_POINTS = 200;
    const dataAccel = [[], [], []];
    const dataGyro  = [[], [], []];
    const CH_COLORS = ['#ff6b6b', '#4ade80', '#4da3ff'];

    let accelRange = 12;
    let gyroRange  = 45;

    function drawChart(canvas, data, range) {
        const { ctx, w, h } = fit(canvas);
        ctx.clearRect(0, 0, w, h);
        const mid = h / 2;
        const half = h / 2 - 5;

        // 网格
        ctx.strokeStyle = 'rgba(255,255,255,.055)';
        ctx.lineWidth = 1;
        for (let i = 1; i < 4; i++) {
            const y = Math.round((h * i) / 4) + .5;
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
        }
        // 零线
        ctx.strokeStyle = 'rgba(255,255,255,.18)';
        ctx.beginPath(); ctx.moveTo(0, mid + .5); ctx.lineTo(w, mid + .5); ctx.stroke();

        for (let s = 0; s < 3; s++) {
            const arr = data[s];
            if (arr.length < 2) continue;
            ctx.beginPath();
            ctx.strokeStyle = CH_COLORS[s];
            ctx.lineWidth = 1.7;
            ctx.lineJoin = 'round';
            ctx.lineCap = 'round';
            for (let i = 0; i < arr.length; i++) {
                const x = (i / (MAX_POINTS - 1)) * w;
                const v = Math.max(-1, Math.min(1, arr[i] / range));
                const y = mid - v * half;
                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.stroke();
        }
    }

    function updateRange(cur, data, min) {
        let m = 0;
        for (let s = 0; s < 3; s++) {
            const arr = data[s];
            for (let i = 0; i < arr.length; i++) {
                const v = arr[i] < 0 ? -arr[i] : arr[i];
                if (v > m) m = v;
            }
        }
        const target = Math.max(m * 1.2, min);
        return cur + (target - cur) * 0.06;
    }

    /* ==================== 采样 & 数值刷新 ==================== */
    function pushSample() {
        const a = state.accel, g = state.gyro;

        if (a.x !== null) {
            dataAccel[0].push(a.x);
            dataAccel[1].push(a.y === null ? 0 : a.y);
            dataAccel[2].push(a.z === null ? 0 : a.z);
            for (const d of dataAccel) { while (d.length > MAX_POINTS) d.shift(); }
        }
        if (g.x !== null) {
            dataGyro[0].push(g.x * RAD2DEG);
            dataGyro[1].push(g.y === null ? 0 : g.y * RAD2DEG);
            dataGyro[2].push(g.z === null ? 0 : g.z * RAD2DEG);
            for (const d of dataGyro) { while (d.length > MAX_POINTS) d.shift(); }
        }
    }

    const el = {
        ax: $('accel-x'), ay: $('accel-y'), az: $('accel-z'),
        gx: $('gyro-x'),  gy: $('gyro-y'),  gz: $('gyro-z')
    };

    function updateReadouts() {
        const a = state.accel, g = state.gyro;
        el.ax.textContent = fmt(a.x, ' m/s²');
        el.ay.textContent = fmt(a.y, ' m/s²');
        el.az.textContent = fmt(a.z, ' m/s²');
        el.gx.textContent = g.x === null ? '—' : (g.x * RAD2DEG).toFixed(2) + ' °/s';
        el.gy.textContent = g.y === null ? '—' : (g.y * RAD2DEG).toFixed(2) + ' °/s';
        el.gz.textContent = g.z === null ? '—' : (g.z * RAD2DEG).toFixed(2) + ' °/s';
    }

    function clearReadouts() {
        Object.values(el).forEach(n => { n.textContent = '—'; });
    }

    /* ==================== 主循环 ==================== */
    const chartAccelCv = $('chartAccel');
    const chartGyroCv  = $('chartGyro');

    let lastT = 0;
    let lastSampleT = 0;

    function loop(t) {
        const now = t || performance.now();
        let dt = lastT ? (now - lastT) / 1000 : 0;
        lastT = now;
        if (dt > 0.1) dt = 0.1;

        // 陀螺仪积分 → 立方体姿态
        const g = state.gyro;
        if (g.x !== null) {
            quat = integrateQuat(quat, [g.x, g.y, g.z], dt);
        }

        // 采样
        if (now - lastSampleT > 33) {
            lastSampleT = now;
            pushSample();
            updateReadouts();
        }

        // 绘制
        drawScene();

        accelRange = updateRange(accelRange, dataAccel, 5);
        gyroRange  = updateRange(gyroRange,  dataGyro,  30);
        drawChart(chartAccelCv, dataAccel, accelRange);
        drawChart(chartGyroCv,  dataGyro,  gyroRange);

        requestAnimationFrame(loop);
    }

    /* ==================== 传感器接入 ==================== */
    const hasGenericAccelerometer = typeof Accelerometer === 'function';
    const hasGenericGyroscope     = typeof Gyroscope === 'function';
    const hasDeviceMotion         = typeof DeviceMotionEvent !== 'undefined';

    let mode = null;          // 'generic' | 'safari'
    let accelerometer = null;
    let gyroscope = null;
    let motionHandler = null;

    const btnStart = $('btnStart');
    const btnStop  = $('btnStop');

    /* ---------- 路径 A：Generic Sensor API ---------- */
    async function startGenericSensors() {
        try {
            const list = [];
            if (hasGenericAccelerometer) list.push(navigator.permissions.query({ name: 'accelerometer' }));
            if (hasGenericGyroscope)     list.push(navigator.permissions.query({ name: 'gyroscope' }));
            const results = await Promise.all(list);
            if (results.some(r => r.state === 'denied')) {
                setStatus('⚠️ 传感器权限被拒绝，请在浏览器设置中允许后重试。', 'warn');
                btnStart.disabled = false;
                return;
            }
        } catch (e) { /* 忽略，继续尝试实例化 */ }

        let ok = false;

        if (hasGenericAccelerometer) {
            try {
                accelerometer = new Accelerometer({ frequency: 60, referenceFrame: 'device' });
                accelerometer.addEventListener('reading', () => {
                    state.accel.x = safe(accelerometer, 'x');
                    state.accel.y = safe(accelerometer, 'y');
                    state.accel.z = safe(accelerometer, 'z');
                });
                accelerometer.addEventListener('error', e => console.warn('加速度计错误：', e.error));
                accelerometer.start();
                ok = true;
            } catch (e) {
                console.warn('Generic Accelerometer 启动失败：', e);
            }
        }

        if (hasGenericGyroscope) {
            try {
                gyroscope = new Gyroscope({ frequency: 60, referenceFrame: 'device' });
                gyroscope.addEventListener('reading', () => {
                    state.gyro.x = safe(gyroscope, 'x');
                    state.gyro.y = safe(gyroscope, 'y');
                    state.gyro.z = safe(gyroscope, 'z');
                });
                gyroscope.addEventListener('error', e => console.warn('陀螺仪错误：', e.error));
                gyroscope.start();
                ok = true;
            } catch (e) {
                console.warn('Generic Gyroscope 启动失败：', e);
            }
        }

        if (ok) {
            mode = 'generic';
            setStatus('✅ 传感器已启动（Generic Sensor API），正在读取…', 'success');
            btnStop.disabled = false;
        } else if (hasDeviceMotion) {
            await startDeviceMotion();
        } else {
            setStatus('❌ 无法启动任何传感器。', 'error');
            btnStart.disabled = false;
        }
    }

    /* ---------- 路径 B：DeviceMotionEvent（Safari） ---------- */
    async function startDeviceMotion() {
        if (typeof DeviceMotionEvent.requestPermission === 'function') {
            try {
                const res = await DeviceMotionEvent.requestPermission();
                if (res !== 'granted') {
                    setStatus('⚠️ 运动传感器权限未授予，请在弹窗中点击"允许"。', 'warn');
                    btnStart.disabled = false;
                    return;
                }
            } catch (e) {
                console.warn('requestPermission 失败：', e);
                setStatus('⚠️ 权限请求失败，请确保由用户点击触发。', 'warn');
                btnStart.disabled = false;
                return;
            }
        }

        motionHandler = (event) => {
            const a = event.accelerationIncludingGravity;
            if (a) {
                state.accel.x = safe(a, 'x');
                state.accel.y = safe(a, 'y');
                state.accel.z = safe(a, 'z');
            }
            const r = event.rotationRate;
            if (r) {
                const al = safe(r, 'alpha');
                const be = safe(r, 'beta');
                const ga = safe(r, 'gamma');
                state.gyro.x = be === null ? null : be / RAD2DEG;
                state.gyro.y = ga === null ? null : ga / RAD2DEG;
                state.gyro.z = al === null ? null : al / RAD2DEG;
            }
        };

        window.addEventListener('devicemotion', motionHandler);

        mode = 'safari';
        setStatus('✅ 传感器已启动（DeviceMotionEvent），正在读取…', 'success');
        btnStop.disabled = false;
    }

    /* ---------- 启动 ---------- */
    async function start() {
        btnStart.disabled = true;

        // 重置数据缓冲
        dataAccel.forEach(d => d.length = 0);
        dataGyro.forEach(d => d.length = 0);
        lastT = 0;
        lastSampleT = 0;

        if (hasGenericAccelerometer || hasGenericGyroscope) {
            await startGenericSensors();
        } else if (hasDeviceMotion) {
            await startDeviceMotion();
        } else {
            setStatus('❌ 当前浏览器不支持任何可用的传感器接口。', 'error');
            btnStart.disabled = false;
        }
    }

    /* ---------- 停止 ---------- */
    function stop() {
        if (mode === 'generic') {
            if (accelerometer) { try { accelerometer.stop(); } catch (e) {} accelerometer = null; }
            if (gyroscope)     { try { gyroscope.stop(); }     catch (e) {} gyroscope = null; }
        } else if (mode === 'safari') {
            if (motionHandler) {
                window.removeEventListener('devicemotion', motionHandler);
                motionHandler = null;
            }
        }

        state.accel.x = state.accel.y = state.accel.z = null;
        state.gyro.x  = state.gyro.y  = state.gyro.z  = null;

        clearReadouts();
        dataAccel.forEach(d => d.length = 0);
        dataGyro.forEach(d => d.length = 0);

        mode = null;
        setStatus('⏹ 传感器已停止。', 'info');
        btnStart.disabled = false;
        btnStop.disabled  = true;
    }

    /* ---------- 重置姿态 ---------- */
    $('btnReset').addEventListener('click', () => {
        quat = [1, 0, 0, 0];
    });

    /* ---------- 事件绑定 ---------- */
    btnStart.addEventListener('click', start);
    btnStop.addEventListener('click', stop);

    /* ==================== 初始检测 ==================== */
    if (hasGenericAccelerometer || hasGenericGyroscope) {
        setStatus('检测到 Generic Sensor API。点击「开始读取」以授权并启动。', 'info');
        btnStart.disabled = false;
    } else if (hasDeviceMotion) {
        setStatus('检测到 DeviceMotionEvent。点击「开始读取」以授权并启动。', 'info');
        btnStart.disabled = false;
    } else {
        setStatus('❌ 当前浏览器不支持任何传感器接口（需 HTTPS 环境）。', 'error');
    }

    // 先跑起来（静止时显示一个空立方体）
    requestAnimationFrame(loop);
})();
</script>
</body>
</html>
```

这是我在给DeepSeek提出了一连串需求后得到的简陋版本，<u>有一堆BUG我懒得去修了</u>。

> *Safari 目前（包括 macOS 和 iOS）**完全不支持** Generic Sensor API，所以上一版代码中使用的 `Accelerometer` 和 `Gyroscope` 构造函数在 Safari 中会直接失败。*

> *这是可直接运行的HTML代码，把手机传感器数据变成了实时旋转的3D立方体和动态折线图......*

## 从手机传感器到宿舍跑

之后我就又叫DeepSeek写了一个**读取手机传感器显示速度**(km/h)的网页，然后我就开始了“<u>宿舍跑</u>”看看

绕了我们这一层楼一圈，看了下结果。因为速度是即时显示的，所以我得边跑边看。现在已经忘记了那时的数据（截图也一起忘了）

然后我就继续折腾......

> <u>我</u>：写一个html手机跑步程序，用户点击跑步之后精确记录传感器，之后生成报表。实时显示配速等信息和km/h，兼容Safari。【<span class="hover-hint">蔚蓝档案<span class="hover-hint__tooltip"><span class="hint-title">蔚蓝档案（Blue Archive）</span>韩国Nexon旗下NAT Games开发的二次元手游，以蓝白色调、清新简洁的UI著称。文章在向DeepSeek提出跑步程序需求时附带了“蔚蓝档案UI设计参考文档”，Runner页面的斜切按钮、蓝白配色、圆角卡片等设计语言均直接来源于此。</span></span>UI设计参考文档V2.md】
>
> <u>DeepSeek</u>：这是可直接运行的 HTML 跑步记录工具

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,maximum-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#21a5e3">
<title>RunBlue · 跑步记录</title>
<style>
/* ============ 1. 设计令牌 ============ */
:root{
  --font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",sans-serif;

  --color-bg-white:#FFFFFF;
  --color-bg-light:#FAFAFA;
  --color-bg-soft:#F5F5F5;
  --color-border:#EDEDED;
  --color-border-strong:#D4D4D4;
  --color-text-primary:#1F1F1F;
  --color-text-body:#404040;
  --color-text-secondary:#737373;
  --color-text-disabled:#A3A3A3;

  --color-primary:#21a5e3;
  --color-primary-hover:#0E7AE0;
  --color-primary-active:#0B6BC5;
  --color-primary-light:#ABD7FF;
  --color-primary-alt:#BEC0EC;
  --color-accent:#4454F8;

  --color-danger:#F21B28;
  --color-success:#169B5B;
  --color-warning:#FFD84D;

  --radius-sm:4px;
  --radius-md:8px;
  --radius-lg:12px;
  --radius-xl:16px;
  --radius-full:9999px;

  --shadow-card:0 2px 8px rgba(0,0,0,.06);
  --shadow-card-hover:0 4px 16px rgba(0,0,0,.1);
  --shadow-accent:0 6px 20px rgba(33,165,227,.25);

  --ease-out:cubic-bezier(.22,.61,.36,1);
  --ease-in-out:cubic-bezier(.65,.05,.36,1);
  --ease-soft:cubic-bezier(.4,0,.2,1);
  --duration-fast:120ms;
  --duration-base:200ms;
  --duration-slow:380ms;

  --btn-skew:-10deg;
  --btn-skew-inv:10deg;

  --topbar-h:56px;
  --content-max:560px;

  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px;
  --space-5:20px; --space-6:24px; --space-8:32px;
}
@media (max-width:480px){
  :root{ --btn-skew:-6deg; --btn-skew-inv:6deg; }
}

/* ============ 2. 基础 ============ */
*,*::before,*::after{box-sizing:border-box;}
html,body{margin:0;padding:0;height:100%;}
body{
  font-family:var(--font-sans);
  background:var(--color-bg-light);
  color:var(--color-text-body);
  -webkit-font-smoothing:antialiased;
  -webkit-tap-highlight-color:transparent;
  overscroll-behavior:none;
  font-size:14px;
}
body::before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(620px 420px at 105% -8%, rgba(33,165,227,.13), transparent 70%),
    radial-gradient(520px 420px at -12% 108%, rgba(190,192,236,.20), transparent 70%);
}
[hidden]{display:none !important;}
.num{font-variant-numeric:tabular-nums;}

/* ============ 3. 按钮 ============ */
.btn{
  display:inline-flex;align-items:center;justify-content:center;
  border:0;background:none;font-family:inherit;padding:0;
  border-radius:var(--radius-lg);
  font-weight:700;letter-spacing:.3px;white-space:nowrap;cursor:pointer;
  transform:skewX(var(--btn-skew));
  transform-origin:center;
  transition:background var(--duration-fast) ease,
             transform var(--duration-fast) ease,
             box-shadow var(--duration-base) ease,
             border-color var(--duration-fast) ease,
             color var(--duration-fast) ease,
             opacity var(--duration-fast) ease;
  -webkit-user-select:none;user-select:none;
}
.btn > span{
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  transform:skewX(var(--btn-skew-inv));
}
.btn:hover{transform:skewX(var(--btn-skew)) translateY(-2px);}
.btn:active{transform:skewX(var(--btn-skew)) scale(.96);}
.btn:disabled{opacity:.45;cursor:not-allowed;transform:skewX(var(--btn-skew));}

.btn--lg{height:52px;padding:0 26px;font-size:16px;font-weight:700;}
.btn--md{height:44px;padding:0 22px;font-size:14px;font-weight:600;}
.btn--sm{height:36px;padding:0 16px;font-size:13px;font-weight:600;}

.btn--primary{background:var(--color-primary);color:#fff;box-shadow:var(--shadow-accent);}
.btn--primary:hover{background:var(--color-primary-hover);}
.btn--primary:active{background:var(--color-primary-active);}
.btn--secondary{background:#fff;color:var(--color-primary);border:1.5px solid var(--color-primary-light);}
.btn--secondary:hover{background:rgba(33,165,227,.06);}
.btn--ghost{background:rgba(33,165,227,.08);color:var(--color-primary);}
.btn--danger{background:var(--color-danger);color:#fff;box-shadow:0 6px 18px rgba(242,27,40,.24);}
.btn--danger:hover{background:#d91621;}
.btn--block{width:100%;}

@media (hover:none){
  .btn:hover{transform:skewX(var(--btn-skew));}
  .btn--primary:hover{background:var(--color-primary);}
  .btn--danger:hover{background:var(--color-danger);}
  .btn--secondary:hover{background:#fff;}
}

/* ============ 4. 卡片 ============ */
.card{
  position:relative;
  background:var(--color-bg-white);
  border-radius:var(--radius-lg);
  border:1px solid var(--color-border);
  box-shadow:var(--shadow-card);
  padding:var(--space-4);
}
.card--static:active{transform:none;}

/* ============ 5. 顶栏 ============ */
.topbar{
  position:fixed;top:0;left:0;right:0;z-index:200;
  height:calc(var(--topbar-h) + env(safe-area-inset-top,0px));
  padding:env(safe-area-inset-top,0px) 16px 0;
  display:flex;align-items:center;gap:12px;
  background:rgba(255,255,255,.92);
  -webkit-backdrop-filter:blur(14px);
  backdrop-filter:blur(14px);
  border-bottom:1px solid rgba(0,0,0,.05);
}
.brand{display:flex;align-items:center;gap:8px;font-weight:800;font-size:17px;
  color:var(--color-text-primary);letter-spacing:.4px;}
.brand__mark{
  display:inline-block;padding:3px 10px;border-radius:var(--radius-sm);
  background:linear-gradient(135deg,var(--color-primary),var(--color-accent));
  color:#fff;font-size:12px;font-weight:800;letter-spacing:1px;
  transform:skewX(var(--btn-skew));
}
.topbar__spacer{flex:1;}

.gps-badge{
  display:inline-flex;align-items:center;gap:6px;
  padding:5px 12px;border-radius:var(--radius-full);
  font-size:11px;font-weight:700;letter-spacing:.3px;
  background:rgba(63,86,140,.08);color:var(--color-text-secondary);
  transition:background .2s,color .2s;
}
.gps-badge::before{
  content:"";width:6px;height:6px;border-radius:50%;
  background:var(--color-text-disabled);transition:background .2s,box-shadow .2s;
}
.gps-badge.is-ok{background:rgba(22,155,91,.10);color:var(--color-success);}
.gps-badge.is-ok::before{background:var(--color-success);box-shadow:0 0 0 3px rgba(22,155,91,.16);}
.gps-badge.is-wait{background:rgba(255,216,77,.20);color:#8a6d00;}
.gps-badge.is-wait::before{background:#e0a800;animation:blink 1.1s ease-in-out infinite;}
.gps-badge.is-err{background:rgba(242,27,40,.10);color:var(--color-danger);}
.gps-badge.is-err::before{background:var(--color-danger);}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}

/* ============ 6. 视图容器 ============ */
.views{position:fixed;inset:0;overflow:hidden;z-index:1;}
.view{
  position:absolute;inset:0;
  overflow-y:auto;-webkit-overflow-scrolling:touch;
  padding:calc(var(--topbar-h) + env(safe-area-inset-top,0px) + 16px) 16px
          calc(32px + env(safe-area-inset-bottom,0px));
  opacity:0;visibility:hidden;transform:translateY(16px);
  transition:opacity .3s var(--ease-out),
             transform .3s var(--ease-out),
             visibility .3s;
}
.view.is-active{opacity:1;visibility:visible;transform:none;}
.view__inner{max-width:var(--content-max);margin:0 auto;}

/* ============ 7. 首页 ============ */
.hero{
  border-radius:var(--radius-xl);
  padding:26px 20px 22px;
  background:
    radial-gradient(120% 140% at 105% -10%, rgba(190,192,236,.50), transparent 62%),
    linear-gradient(135deg,#FFFFFF 0%,#F2F9FF 100%);
  border:1px solid #E4F1FC;
  box-shadow:0 8px 26px rgba(33,165,227,.10);
  overflow:hidden;
  position:relative;
}
.hero::after{
  content:"";position:absolute;right:-40px;top:-40px;width:150px;height:150px;
  border-radius:50%;background:rgba(33,165,227,.10);filter:blur(6px);pointer-events:none;
}
.hero__title{
  font-size:26px;font-weight:800;color:var(--color-text-primary);
  letter-spacing:.5px;line-height:1.2;
}
.hero__desc{
  font-size:13px;color:var(--color-text-secondary);
  margin:8px 0 22px;line-height:1.6;
}
.hero__chips{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap;}
.chip{
  display:inline-flex;align-items:center;height:22px;padding:0 9px;
  border-radius:var(--radius-sm);
  font-size:11px;font-weight:600;
  background:rgba(33,165,227,.09);color:var(--color-primary);
}
.chip--ok{background:rgba(22,155,91,.10);color:var(--color-success);}
.chip--warn{background:rgba(242,27,40,.08);color:var(--color-danger);}

.section-title{
  display:flex;align-items:center;gap:8px;
  font-size:15px;font-weight:700;color:var(--color-text-primary);
  margin:26px 2px 12px;
}
.section-title::before{
  content:"";width:4px;height:14px;border-radius:2px;
  background:var(--color-primary);transform:skewX(var(--btn-skew));
}

.list{display:grid;grid-template-columns:1fr;gap:10px;}
.list-item{
  display:grid;grid-template-columns:52px minmax(0,1fr);
  gap:12px;align-items:center;
  padding:10px;cursor:pointer;
  transition:box-shadow var(--duration-base) ease,transform var(--duration-fast) ease;
}
.list-item:hover{box-shadow:var(--shadow-card-hover);}
.list-item:active{transform:scale(.985);}
.list-item__thumb{
  width:52px;height:52px;border-radius:var(--radius-md);
  background:linear-gradient(135deg,var(--c1,#ABD7FF),var(--c2,#BEC0EC));
  position:relative;overflow:hidden;
}
.list-item__thumb::after{
  content:"";position:absolute;inset:0;
  background-image:
    linear-gradient(rgba(255,255,255,.16) 1px,transparent 1px),
    linear-gradient(90deg,rgba(255,255,255,.16) 1px,transparent 1px);
  background-size:13px 13px;opacity:.55;
}
.list-item__title{
  font-size:17px;font-weight:800;color:var(--color-text-primary);
  font-variant-numeric:tabular-nums;letter-spacing:-.2px;
}
.list-item__title em{
  font-style:normal;font-size:11px;font-weight:700;
  color:var(--color-text-secondary);margin-left:3px;
}
.list-item__meta{
  font-size:11px;color:var(--color-text-secondary);margin-top:4px;
  font-variant-numeric:tabular-nums;
}
.empty{
  padding:26px 16px;text-align:center;
  font-size:12.5px;color:var(--color-text-disabled);
  background:#fff;border:1px dashed var(--color-border);
  border-radius:var(--radius-lg);
}

/* ============ 8. 跑步中 ============ */
.run-hero{text-align:center;padding:16px 0 6px;}
.run-dist{
  font-size:clamp(54px,17vw,82px);
  font-weight:800;line-height:1;
  letter-spacing:-2.5px;
  color:var(--color-text-primary);
  font-variant-numeric:tabular-nums;
}
.run-dist em{
  font-style:normal;font-size:18px;font-weight:700;
  color:var(--color-text-secondary);margin-left:6px;letter-spacing:0;
}
.run-status{
  margin-top:14px;
  display:inline-flex;align-items:center;gap:7px;
  height:26px;padding:0 13px;
  border-radius:var(--radius-full);
  font-size:11.5px;font-weight:700;letter-spacing:.3px;
  background:rgba(33,165,227,.09);color:var(--color-primary);
  transition:background .2s,color .2s;
}
.run-status .dot{
  width:6px;height:6px;border-radius:50%;background:currentColor;
  box-shadow:0 0 0 3px rgba(33,165,227,.15);
  animation:pulse 1.6s var(--ease-soft) infinite;
}
.run-status.is-paused{background:rgba(255,216,77,.22);color:#96700a;}
.run-status.is-paused .dot{animation:none;box-shadow:0 0 0 3px rgba(224,168,0,.16);}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(.72)}}

.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:20px;}
.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:10px;}
.stat{
  background:#fff;border:1px solid var(--color-border);
  border-radius:var(--radius-lg);box-shadow:var(--shadow-card);
  padding:12px 8px;text-align:center;
}
.stat__label{font-size:11px;color:var(--color-text-secondary);letter-spacing:.4px;}
.stat__val{
  font-size:21px;font-weight:800;color:var(--color-text-primary);
  margin-top:5px;line-height:1.15;font-variant-numeric:tabular-nums;
  letter-spacing:-.4px;
}
.stat__val.is-small{font-size:17px;}
.stat__unit{font-size:10px;color:var(--color-text-disabled);margin-top:3px;}

.run-actions{display:flex;gap:12px;margin-top:24px;padding:0 4px;}
.run-actions .btn{flex:1;}
.hint-text{
  font-size:11px;color:var(--color-text-disabled);
  text-align:center;margin-top:16px;line-height:1.6;
}

/* ============ 9. 报表 ============ */
.report-head{padding:6px 2px 16px;}
.report-title{font-size:22px;font-weight:800;color:var(--color-text-primary);letter-spacing:.3px;}
.report-date{font-size:12px;color:var(--color-text-secondary);margin-top:6px;font-variant-numeric:tabular-nums;}

.hero-stat{
  border-radius:var(--radius-xl);
  padding:24px 20px;
  background:
    radial-gradient(120% 130% at 100% 0%, rgba(33,165,227,.16), transparent 62%),
    linear-gradient(135deg,#FFFFFF,#F3FAFF);
  border:1px solid #E4F1FC;
  text-align:center;
}
.hero-stat__num{
  font-size:clamp(44px,13vw,64px);font-weight:800;line-height:1;
  color:var(--color-text-primary);letter-spacing:-2px;
  font-variant-numeric:tabular-nums;
}
.hero-stat__num em{
  font-style:normal;font-size:17px;font-weight:700;
  color:var(--color-text-secondary);margin-left:5px;letter-spacing:0;
}
.hero-stat__meta{
  margin-top:12px;display:flex;justify-content:center;gap:18px;
  font-size:12px;color:var(--color-text-secondary);
  font-variant-numeric:tabular-nums;
}
.hero-stat__meta b{color:var(--color-text-primary);font-weight:800;}

.split-row{
  display:grid;grid-template-columns:38px 1fr 62px;
  align-items:center;gap:10px;
  padding:9px 2px;
  border-bottom:1px dashed var(--color-border);
  font-size:12.5px;font-variant-numeric:tabular-nums;
}
.split-row:last-child{border-bottom:0;}
.split-row__idx{
  font-weight:800;color:var(--color-primary);font-size:12px;
}
.split-row__bar{
  height:6px;border-radius:3px;
  background:linear-gradient(90deg,var(--color-primary),#4FA9FF);
  min-width:8px;transition:width .4s var(--ease-soft);
}
.split-row__time{text-align:right;font-weight:700;color:var(--color-text-primary);}
.split-row__time small{display:block;font-size:10px;font-weight:500;color:var(--color-text-disabled);}

.track-box{
  background:#fff;border:1px solid var(--color-border);
  border-radius:var(--radius-lg);box-shadow:var(--shadow-card);
  padding:8px;overflow:hidden;
}
.track-box svg{display:block;width:100%;height:auto;border-radius:var(--radius-md);}

.actions{display:flex;gap:12px;margin-top:26px;padding:0 4px;}
.actions .btn{flex:1;}

/* ============ 10. Toast ============ */
.toast{
  position:fixed;left:50%;
  top:calc(var(--topbar-h) + env(safe-area-inset-top,0px) + 16px);
  z-index:99999;
  display:inline-flex;align-items:center;gap:9px;
  max-width:min(86vw,360px);
  padding:10px 20px;
  border-radius:var(--radius-full);
  background:rgba(255,255,255,.94);
  -webkit-backdrop-filter:blur(14px);
  backdrop-filter:blur(14px);
  box-shadow:var(--shadow-card-hover);
  font-size:13px;font-weight:600;color:var(--color-text-primary);
  white-space:pre-line;
  pointer-events:none;
  opacity:0;transform:translate(-50%,-10px);
  transition:opacity .25s var(--ease-out),transform .25s var(--ease-out);
}
.toast.is-visible{opacity:1;transform:translate(-50%,0);}
.toast::before{
  content:"";width:6px;height:6px;border-radius:50%;
  background:var(--color-primary);
  box-shadow:0 0 0 3px rgba(33,165,227,.15);
  flex:none;
}

/* ============ 11. Modal ============ */
.modal-overlay{
  position:fixed;inset:0;z-index:1000;
  display:flex;align-items:center;justify-content:center;
  padding:16px;
  background:rgba(0,0,0,.4);
  -webkit-backdrop-filter:blur(4px);
  backdrop-filter:blur(4px);
  animation:fadeIn .2s var(--ease-out);
}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.modal-box{
  width:100%;max-width:400px;
  background:#fff;
  border-radius:var(--radius-xl);
  box-shadow:0 10px 40px rgba(0,0,0,.16);
  padding:22px 20px calc(18px + env(safe-area-inset-bottom,0px));
  animation:modalIn .3s var(--ease-out);
}
@keyframes modalIn{
  from{opacity:0;transform:scale(.95) translateY(10px)}
  to{opacity:1;transform:scale(1) translateY(0)}
}
.modal-title{font-size:17px;font-weight:800;color:var(--color-text-primary);}
.modal-body{
  font-size:13px;color:var(--color-text-secondary);
  line-height:1.7;margin:10px 0 20px;
}
.modal-body b{color:var(--color-primary);font-weight:800;font-variant-numeric:tabular-nums;}
.modal-foot{display:flex;gap:10px;}
.modal-foot .btn{flex:1;}

/* 减少动效 */
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{
    animation-duration:.001ms !important;
    animation-iteration-count:1 !important;
    transition-duration:.001ms !important;
  }
}
</style>
</head>
<body>

<!-- 顶栏 -->
<header class="topbar">
  <div class="brand"><span class="brand__mark">RUN</span><span>Blue</span></div>
  <div class="topbar__spacer"></div>
  <div class="gps-badge" id="gps-badge">GPS</div>
</header>

<div class="views">

  <!-- ========== 首页 ========== -->
  <section class="view is-active" id="view-home">
    <div class="view__inner">
      <div class="hero">
        <div class="hero__title">今天，也跑起来。</div>
        <p class="hero__desc">
          实时记录 GPS 轨迹、配速与步频，<br>跑完即刻生成完整报表。
        </p>
        <div class="hero__chips">
          <span class="chip" id="chip-geo">定位检测中…</span>
          <span class="chip" id="chip-motion">步频传感器待授权</span>
        </div>
        <button class="btn btn--primary btn--lg btn--block" id="btn-start">
          <span>开始跑步</span>
        </button>
      </div>

      <div class="section-title">历史记录</div>
      <div class="list" id="history-list"></div>
    </div>
  </section>

  <!-- ========== 跑步中 ========== -->
  <section class="view" id="view-run">
    <div class="view__inner">
      <div class="run-hero">
        <div class="run-dist"><span id="live-dist">0.00</span><em>km</em></div>
        <div class="run-status" id="run-status">
          <span class="dot"></span><span id="run-status-text">记录中</span>
        </div>
      </div>

      <div class="grid3">
        <div class="stat">
          <div class="stat__label">配速</div>
          <div class="stat__val" id="live-pace">--'--"</div>
          <div class="stat__unit">/km</div>
        </div>
        <div class="stat">
          <div class="stat__label">速度</div>
          <div class="stat__val" id="live-speed">0.0</div>
          <div class="stat__unit">km/h</div>
        </div>
        <div class="stat">
          <div class="stat__label">时长</div>
          <div class="stat__val" id="live-time">00:00</div>
          <div class="stat__unit">分:秒</div>
        </div>
      </div>

      <div class="grid3" style="margin-top:10px">
        <div class="stat">
          <div class="stat__label">步频</div>
          <div class="stat__val is-small" id="live-cadence">--</div>
          <div class="stat__unit">步/分</div>
        </div>
        <div class="stat">
          <div class="stat__label">步数</div>
          <div class="stat__val is-small" id="live-steps">0</div>
          <div class="stat__unit">步</div>
        </div>
        <div class="stat">
          <div class="stat__label">定位精度</div>
          <div class="stat__val is-small" id="live-acc">--</div>
          <div class="stat__unit">米</div>
        </div>
      </div>

      <div class="run-actions">
        <button class="btn btn--secondary btn--md" id="btn-pause"><span>暂停</span></button>
        <button class="btn btn--danger btn--md" id="btn-stop"><span>结束</span></button>
      </div>

      <p class="hint-text">
        保持屏幕常亮、应用在前台，GPS 记录更准确<br>
        建议在开阔地带使用，首次定位可能需要 10–30 秒
      </p>
    </div>
  </section>

  <!-- ========== 报表 ========== -->
  <section class="view" id="view-report">
    <div class="view__inner">
      <div class="report-head">
        <div class="report-title" id="rep-title">本次跑步</div>
        <div class="report-date" id="rep-date"></div>
      </div>

      <div class="hero-stat">
        <div class="hero-stat__num"><span id="rep-dist">0.00</span><em>km</em></div>
        <div class="hero-stat__meta">
          <span>用时 <b id="rep-duration">00:00</b></span>
          <span>均速 <b id="rep-avgspeed">0.0</b> km/h</span>
        </div>
      </div>

      <div class="grid2">
        <div class="stat">
          <div class="stat__label">平均配速</div>
          <div class="stat__val" id="rep-avgpace">--'--"</div>
          <div class="stat__unit">/km</div>
        </div>
        <div class="stat">
          <div class="stat__label">最高速度</div>
          <div class="stat__val" id="rep-maxspeed">0.0</div>
          <div class="stat__unit">km/h</div>
        </div>
      </div>
      <div class="grid3" style="margin-top:10px">
        <div class="stat">
          <div class="stat__label">步数</div>
          <div class="stat__val is-small" id="rep-steps">0</div>
          <div class="stat__unit">步</div>
        </div>
        <div class="stat">
          <div class="stat__label">平均步频</div>
          <div class="stat__val is-small" id="rep-cadence">--</div>
          <div class="stat__unit">步/分</div>
        </div>
        <div class="stat">
          <div class="stat__label">消耗</div>
          <div class="stat__val is-small" id="rep-cal">0</div>
          <div class="stat__unit">千卡</div>
        </div>
      </div>

      <div class="section-title">每公里分段</div>
      <div class="card card--static" style="padding:6px 14px" id="rep-splits"></div>

      <div class="section-title">GPS 轨迹</div>
      <div class="track-box" id="rep-track"></div>

      <div class="actions" id="rep-actions"></div>
    </div>
  </section>

</div>

<!-- Toast -->
<div class="toast" id="toast" role="status" aria-live="polite"></div>

<!-- 结束确认 -->
<div class="modal-overlay" id="modal-confirm" hidden>
  <div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
    <div class="modal-title" id="confirm-title">结束本次跑步？</div>
    <div class="modal-body">
      当前已记录 <b id="confirm-dist">0.00</b> km，<br>
      结束后将立即生成报表。
    </div>
    <div class="modal-foot">
      <button class="btn btn--secondary btn--md" id="btn-cancel-end"><span>继续跑</span></button>
      <button class="btn btn--danger btn--md" id="btn-confirm-end"><span>结束</span></button>
    </div>
  </div>
</div>

<script>
(function () {
  'use strict';

  /* ---------------- 工具 ---------------- */
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const now = () => performance.now();
  const LS_KEY = 'runblue.runs.v1';

  function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371000, toRad = Math.PI / 180;
    const dLat = (lat2 - lat1) * toRad;
    const dLon = (lon2 - lon1) * toRad;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
  }

  function fmtTime(ms) {
    const t = Math.max(0, Math.floor(ms / 1000));
    const h = Math.floor(t / 3600);
    const m = Math.floor((t % 3600) / 60);
    const s = t % 60;
    const p = n => String(n).padStart(2, '0');
    return h > 0 ? `${h}:${p(m)}:${p(s)}` : `${p(m)}:${p(s)}`;
  }

  function fmtPace(secPerKm) {
    if (!isFinite(secPerKm) || secPerKm <= 0 || secPerKm >= 3600) return "--'--\"";
    let m = Math.floor(secPerKm / 60);
    let s = Math.round(secPerKm - m * 60);
    if (s === 60) { m += 1; s = 0; }
    return `${m}'${String(s).padStart(2, '0')}"`;
  }

  function fmtDate(ts) {
    const d = new Date(ts);
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  function downsample(arr, max) {
    if (!arr || arr.length <= max) return (arr || []).slice();
    const step = arr.length / max;
    const out = [];
    for (let i = 0; i < max; i++) out.push(arr[Math.floor(i * step)]);
    out.push(arr[arr.length - 1]);
    return out;
  }

  /* ---------------- Toast ---------------- */
  let toastTimer = null;
  function toast(msg) {
    const el = $('#toast');
    el.textContent = msg;
    el.classList.add('is-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('is-visible'), 2400);
  }

  /* ---------------- 视图切换 ---------------- */
  function showView(name) {
    $$('.view').forEach(v => v.classList.toggle('is-active', v.id === 'view-' + name));
    const active = $('#view-' + name);
    if (active) active.scrollTop = 0;
    document.activeElement && document.activeElement.blur && document.activeElement.blur();
  }

  /* ---------------- 运行状态 ---------------- */
  const S = {
    phase: 'idle',          // idle | running | paused
    points: [],
    distance: 0,
    accumMs: 0,
    segStart: 0,
    startWall: 0,
    maxSpeed: 0,
    curSpeed: 0,
    smoothBuf: [],
    lastFix: null,
    watchId: null,
    timerId: null,
    steps: 0,
    stepTimes: [],
    splitKm: 0,
    lastSplitMs: 0,
    splits: [],
    gpsState: 'idle',
    gpsAccuracy: null,
    motionEnabled: false,
    wakeLock: null
  };

  function elapsedMs() {
    return S.accumMs + (S.phase === 'running' ? (now() - S.segStart) : 0);
  }

  function resetRun() {
    S.phase = 'idle';
    S.points = [];
    S.distance = 0;
    S.accumMs = 0;
    S.segStart = 0;
    S.startWall = 0;
    S.maxSpeed = 0;
    S.curSpeed = 0;
    S.smoothBuf = [];
    S.lastFix = null;
    S.steps = 0;
    S.stepTimes = [];
    S.splitKm = 0;
    S.lastSplitMs = 0;
    S.splits = [];
    S.gpsAccuracy = null;
  }

  /* ---------------- 传感器：运动权限（iOS 必须在手势中调用） ---------------- */
  let motionHandler = null;

  function requestMotionPermission() {
    if (typeof DeviceMotionEvent === 'undefined') return Promise.resolve(false);
    if (typeof DeviceMotionEvent.requestPermission === 'function') {
      return DeviceMotionEvent.requestPermission()
        .then(res => {
          if (res === 'granted') { attachMotion(); return true; }
          return false;
        })
        .catch(() => false);
    }
    attachMotion();
    return Promise.resolve(true);
  }

  function attachMotion() {
    if (motionHandler) { S.motionEnabled = true; return; }
    let gravity = 9.81;
    let lastPeak = 0;

    motionHandler = function (e) {
      if (S.phase !== 'running') return;
      const a = e.accelerationIncludingGravity;
      if (!a || a.x == null) return;
      const mag = Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
      gravity = gravity * 0.92 + mag * 0.08;      // 低通估计重力
      const lin = mag - gravity;                   // 线性加速度
      const t = now();
      if (lin > 1.6 && t - lastPeak > 250) {       // 峰值检测，最小步间隔 250ms
        lastPeak = t;
        S.steps++;
        S.stepTimes.push(t);
        if (S.stepTimes.length > 400) S.stepTimes.splice(0, 200);
      }
    };
    window.addEventListener('devicemotion', motionHandler, { passive: true });
    S.motionEnabled = true;
    updateHomeChips();
  }

  function cadenceNow() {
    const t = now();
    const recent = S.stepTimes.filter(x => t - x < 15000);
    if (recent.length < 4) return 0;
    const span = (t - recent[0]) / 1000;
    if (span <= 0.5) return 0;
    return Math.round((recent.length / span) * 60);
  }

  function avgCadence(totalMs) {
    if (!S.motionEnabled || S.steps < 10 || totalMs <= 0) return 0;
    return Math.round(S.steps / (totalMs / 60000));
  }

  /* ---------------- 屏幕常亮 ---------------- */
  async function requestWakeLock() {
    try {
      if ('wakeLock' in navigator) {
        S.wakeLock = await navigator.wakeLock.request('screen');
        S.wakeLock.addEventListener('release', () => { S.wakeLock = null; });
      }
    } catch (e) { /* 忽略 */ }
  }
  function releaseWakeLock() {
    if (S.wakeLock) { try { S.wakeLock.release(); } catch (e) {} S.wakeLock = null; }
  }
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && S.phase === 'running' && !S.wakeLock) {
      requestWakeLock();
    }
  });

  /* ---------------- GPS ---------------- */
  function startWatch() {
    if (!navigator.geolocation) {
      S.gpsState = 'error';
      updateGpsBadge();
      toast('当前浏览器不支持定位');
      return;
    }
    S.gpsState = 'waiting';
    updateGpsBadge();
    S.watchId = navigator.geolocation.watchPosition(onFix, onGeoError, {
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: 20000
    });
  }

  function stopWatch() {
    if (S.watchId != null) {
      navigator.geolocation.clearWatch(S.watchId);
      S.watchId = null;
    }
  }

  function onGeoError(err) {
    S.gpsState = 'error';
    updateGpsBadge();
    let msg = '定位失败';
    if (err.code === 1) msg = '定位权限被拒绝\n请在设置中允许此站点访问位置';
    else if (err.code === 2) msg = '无法获取定位信号\n请到开阔地带重试';
    else if (err.code === 3) msg = '定位超时，请检查网络与信号';
    toast(msg);
  }

  function onFix(pos) {
    const c = pos.coords;
    S.gpsState = 'ok';
    S.gpsAccuracy = c.accuracy;
    updateGpsBadge();

    const t = now();
    const acc = typeof c.accuracy === 'number' ? c.accuracy : 999;

    // 暂停 / 未跑步时只维护基准点，不累加距离
    if (S.phase !== 'running') {
      S.lastFix = { lat: c.latitude, lng: c.longitude, t: t, acc: acc };
      return;
    }

    // 精度过滤
    if (acc > 50) return;

    const p = { lat: c.latitude, lng: c.longitude, t: t, acc: acc };

    if (!S.lastFix) {
      S.lastFix = p;
      S.points.push(p);
      return;
    }

    const dt = (t - S.lastFix.t) / 1000;
    if (dt < 0.6) return;

    const d = haversine(S.lastFix.lat, S.lastFix.lng, p.lat, p.lng);
    const v = d / dt; // m/s

    // 明显跳点（瞬时速度 > 43km/h 且位移较大）
    if (d > 5 && v > 12) return;
    // 微小抖动，忽略但保留基准点以累积真实位移
    if (d < 1.2 && dt < 8) return;

    S.distance += d;
    S.lastFix = p;
    S.points.push(p);

    // 速度平滑（最近 8 秒滑动平均）
    if (v <= 12) {
      S.smoothBuf.push({ v: v, t: t });
      while (S.smoothBuf.length && t - S.smoothBuf[0].t > 12000) S.smoothBuf.shift();
      const recent = S.smoothBuf.filter(x => t - x.t <= 8000);
      if (recent.length) {
        S.curSpeed = recent.reduce((s, x) => s + x.v, 0) / recent.length;
        if (S.curSpeed > S.maxSpeed) S.maxSpeed = S.curSpeed;
      }
    }

    checkSplit();
  }

  function checkSplit() {
    const kmIdx = Math.floor(S.distance / 1000);
    if (kmIdx > S.splitKm) {
      const t = elapsedMs();
      S.splits.push({ km: kmIdx, ms: t - S.lastSplitMs });
      S.lastSplitMs = t;
      S.splitKm = kmIdx;
    }
  }

  function updateGpsBadge() {
    const el = $('#gps-badge');
    let cls = '', label = 'GPS';
    if (S.gpsState === 'ok') {
      cls = 'is-ok';
      label = S.gpsAccuracy != null ? '±' + Math.round(S.gpsAccuracy) + 'm' : 'GPS';
    } else if (S.gpsState === 'waiting') {
      cls = 'is-wait'; label = '定位中';
    } else if (S.gpsState === 'error') {
      cls = 'is-err'; label = '无信号';
    }
    el.className = 'gps-badge ' + cls;
    el.textContent = label;
  }

  /* ---------------- 计时与实时刷新 ---------------- */
  function startTimer() {
    clearInterval(S.timerId);
    S.timerId = setInterval(updateRunUI, 200);
  }

  function updateRunUI() {
    const ms = elapsedMs();
    const km = S.distance / 1000;

    $('#live-dist').textContent = km.toFixed(2);
    $('#live-time').textContent = fmtTime(ms);
    $('#live-pace').textContent = fmtPace(km > 0.005 ? (ms / 1000) / km : Infinity);
    $('#live-speed').textContent = (S.curSpeed * 3.6).toFixed(1);

    const cad = cadenceNow();
    $('#live-cadence').textContent = S.motionEnabled && cad > 0 ? cad : '--';
    $('#live-steps').textContent = S.motionEnabled ? S.steps : '--';
    $('#live-acc').textContent = S.gpsAccuracy != null ? Math.round(S.gpsAccuracy) : '--';

    const st = $('#run-status');
    const stt = $('#run-status-text');
    if (S.phase === 'paused') {
      st.classList.add('is-paused');
      stt.textContent = '已暂停';
    } else {
      st.classList.remove('is-paused');
      stt.textContent = S.gpsState === 'ok' ? '记录中' : '等待定位…';
    }
  }

  /* ---------------- 开始 / 暂停 / 结束 ---------------- */
  async function startRun() {
    resetRun();
    showView('run');

    // 关键：传感器权限请求必须在用户手势的同步阶段发起
    const motionPromise = requestMotionPermission();

    S.phase = 'running';
    S.startWall = Date.now();
    S.segStart = now();
    S.lastSplitMs = 0;

    startTimer();
    startWatch();
    requestWakeLock();
    updateRunUI();

    await motionPromise;
    if (!S.motionEnabled) {
      toast('未获得运动传感器权限\n步频与步数将不可用');
    }
    updateHomeChips();
  }

  function togglePause() {
    if (S.phase === 'running') {
      S.accumMs = elapsedMs();
      S.phase = 'paused';
      toast('已暂停');
    } else if (S.phase === 'paused') {
      S.segStart = now();
      S.phase = 'running';
      S.lastFix = null;      // 避免恢复后把暂停期间的位移计入
      toast('继续记录');
    }
    updateRunUI();
  }

  function askStop() {
    if (S.phase === 'idle') return;
    $('#confirm-dist').textContent = (S.distance / 1000).toFixed(2);
    $('#modal-confirm').hidden = false;
  }

  function finishRun() {
    $('#modal-confirm').hidden = true;
    if (S.phase === 'running') S.accumMs += now() - S.segStart;
    S.phase = 'idle';

    clearInterval(S.timerId);
    stopWatch();
    releaseWakeLock();

    const data = buildReportData();
    renderReport(data, false);
    showView('report');
    updateGpsBadge();
  }

  /* ---------------- 报表数据 ---------------- */
  function buildReportData() {
    const dur = S.accumMs;
    const dist = S.distance;
    const km = dist / 1000;
    const avgSpeedMs = dur > 0 ? dist / (dur / 1000) : 0;
    const avgPaceSec = km > 0.005 ? (dur / 1000) / km : 0;
    const cadence = avgCadence(dur);
    const calories = Math.round(km * 62 * 1.036);

    return {
      id: Date.now(),
      date: S.startWall || Date.now(),
      distance: dist,
      duration: dur,
      avgSpeed: avgSpeedMs * 3.6,
      avgPace: avgPaceSec,
      maxSpeed: S.maxSpeed * 3.6,
      steps: S.motionEnabled ? S.steps : 0,
      cadence: cadence,
      calories: calories,
      splits: S.splits.slice(),
      track: downsample(S.points, 300).map(p => [
        +p.lat.toFixed(5),
        +p.lng.toFixed(5)
      ])
    };
  }

  function renderReport(data, isHistory) {
    const km = data.distance / 1000;

    $('#rep-title').textContent = isHistory ? '历史记录' : '本次跑步';
    $('#rep-date').textContent = fmtDate(data.date);
    $('#rep-dist').textContent = km.toFixed(2);
    $('#rep-duration').textContent = fmtTime(data.duration);
    $('#rep-avgspeed').textContent = (data.avgSpeed || 0).toFixed(1);
    $('#rep-avgpace').textContent = fmtPace(data.avgPace);
    $('#rep-maxspeed').textContent = (data.maxSpeed || 0).toFixed(1);
    $('#rep-steps').textContent = data.steps || 0;
    $('#rep-cadence').textContent = data.cadence || '--';
    $('#rep-cal').textContent = data.calories || 0;

    renderSplits(data);
    renderTrack(data.track);

    // 底部按钮
    const box = $('#rep-actions');
    box.innerHTML = '';
    if (isHistory) {
      box.innerHTML = '<button class="btn btn--primary btn--md" id="btn-back-home"><span>返回首页</span></button>';
      $('#btn-back-home').addEventListener('click', () => {
        renderHistory();
        showView('home');
      });
    } else {
      box.innerHTML =
        '<button class="btn btn--primary btn--md" id="btn-save"><span>保存记录</span></button>' +
        '<button class="btn btn--secondary btn--md" id="btn-again"><span>再来一次</span></button>';
      $('#btn-save').addEventListener('click', function () {
        saveRun(data);
        this.disabled = true;
        this.querySelector('span').textContent = '已保存';
        toast('记录已保存');
      });
      $('#btn-again').addEventListener('click', () => {
        renderHistory();
        startRun();
      });
    }
  }

  function renderSplits(data) {
    const box = $('#rep-splits');
    const splits = data.splits || [];
    const rows = [];

    splits.forEach((sp, i) => {
      const paceSec = sp.ms / 1000; // 每公里秒数
      rows.push({ idx: i + 1, ms: sp.ms, paceSec: paceSec });
    });

    // 最后不足 1km 的段落
    const coveredKm = splits.length;
    const remainKm = data.distance / 1000 - coveredKm;
    if (remainKm > 0.05) {
      const usedMs = splits.reduce((s, x) => s + x.ms, 0);
      const remainMs = Math.max(0, data.duration - usedMs);
      rows.push({
        idx: splits.length + 1,
        ms: remainMs,
        paceSec: remainMs / 1000 / remainKm,
        partial: remainKm
      });
    }

    if (!rows.length) {
      box.innerHTML = '<div class="empty" style="border:0;background:transparent;padding:18px">距离不足 1 公里，暂无分段数据</div>';
      return;
    }

    const maxPace = Math.max.apply(null, rows.map(r => r.paceSec).filter(p => isFinite(p) && p > 0)) || 1;

    box.innerHTML = rows.map(r => {
      const pct = Math.max(8, Math.min(100, (r.paceSec / maxPace) * 100));
      const label = r.partial != null
        ? (r.partial * 1000 | 0) + 'm'
        : 'KM ' + r.idx;
      return '<div class="split-row">' +
        '<div class="split-row__idx">' + label + '</div>' +
        '<div class="split-row__bar" style="width:' + pct.toFixed(1) + '%"></div>' +
        '<div class="split-row__time">' + fmtPace(r.paceSec) +
        '<small>' + fmtTime(r.ms) + '</small></div>' +
        '</div>';
    }).join('');
  }

  function renderTrack(track) {
    const box = $('#rep-track');
    if (!track || track.length < 2) {
      box.innerHTML = '<div class="empty" style="border:0;background:transparent;padding:26px">轨迹点不足，无法绘制路线</div>';
      return;
    }
    const lats = track.map(p => p[0]);
    const lngs = track.map(p => p[1]);
    const minLat = Math.min.apply(null, lats), maxLat = Math.max.apply(null, lats);
    const minLng = Math.min.apply(null, lngs), maxLng = Math.max.apply(null, lngs);
    const midLat = (minLat + maxLat) / 2;
    const cosLat = Math.cos(midLat * Math.PI / 180) || 1;

    const W = 320, H = 200, PAD = 16;
    const spanX = Math.max((maxLng - minLng) * cosLat, 1e-9);
    const spanY = Math.max(maxLat - minLat, 1e-9);
    const scale = Math.min((W - PAD * 2) / spanX, (H - PAD * 2) / spanY);
    const ox = (W - spanX * scale) / 2;
    const oy = (H - spanY * scale) / 2;

    const pts = track.map(function (pt) {
      const x = ox + (pt[1] - minLng) * cosLat * scale;
      const y = H - oy - (pt[0] - minLat) * scale;
      return x.toFixed(1) + ',' + y.toFixed(1);
    });

    const first = pts[0].split(',');
    const last = pts[pts.length - 1].split(',');

    box.innerHTML =
      '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet" role="img" aria-label="跑步轨迹">' +
      '<defs>' +
      '<linearGradient id="tg" x1="0" y1="0" x2="1" y2="1">' +
      '<stop offset="0" stop-color="#21a5e3"/><stop offset="1" stop-color="#4454F8"/>' +
      '</linearGradient>' +
      '<pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">' +
      '<path d="M20 0 L0 0 0 20" fill="none" stroke="#EDEDED" stroke-width="1"/>' +
      '</pattern>' +
      '</defs>' +
      '<rect width="' + W + '" height="' + H + '" fill="url(#grid)" opacity=".7"/>' +
      '<polyline points="' + pts.join(' ') + '" fill="none" stroke="url(#tg)" ' +
      'stroke-width="3" stroke-linejoin="round" stroke-linecap="round" opacity=".95"/>' +
      '<circle cx="' + first[0] + '" cy="' + first[1] + '" r="4.5" fill="#169B5B" stroke="#fff" stroke-width="2"/>' +
      '<circle cx="' + last[0] + '" cy="' + last[1] + '" r="4.5" fill="#F21B28" stroke="#fff" stroke-width="2"/>' +
      '</svg>';
  }

  /* ---------------- 本地存储 ---------------- */
  function loadRuns() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch (e) { return []; }
  }

  function saveRun(data) {
    const runs = loadRuns();
    runs.unshift(data);
    // 只保留最近 30 条，防止存储超限
    while (runs.length > 30) runs.pop();
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(runs));
    } catch (e) {
      // 存储超限时剥离轨迹再试
      try {
        const slim = runs.map(r => Object.assign({}, r, { track: [] }));
        localStorage.setItem(LS_KEY, JSON.stringify(slim));
      } catch (e2) { toast('存储空间不足，未能保存'); }
    }
  }

  const THUMB_COLORS = [
    ['#ABD7FF', '#BEC0EC'],
    ['#8FD8F5', '#4FA9FF'],
    ['#BEC0EC', '#8C9BF7'],
    ['#A8E6CF', '#7FC8E8'],
    ['#FFD9A0', '#ABD7FF'],
    ['#C7B9F5', '#8FD8F5']
  ];

  function renderHistory() {
    const box = $('#history-list');
    const runs = loadRuns();
    if (!runs.length) {
      box.innerHTML = '<div class="empty">还没有记录，开始你的第一次跑步吧</div>';
      return;
    }
    box.innerHTML = runs.map(function (r, i) {
      const c = THUMB_COLORS[i % THUMB_COLORS.length];
      return '<div class="card list-item" data-id="' + r.id + '" role="button" tabindex="0">' +
        '<div class="list-item__thumb" style="--c1:' + c[0] + ';--c2:' + c[1] + '"></div>' +
        '<div>' +
        '<div class="list-item__title">' + (r.distance / 1000).toFixed(2) + '<em>km</em></div>' +
        '<div class="list-item__meta">' + fmtDate(r.date) + ' · ' + fmtTime(r.duration) +
        ' · ' + fmtPace(r.avgPace) + '/km</div>' +
        '</div></div>';
    }).join('');
  }

  function updateHomeChips() {
    const geo = $('#chip-geo');
    const mot = $('#chip-motion');

    if (S.gpsState === 'ok') {
      geo.textContent = 'GPS 已就绪 ±' + Math.round(S.gpsAccuracy || 0) + 'm';
      geo.className = 'chip chip--ok';
    } else if (S.gpsState === 'error') {
      geo.textContent = '定位不可用';
      geo.className = 'chip chip--warn';
    } else {
      geo.textContent = '定位待授权';
      geo.className = 'chip';
    }

    if (S.motionEnabled) {
      mot.textContent = '步频传感器已开启';
      mot.className = 'chip chip--ok';
    } else {
      mot.textContent = '开始后授权步频传感器';
      mot.className = 'chip';
    }
  }

  /* ---------------- 事件绑定 ---------------- */
  $('#btn-start').addEventListener('click', startRun);
  $('#btn-pause').addEventListener('click', togglePause);
  $('#btn-stop').addEventListener('click', askStop);
  $('#btn-cancel-end').addEventListener('click', () => { $('#modal-confirm').hidden = true; });
  $('#btn-confirm-end').addEventListener('click', finishRun);

  // 点击遮罩关闭确认框
  $('#modal-confirm').addEventListener('click', function (e) {
    if (e.target === this) this.hidden = true;
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') $('#modal-confirm').hidden = true;
  });

  // 历史记录点击 / 键盘
  $('#history-list').addEventListener('click', function (e) {
    const item = e.target.closest('.list-item');
    if (!item) return;
    const runs = loadRuns();
    const r = runs.filter(x => String(x.id) === item.dataset.id)[0];
    if (r) { renderReport(r, true); showView('report'); }
  });
  $('#history-list').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') {
      const item = e.target.closest('.list-item');
      if (item) { e.preventDefault(); item.click(); }
    }
  });

  // 首页定位探测（非必须，失败静默）
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        S.gpsState = 'ok';
        S.gpsAccuracy = pos.coords.accuracy;
        updateGpsBadge();
        updateHomeChips();
      },
      function () {
        if (S.gpsState !== 'ok') { S.gpsState = 'idle'; updateHomeChips(); }
      },
      { enableHighAccuracy: true, maximumAge: 30000, timeout: 12000 }
    );
  }

  // 离开页面时保存提示
  window.addEventListener('beforeunload', function (e) {
    if (S.phase === 'running' || S.phase === 'paused') {
      e.preventDefault();
      e.returnValue = '跑步正在记录中，确定离开吗？';
      return e.returnValue;
    }
  });

  /* ---------------- 初始化 ---------------- */
  renderHistory();
  updateHomeChips();
  updateGpsBadge();
})();
</script>
</body>
</html>
```

OK啊，这波跑完了来看看我成绩

> **走了0.32km，配速5'07''，12.1km/h**

比慢跑快？！**这数据不对吧？！**有点怀疑数据的准确性，毕竟**宿舍走廊GPS精度没外面那么好**。我看最终的轨迹是歪七扭八的。

## 从宿舍跑到金属探测器

之后我注意到浏览器可以调用的传感器中还有**磁场强度**，所以我就让DeepSeek做了一个Sample给我看看：

> <u>我</u>：HTML 可以做金属探测器吗？
>
> <u>DeepSeek</u>：......
>
> <u>我</u>：简单做一个，兼容 Safari
>
> <u>DeepSeek</u>：Safari <span class="hover-hint">Magnetometer<span class="hover-hint__tooltip"><span class="hint-title">Magnetometer</span>Generic Sensor API中的磁力计接口，本可读取原始磁场强度（µT）。Safari拒绝实现该接口，核心原因之一是磁场数据可用于设备指纹识别——不同设备的磁传感器噪声特征具有可区分性。文章中的“金属探测器”因此无法使用原始磁力计，只能退而求其次用指南针朝向的偏转来“间接探测”。<br><br>文章提到Safari不能计步、不能震动。Vibration API（navigator.vibrate()）在Android Chrome上可用，但Safari在macOS、iPadOS、iOS的所有版本中均未实现 navigator.vibrate，也没有开启它的flag。计步器同理：Web端没有标准计步接口，Safari连运动传感器的原始访问都限制重重，计步自然无从谈起。</span></span>，只能走 `DeviceOrientation` 的指南针模式，**监测方向角异常偏转**，做成一个“指南针模式金属探测”演示页。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Safari 简易金属探测器（指南针模式）</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0a0a0a; color: #e0e0e0;
            min-height: 100vh; display: flex; flex-direction: column;
            align-items: center; justify-content: center; padding: 20px;
            user-select: none; -webkit-user-select: none;
            transition: background 0.15s ease;
        }
        body.alert { background: #2a0a0a; }
        h1 { font-size: 18px; font-weight: 600; margin-bottom: 6px; letter-spacing: 0.5px; }
        .subtitle { font-size: 12px; color: #777; margin-bottom: 30px; text-align: center; line-height: 1.5; }

        #status {
            font-size: 15px; padding: 10px 20px; border-radius: 20px;
            background: #1a1a1a; color: #888; margin-bottom: 24px;
            transition: all 0.3s ease; text-align: center; min-height: 42px;
            display: flex; align-items: center; justify-content: center;
        }
        #status.active { background: #0d2a1a; color: #4ade80; }
        #status.alert { background: #3a0d0d; color: #f87171; font-weight: 600; }

        .readout {
            display: flex; gap: 24px; margin-bottom: 30px;
            font-variant-numeric: tabular-nums;
        }
        .readout-item { text-align: center; }
        .readout-item .label { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
        .readout-item .value { font-size: 28px; font-weight: 300; color: #fff; min-width: 90px; }
        .readout-item .value.alert { color: #f87171; font-weight: 600; }
        .readout-item .unit { font-size: 12px; color: #555; margin-left: 2px; }

        button {
            padding: 14px 40px; font-size: 16px; font-weight: 600;
            border: none; border-radius: 30px; cursor: pointer;
            background: #2563eb; color: #fff; margin-bottom: 20px;
            transition: background 0.2s; -webkit-tap-highlight-color: transparent;
        }
        button:active { background: #1d4ed8; }
        button:disabled { background: #333; color: #666; cursor: default; }

        .hint { font-size: 12px; color: #555; text-align: center; line-height: 1.7; max-width: 320px; }
        .hint strong { color: #888; }
    </style>
</head>
<body>

<h1>指南针模式金属探测</h1>
<p class="subtitle">
    Safari 不支持原始磁力计数据。<br>
    本工具通过监测方向角的异常偏转来间接感应铁磁性金属。
</p>

<div id="status">点击下方按钮开始</div>

<div class="readout">
    <div class="readout-item">
        <div class="label">当前方向</div>
        <div class="value" id="headingDisplay">--<span class="unit">°</span></div>
    </div>
    <div class="readout-item">
        <div class="label">偏转量</div>
        <div class="value" id="deviationDisplay">--<span class="unit">°</span></div>
    </div>
</div>

<button id="startBtn">开始探测</button>

<p class="hint">
    <strong>使用方法：</strong>将手机背面靠近待测表面，缓慢平移，<strong>不要转动手机</strong>。
    如果偏转量突然飙升并持续，说明附近可能有铁磁性金属（铁、镍、钴）。
    金、银、铜、铝等非磁性金属无法被感应。
</p>

<script>
    (function () {
        'use strict';

        const statusEl = document.getElementById('status');
        const headingDisplay = document.getElementById('headingDisplay');
        const deviationDisplay = document.getElementById('deviationDisplay');
        const startBtn = document.getElementById('startBtn');
        const body = document.body;

        // ---- 状态 ----
        let running = false;
        let baselineHeading = null;          // 基准方向（缓慢跟踪）
        let baselineSamples = 0;
        let lastRawHeading = null;
        let deviation = 0;                   // 当前偏转量（度）
        let deviationSmooth = 0;             // 平滑后的偏转量
        let alertFrames = 0;                 // 连续超阈值帧数
        let lastUpdate = 0;

        // ---- 参数 ----
        const BASELINE_ALPHA = 0.02;         // 基准方向的缓慢跟随系数（越小越慢）
        const DEVIATION_SMOOTH = 0.3;        // 偏转量平滑系数
        const ALERT_THRESHOLD_DEG = 12;      // 偏转超过多少度触发警报（可根据环境调整）
        const ALERT_CONFIRM_FRAMES = 8;      // 连续多少帧超阈值才确认警报（防抖）
        const RESET_FRAMES = 30;             // 连续多少帧无偏转后重置警报

        // ---- 工具函数 ----
        function angleDiff(a, b) {
            // 返回 a - b 的最短角差，结果在 [-180, 180]
            let d = a - b;
            while (d > 180) d -= 360;
            while (d < -180) d += 360;
            return d;
        }

        function updateUI(rawHeading) {
            if (rawHeading === null || isNaN(rawHeading)) {
                headingDisplay.textContent = '--';
                deviationDisplay.textContent = '--';
                return;
            }

            headingDisplay.innerHTML = rawHeading.toFixed(1) + '<span class="unit">°</span>';

            if (baselineHeading === null) {
                deviationDisplay.innerHTML = '--';
                return;
            }

            const absDev = Math.abs(deviationSmooth);
            const isAlert = alertFrames >= ALERT_CONFIRM_FRAMES;
            deviationDisplay.innerHTML = absDev.toFixed(1) + '<span class="unit">°</span>';
            deviationDisplay.className = 'value' + (isAlert ? ' alert' : '');
        }

        // ---- 核心处理 ----
        function handleOrientation(event) {
            if (!running) return;

            // iOS Safari 提供 webkitCompassHeading（0-360，正北为0）
            // 其他浏览器可能只有 alpha（也是0-360，但0不一定对准正北）
            let heading = null;
            if (event.webkitCompassHeading !== undefined && event.webkitCompassHeading !== null) {
                heading = event.webkitCompassHeading;
            } else if (event.alpha !== null && event.alpha !== undefined) {
                heading = (360 - event.alpha) % 360; // alpha 的0方向与指南针相反
            }

            if (heading === null || isNaN(heading)) {
                return;
            }

            lastRawHeading = heading;

            // 初始化基准
            if (baselineHeading === null) {
                baselineHeading = heading;
                baselineSamples = 1;
                updateUI(heading);
                return;
            }

            // 基准缓慢跟随（只跟随“正常”的小幅变化，不跟随突然的大偏转）
            const rawDev = angleDiff(heading, baselineHeading);
            const absRawDev = Math.abs(rawDev);

            // 如果偏转不大，让基准慢慢跟上（适应缓慢转动/环境漂移）
            if (absRawDev < ALERT_THRESHOLD_DEG * 0.8) {
                baselineHeading += angleDiff(heading, baselineHeading) * BASELINE_ALPHA;
                baselineHeading = (baselineHeading + 360) % 360;
                baselineSamples++;
            }

            // 计算平滑后的偏转量
            deviation = angleDiff(heading, baselineHeading);
            deviationSmooth = deviationSmooth * (1 - DEVIATION_SMOOTH) + deviation * DEVIATION_SMOOTH;

            const absSmoothDev = Math.abs(deviationSmooth);

            // 警报逻辑：连续超阈值才确认，连续无偏转才重置
            if (absSmoothDev > ALERT_THRESHOLD_DEG) {
                alertFrames = Math.min(alertFrames + 1, ALERT_CONFIRM_FRAMES + 30);
            } else {
                alertFrames = Math.max(alertFrames - 2, 0);
            }

            const isAlert = alertFrames >= ALERT_CONFIRM_FRAMES;

            // 更新 UI
            statusEl.textContent = isAlert
                ? '⚠️ 检测到磁场异常偏转'
                : '监测中 — 缓慢平移手机';
            statusEl.className = isAlert ? 'alert' : 'active';
            body.classList.toggle('alert', isAlert);

            updateUI(heading);
        }

        // ---- 启动 ----
        async function start() {
            if (running) return;

            // 检查 DeviceOrientationEvent 是否存在
            if (!window.DeviceOrientationEvent) {
                statusEl.textContent = '此设备/浏览器不支持方向传感器';
                statusEl.className = 'alert';
                return;
            }

            // iOS 13+ 需要在用户手势中请求权限
            if (typeof DeviceOrientationEvent.requestPermission === 'function') {
                try {
                    const permission = await DeviceOrientationEvent.requestPermission();
                    if (permission !== 'granted') {
                        statusEl.textContent = '传感器权限被拒绝，无法探测';
                        statusEl.className = 'alert';
                        return;
                    }
                } catch (e) {
                    statusEl.textContent = '权限请求失败：' + e.message;
                    statusEl.className = 'alert';
                    return;
                }
            }

            // 重置状态
            baselineHeading = null;
            deviationSmooth = 0;
            alertFrames = 0;
            running = true;
            startBtn.textContent = '探测中…';
            startBtn.disabled = true;

            statusEl.textContent = '正在初始化，请保持手机静止…';
            statusEl.className = 'active';

            window.addEventListener('deviceorientation', handleOrientation, true);

            // 如果 3 秒内没有收到任何数据，给出提示
            setTimeout(() => {
                if (running && lastRawHeading === null) {
                    statusEl.textContent = '未收到传感器数据。请确保在 HTTPS 页面中打开，并已授权运动与方向访问。';
                    statusEl.className = 'alert';
                }
            }, 3000);
        }

        // ---- 绑定事件 ----
        startBtn.addEventListener('click', start);

        // 页面隐藏时暂停处理，节省电量
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                running = false;
                startBtn.textContent = '继续探测';
                startBtn.disabled = false;
                window.removeEventListener('deviceorientation', handleOrientation, true);
            }
        });

    })();
</script>
</body>
</html>
```

运行起来发现欸这啥，看来这是DeepSeek想到的方案。（怪我之前没有看前面DeepSeek说的咯）

> *Safari 拒绝 `Magnetometer` API 是出于隐私考虑（磁场数据可用于设备指纹识别）*

## 从金属探测器到放弃

之后我就去了解了下Safari可以获取设备的哪些有关传感器的信息：

> *加速度计、陀螺仪、指南针、GPS*

啊这，怎么这么点？！

> [!note]
>
> 为了避免用户被轻易追踪，Safari 主动拒绝实现了大量能够访问敏感硬件信息的 Web API。

> <u>我</u>：......回来后就开始折腾研究网页可以获取手机多少传感器信息，只能说safari为了安全砍掉了太多功能
>
> <u><span class="hover-hint">凯伊<span class="hover-hint__tooltip"><span class="hint-title">天童凯伊/天童Kei（柯伊/Kei）</span>柯伊是手机游戏《蔚蓝档案》及其衍生作品中的角色。性格傲娇。文章作者曾在AstrBot中部署QQ机器人并赋予其“凯伊”人格，详细见之前的文章《QQ机器人二周目：从立绘对话框到跨次元陪伴》</span></span></u>：......
>
> ​	至于 Safari 那事——
> ​	（别过脸）安全保守归保守，不过你说得对，砍得也太狠了点。

然后我又继续了解了Safari的种种限制：

> <u>我</u>：Safari 可以访问计步器吗
>
> *不能*
>
> <u>我</u>：Safari 可以令设备震动吗
>
> *不能*
>
> <u>我</u>：安卓浏览器可以令设备震动吗
>
> ***可以***

我也是用上<span class="hover-hint">残血版<span class="hover-hint__tooltip"><span class="hint-title">Safari的“残血版”传感器策略</span>文章的核心吐槽：出于隐私与防指纹追踪的考虑，Safari主动拒绝实现了大量Web传感器API。具体包括：不支持Generic Sensor API全系、devicemotion/deviceorientation 默认关闭且需手势授权、不支持 navigator.vibrate、无计步器接口。相比之下，Chromium内核浏览器对传感器的覆盖要完整得多。</span></span>浏览器了。就这样吧，想给我的网站的/tools目录做一个引导页面，但是我懒得做，还是下次再做吧。

> 前面的区域，以后再来探索吧