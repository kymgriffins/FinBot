// Poll /api/providers/status and update sidebar provider statuses
(function () {
  async function fetchStatuses() {
    try {
      const res = await fetch('/api/providers/status');
      if (!res.ok) return;
      const data = await res.json();
      if (data.status !== 'success') return;
      const providers = data.providers || {};
      // find or create status container
      let container = document.getElementById('provider-status-container');
      if (!container) {
        container = document.createElement('div');
        container.id = 'provider-status-container';
        container.className = 'p-4 border-t border-gray-700 mt-4 text-white';
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.appendChild(container);
      }
      container.innerHTML = '<h4 class="text-sm text-gray-400 uppercase mb-2">Data Providers</h4>';
      for (const [key, info] of Object.entries(providers)) {
        const el = document.createElement('div');
        const onlineClass = info.available ? 'status-online' : 'status-error';
        el.className = 'flex items-center justify-between mb-2';
        el.innerHTML = `<div class="flex items-center"><span class="status-indicator ${onlineClass}"></span><span class="ml-2">${info.name || key}</span></div><div class="text-xs text-gray-300">${key}</div>`;
        container.appendChild(el);
      }
    } catch (e) {
      console.error('Failed to fetch provider statuses', e);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    fetchStatuses();
    // refresh every 60 seconds
    setInterval(fetchStatuses, 60000);

    // update statuses when provider changes
    window.addEventListener('provider:changed', function (e) {
      const provider = e.detail && e.detail.provider;
      if (provider) {
        // highlight selected provider
        const container = document.getElementById('provider-status-container');
        if (!container) return;
        for (const node of container.querySelectorAll('div.flex.items-center')) {
          node.style.fontWeight = 'normal';
        }
      }
    });
  });
})();
