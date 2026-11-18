document.addEventListener('DOMContentLoaded', () => {
    const button = document.querySelector('.nav-toggle');
    const menu = document.querySelector('.site-nav');

    if (!button || !menu) return;

    button.addEventListener('click', () => {
        const isOpen = button.getAttribute('aria-expanded') === 'true';
        button.setAttribute('aria-expanded', String(!isOpen));
        button.setAttribute('aria-label', isOpen ? 'Открыть меню' : 'Закрыть меню');
        menu.classList.toggle('is-open', !isOpen);
    });

    menu.addEventListener('click', (event) => {
        if (event.target.closest('a')) {
            menu.classList.remove('is-open');
            button.setAttribute('aria-expanded', 'false');
            button.setAttribute('aria-label', 'Открыть меню');
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            menu.classList.remove('is-open');
            button.setAttribute('aria-expanded', 'false');
            button.setAttribute('aria-label', 'Открыть меню');
        }
    });
});
