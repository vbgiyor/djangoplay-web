$(function() {
    // Initialize Select2 for all dropdowns
    $('.select2').select2({
        width: '100%',
        placeholder: 'Select an option',
        allowClear: true
    });

    // Action dropdown
    $('select[name="action"]').addClass('select2').select2({
        width: '100%',
        placeholder: '— Select action —',
        allowClear: true
    });

    // Hide default Django elements
    $('input[type="submit"][value="Go"]').hide();
    $('.actions').hide();

    // --- Dependent Filters: Country → Region ---
    const $country = $('select[name="country"]');
    const $dependentRegions = $('select[data-dependent="country"]');

    if ($country.length && $dependentRegions.length) {
        $dependentRegions.each(function() {
            const $region = $(this);

            function filterRegions() {
                const selectedCountry = $country.val();
                $region.find('option').each(function() {
                    const countryId = $(this).data('country-id');
                    $(this).toggle(!countryId || countryId == selectedCountry);
                });

                // Reset Region if selection hidden
                if ($region.find('option:selected').is(':hidden')) {
                    $region.val('').trigger('change');
                }
            }

            filterRegions(); // Initial run
            $country.on('change', filterRegions);
        });
    }

    // Pagination handling
    $('.pagination-link').on('click', function(e) {
        e.preventDefault();
        const page = $(this).data('page');
        const url = new URL(window.location.href);
        url.searchParams.set('p', page);
        window.location.href = url.toString();
    });
});
