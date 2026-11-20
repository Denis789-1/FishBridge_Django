document.addEventListener('DOMContentLoaded', () => {
    const search = document.querySelector('#pond-search');
    const cards = document.querySelector('#pond-cards');
    const loading = document.querySelector('#pond-loading');
    if (!cards) return;

    let savedFavorites = [];
    try {
        const storedFavorites = JSON.parse(localStorage.getItem('fishbridge-favorites') || '[]');
        if (Array.isArray(storedFavorites)) savedFavorites = storedFavorites.map(String);
    } catch (error) {
        console.warn('Не удалось прочитать избранное из localStorage:', error);
    }
    const saved = new Set(savedFavorites);
    const updateFavorites = () => {
        document.querySelectorAll('[data-favorite]').forEach((button) => {
            const active = saved.has(button.dataset.favorite);
            button.setAttribute('aria-pressed', String(active));
            button.textContent = active ? '♥ В избранном' : '♡ В избранное';
        });
    };
    updateFavorites();

    cards.addEventListener('click', (event) => {
        const button = event.target.closest('[data-favorite]');
        if (!button) return;
        const id = button.dataset.favorite;
        saved.has(id) ? saved.delete(id) : saved.add(id);
        localStorage.setItem('fishbridge-favorites', JSON.stringify([...saved]));
        updateFavorites();
    });

    if (!search) return;
    const searchForm = document.querySelector('#pond-search-form');
    if (searchForm) searchForm.addEventListener('submit', (event) => event.preventDefault());
    let requestNumber = 0;
    search.addEventListener('input', async () => {
        const currentRequest = ++requestNumber;
        loading.textContent = 'Загрузка...';
        try {
            const response = await fetch(`${search.dataset.apiUrl}?q=${encodeURIComponent(search.value)}`, {
                headers: {'X-Requested-With': 'XMLHttpRequest'}
            });
            if (!response.ok) throw new Error('Ошибка ответа сервера');
            const data = await response.json();
            if (!data || !Array.isArray(data.ponds)) throw new Error('Сервер вернул данные в неверном формате');
            if (currentRequest !== requestNumber) return;
            cards.replaceChildren();
            if (!data.ponds.length) {
                const empty = document.createElement('p');
                empty.className = 'empty-state';
                empty.textContent = 'Водоёмы не найдены.';
                cards.append(empty);
            }
            data.ponds.forEach((pond) => {
                const article = document.createElement('article');
                article.className = 'card';
                if (pond.image_url) {
                    const image = document.createElement('img');
                    image.className = 'pond-card-image';
                    image.src = pond.image_url;
                    image.alt = pond.name;
                    image.width = pond.image_width;
                    image.height = pond.image_height;
                    image.loading = 'lazy';
                    image.decoding = 'async';
                    article.append(image);
                }
                const content = document.createElement('div');
                content.className = 'card-content';
                const title = document.createElement('h3'); title.textContent = pond.name;
                const description = document.createElement('p'); description.textContent = pond.description;
                const address = document.createElement('p'); address.textContent = `Адрес: ${pond.address}`;
                const link = document.createElement('a'); link.className = 'btn'; link.href = pond.url; link.textContent = 'Подробнее';
                const favorite = document.createElement('button'); favorite.type = 'button'; favorite.className = 'favorite-button'; favorite.dataset.favorite = pond.id;
                content.append(title, description, address, link, favorite);
                article.append(content); cards.append(article);
            });
            updateFavorites();
            loading.textContent = `Найдено водоёмов: ${data.ponds.length}`;
        } catch (error) {
            console.error('Ошибка поиска водоёмов:', error);
            loading.textContent = 'Не удалось загрузить результаты. Попробуйте обновить страницу.';
        }
    });
});
