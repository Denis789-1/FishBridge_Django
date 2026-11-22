document.addEventListener('DOMContentLoaded', () => {
    const pond = document.querySelector('#id_pond');
    const sector = document.querySelector('#sector');
    if (!pond || !sector) return;

    const updateSectors = () => {
        const selectedPond = pond.value;
        Array.from(sector.options).forEach((option) => {
            if (!option.value) {
                option.hidden = false;
                return;
            }
            option.hidden = Boolean(selectedPond) && option.dataset.pond !== selectedPond;
        });
        const selectedOption = sector.selectedOptions[0];
        if (selectedOption && selectedOption.hidden) sector.value = '';
    };

    pond.addEventListener('change', updateSectors);
    updateSectors();
});
