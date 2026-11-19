document.addEventListener('DOMContentLoaded', () => {
    const container = document.querySelector('#account-favorites');
    const emptyMessage = document.querySelector('#favorites-empty');
    const dataElement = document.querySelector('#favorite-pond-data');
    if (!container || !emptyMessage || !dataElement) return;

    let ponds = [];
    try {
        ponds = JSON.parse(dataElement.textContent);
    } catch (error) {
        emptyMessage.hidden = false;
        emptyMessage.textContent = 'Не удалось загрузить список водоёмов.';
        return;
    }

    const storageKey = 'fishbridge-favorites';
    let favorites = [];
    try {
        favorites = JSON.parse(localStorage.getItem(storageKey) || '[]');
        if (!Array.isArray(favorites)) favorites = [];
    } catch (error) {
        favorites = [];
    }

    const render = () => {
        container.replaceChildren();
        const selected = ponds.filter((pond) => favorites.includes(String(pond.id)));
        emptyMessage.hidden = selected.length > 0;

        selected.forEach((pond) => {
            const card = document.createElement('article');
            card.className = 'card';
            const content = document.createElement('div');
            content.className = 'card-content';
            const title = document.createElement('h3');
            title.textContent = pond.name;
            const description = document.createElement('p');
            description.textContent = pond.description;
            const address = document.createElement('p');
            address.textContent = pond.address ? `Адрес: ${pond.address}` : 'Адрес не указан';
            const details = document.createElement('a');
            details.className = 'btn';
            details.href = pond.detail_url;
            details.textContent = 'Подробнее';
            content.append(title, description, address, details);

            if (pond.has_sector) {
                const booking = document.createElement('a');
                booking.className = 'btn';
                booking.href = pond.booking_url;
                booking.textContent = 'Забронировать';
                content.append(booking);
            } else {
                const unavailable = document.createElement('p');
                unavailable.className = 'field-error';
                unavailable.textContent = 'Пока нет доступных секторов для бронирования.';
                content.append(unavailable);
            }

            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'favorite-button';
            remove.dataset.removeFavorite = String(pond.id);
            remove.textContent = 'Убрать из избранного';
            content.append(remove);
            card.append(content);
            container.append(card);
        });
    };

    container.addEventListener('click', (event) => {
        const button = event.target.closest('[data-remove-favorite]');
        if (!button) return;
        favorites = favorites.filter((id) => id !== button.dataset.removeFavorite);
        localStorage.setItem(storageKey, JSON.stringify(favorites));
        render();
    });

    render();
});
