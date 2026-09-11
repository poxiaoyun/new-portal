/* =========================================================================
   联系我们页（/contact/）的两个交互：需求表单 + 位置地图。

   表单走 web3forms —— 纯前端收件服务，不需要后端。POST 到
   https://api.web3forms.com/submit，成功/失败都留在本页（用 AJAX 而不是让
   浏览器跳走，这样能落 .tf-company-form-success / -error 两个槽位）。
   **access_key 由 build_contact.py 写成显式占位符**，见那边的注释。

   地图走腾讯地图 GL JS。合规要求：只能用腾讯 / 高德 / 百度 / 天地图，不能用
   Google / OSM / Mapbox，坐标必须 GCJ-02。两种加载模式由 build_contact.py 决定，
   本文件不关心区别（只看 window.TMap 在不在）：
     · 线上：SDK 带 key 参数直连（key 由 CI 从 GitHub Secret 注入）
     · 本机：走官方 `_TMapSecurityConfig` 代理，前端零 key
   两种模式都失败时退到降级卡（showAddressCard），不传 mapStyleId —— 自定义样式
   未开通时会让底图变灰。
   ========================================================================= */
(function () {
  'use strict';

  /* ------------------------------------------------------------- 位置 */
  /* 成都高新区银泰悦坊（益州大道中段 1999 号），GCJ-02 火星坐标 —— 与旧站
     <meta name="ICBM" content="30.540905, 104.05972"> 里的那一对一致。
     腾讯地图用 GCJ-02，直接填，不要做 WGS-84 转换。 */
  var OFFICE = { lat: 30.540905, lng: 104.05972 };
  var OFFICE_NAME = '成都破晓石科技有限公司';
  var OFFICE_ADDR = '四川省成都市高新区银泰悦坊 17 号楼 9 层';

  /* 地图标注。用内联 SVG 的 data URI：腾讯的 demo 图片只授权给官方示例用，
     不能引用 mapapi.qq.com 下的路径。 */
  var PIN_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36">' +
    '<path d="M14 1C7.4 1 2 6.4 2 13c0 8.6 12 22 12 22s12-13.4 12-22c0-6.6-5.4-12-12-12z" ' +
    'fill="#9fe9ff" stroke="#071013" stroke-width="1.5"/>' +
    '<circle cx="14" cy="13" r="4.4" fill="#071013"/></svg>';

  /* --------------------------------------------------------- 表单提交 */
  function initForm() {
    var form = document.querySelector('.tf-company-contact-form');
    if (!form) return;
    var ok = form.querySelector('.tf-company-form-success');
    var err = form.querySelector('.tf-company-form-error');
    var button = form.querySelector('button[type="submit"]');
    var idleLabel = button ? button.innerHTML : '';

    function say(node, text) {
      if (ok) { ok.hidden = true; ok.textContent = ''; }
      if (err) { err.hidden = true; err.textContent = ''; }
      if (!node) return;
      node.textContent = text;
      node.hidden = false;
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (!form.reportValidity()) return;
      if (button) { button.disabled = true; button.textContent = '提交中…'; }
      say(null, '');

      fetch(form.action, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: new FormData(form)
      }).then(function (response) {
        return response.json().catch(function () { return {}; });
      }).then(function (data) {
        if (data && data.success) {
          form.reset();
          say(ok, '已收到，我们会在 1 个工作日内回复。需要加急请在邮件里注明。');
        } else {
          say(err, (data && data.message) ||
            '提交失败，请稍后重试，或直接发邮件到 support@xiaoshiai.cn。');
        }
      }).catch(function () {
        say(err, '网络异常，提交未送达。请直接发邮件到 support@xiaoshiai.cn。');
      }).then(function () {
        if (button) { button.disabled = false; button.innerHTML = idleLabel; }
      });
    });
  }

  /* ------------------------------------------------------------- 地图 */
  function mapFailed() {
    /* 两种失败：SDK 请求本身失败（onerror 打标），或脚本跑到了但没挂上 TMap。
       第二种才是线上常态 —— 代理 serviceHost 指向本机，线上必然连不上。 */
    return window.__TF_TMAP_FAILED__ === true || typeof window.TMap === 'undefined';
  }

  /* 兜底：不画地图，改给一张地址卡。
     链接用腾讯地图网页版的 marker 参数，不需要 key —— 别在这里塞 API key。 */
  function showAddressCard() {
    var box = document.getElementById('contact-map');
    var card = document.querySelector('.tf-contact-map-fallback');
    if (box) box.hidden = true;
    if (card) card.hidden = false;
    var link = card && card.querySelector('a[data-map-link]');
    if (link) {
      link.href = 'https://map.qq.com/?type=marker&isopeninfowin=1&markertype=1' +
        '&pointx=' + OFFICE.lng + '&pointy=' + OFFICE.lat +
        '&name=' + encodeURIComponent(OFFICE_NAME) +
        '&addr=' + encodeURIComponent(OFFICE_ADDR);
    }
  }

  function initMap() {
    var box = document.getElementById('contact-map');
    if (!box) return;
    if (mapFailed()) { showAddressCard(); return; }
    try {
      var center = new TMap.LatLng(OFFICE.lat, OFFICE.lng);
      var map = new TMap.Map(box, { center: center, zoom: 16, pitch: 0, rotation: 0 });
      /* 图层类带 Multi 前缀，样式类不带 —— TMap.MultiMarker + TMap.MarkerStyle。
         这里不传 mapStyleId：自定义样式要在控制台单独开通，默认 key 用不了。 */
      new TMap.MultiMarker({
        map: map,
        styles: {
          office: new TMap.MarkerStyle({
            width: 28, height: 36, anchor: { x: 14, y: 36 },
            src: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(PIN_SVG)
          })
        },
        geometries: [{ id: 'office', styleId: 'office', position: center }]
      });
    } catch (error) {
      showAddressCard();
    }
  }

  function boot() { initForm(); initMap(); }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
