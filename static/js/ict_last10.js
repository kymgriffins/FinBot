(function () {
  async function fetchCards(symbol) {
    const url = `/api/ict/market-overview/cards?symbols=${encodeURIComponent(symbol)}&days=10`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch cards');
    return res.json();
  }

  function renderCard(card) {
    const container = document.createElement('div');
    container.className = 'card p-4';

    container.innerHTML = `
      <div class="flex justify-between items-start mb-2">
        <div>
          <div class="text-sm text-gray-600">${card.symbol}</div>
          <div class="text-lg font-bold">${card.date}</div>
        </div>
        <div class="text-right">
          <div class="text-sm text-gray-500">${card.market_condition || 'N/A'}</div>
          <div class="text-xs text-gray-400">Range: ${card.daily_range || 0}</div>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-2 mt-2">
        <div class="text-sm">Open<br><strong>${card.daily_open ?? '-'}</strong></div>
        <div class="text-sm">High<br><strong>${card.daily_high ?? '-'}</strong></div>
        <div class="text-sm">Low<br><strong>${card.daily_low ?? '-'}</strong></div>
        <div class="text-sm">Close<br><strong>${card.daily_close ?? '-'}</strong></div>
        <div class="text-sm">FVGs<br><strong>${card.fvg_count}</strong></div>
        <div class="text-sm">Liquidity<br><strong>${card.liquidity_count}</strong></div>
      </div>
      <div class="mt-3 text-sm text-gray-600">
        <div>Top Premium: ${card.top_premium ? card.top_premium.price : 'N/A'}</div>
        <div>Top Discount: ${card.top_discount ? card.top_discount.price : 'N/A'}</div>
      </div>
    `;

    return container;
  }

  async function load(symbol) {
    const cardsContainer = document.getElementById('cardsContainer');
    cardsContainer.innerHTML = '<div class="text-center p-8">Loading...</div>';
    try {
      const data = await fetchCards(symbol);
      if (data.status !== 'success') throw new Error('No data');
      const cards = data.data[symbol] || [];
      if (!cards.length) {
        cardsContainer.innerHTML = '<div class="text-center p-8">No card data available</div>';
        return;
      }
      cardsContainer.innerHTML = '';
      cards.reverse().forEach(card => {
        cardsContainer.appendChild(renderCard(card));
      });
    } catch (e) {
      cardsContainer.innerHTML = `<div class="text-center p-8 text-red-600">Error loading cards: ${e.message}</div>`;
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const sel = document.getElementById('symbolSelect');
    sel.addEventListener('change', () => load(sel.value));
    load(sel.value);
  });
})();
