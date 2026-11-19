document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.querySelector('#register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', (event) => {
            const error = document.querySelector('#register-client-error');
            const email = registerForm.querySelector('[name="email"]');
            const phone = registerForm.querySelector('[name="phone"]');
            const password = registerForm.querySelector('[name="password"]');
            error.textContent = '';
            if (!registerForm.checkValidity()) {
                event.preventDefault();
                error.textContent = 'Проверьте обязательные поля, почту, телефон и длину пароля.';
            } else if (phone.value && !/^[+0-9()\- ]{6,20}$/.test(phone.value)) {
                event.preventDefault();
                error.textContent = 'Введите корректный номер телефона.';
            } else if (password.value.length < 8) {
                event.preventDefault();
                error.textContent = 'Пароль должен содержать минимум 8 символов.';
            }
        });
    }

    const form = document.querySelector('#booking-form');
    if (!form) return;
    form.addEventListener('submit', (event) => {
        const error = document.querySelector('#client-error');
        const sector = form.querySelector('#sector');
        const tariff = form.querySelector('#tariff');
        const date = form.querySelector('#start_datetime');
        error.textContent = '';
        if (!sector.value || !tariff.value || !date.value) {
            event.preventDefault();
            error.textContent = 'Заполните все обязательные поля.';
            return;
        }
        if (new Date(date.value) <= new Date()) {
            event.preventDefault();
            error.textContent = 'Выберите дату и время в будущем.';
        }
    });
});
