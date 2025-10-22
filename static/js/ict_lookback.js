document.addEventListener('DOMContentLoaded', function () {
  const fetchBtn = document.getElementById('fetchBtn');
  const results = document.getElementById('results');

  function renderDayCard(day) {
    const card = document.createElement('div');
    card.className = 'card p-4';
    const html = [];
    html.push(`<h4 class="font-semibold">${day.date} — ${day.symbol}</h4>`);
    html.push(`<div class="text-sm text-gray-700">Open: ${day.daily_open} High: ${day.daily_high} Low: ${day.daily_low} Close: ${day.daily_close}</div>`);
    html.push(`<div class="text-sm text-gray-600">Range points: ${day.range_points} Pips: ${day.range_pips || 'N/A'}</div>`);
    if (day.sessions) {
      html.push('<div class="mt-2">');
      for (const [k, v] of Object.entries(day.sessions)) {
        if (v) {
          html.push(`<div class="text-xs">${k}: O:${v.open} H:${v.high} L:${v.low} C:${v.close}</div>`);
        } else {
          html.push(`<div class="text-xs text-gray-500">${k}: no data</div>`);
        }
      }
      html.push('</div>');
    }

    if (day.selected_time) {
      const s = day.selected_time;
      html.push(`<div class="mt-2 text-sm text-indigo-700">Selected: O:${s.open} H:${s.high} L:${s.low} C:${s.close}</div>`);
    }

    card.innerHTML = html.join('');
    return card;
  }

  fetchBtn.addEventListener('click', async function () {
    const symbols = document.getElementById('symbolsInput').value;
    const days = document.getElementById('daysInput').value;
    const time = document.getElementById('timeInput').value;
    const window = document.getElementById('windowInput').value;

    results.innerHTML = '<div class="p-4 card">Loading...</div>';

    try {
      const provider = window.APP_PROVIDER || localStorage.getItem('finbot_data_provider') || 'yfinance';
      const qs = new URLSearchParams({ symbols, days, time, window, provider });
      const r = await fetch(`/api/ict/lookback?${qs.toString()}`);
      const payload = await r.json();

      if (payload.status !== 'success') {
        results.innerHTML = `<div class="p-4 card text-red-600">Error: ${payload.error || 'Unknown'}</div>`;
        return;
      }

      results.innerHTML = '';
      for (const [sym, daysList] of Object.entries(payload.data)) {
        const section = document.createElement('div');
        section.className = 'mb-6';
        const title = document.createElement('h3');
        title.className = 'text-lg font-semibold mb-2';
        title.textContent = sym;
        section.appendChild(title);

        const grid = document.createElement('div');
        grid.className = 'grid grid-cols-1 md:grid-cols-2 gap-4';

        daysList.forEach(d => {
          const card = renderDayCard(d);
          grid.appendChild(card);
        });

        section.appendChild(grid);
        results.appendChild(section);
      }

    } catch (err) {
      console.error(err);
      results.innerHTML = `<div class="p-4 card text-red-600">Fetch failed: ${err.message}</div>`;
    }
  });
});
