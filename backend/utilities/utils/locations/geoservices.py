# Class to determine administrative category of the country

def get_country_administrative_category(country_code):
    from locations.exceptions import InvalidLocationData
    from locations.models.custom_country import CustomCountry

    # TODO Country model changes to incorporate administrative type. Meanwhile use below dict.
    # Eliminate this implementation once it is done.
    if not CustomCountry.objects.filter(country_code=country_code).exists():
        raise InvalidLocationData(f"Country code '{country_code}' does not exist in CustomCountry.")

    country_data = {
        'AD': 'unitary_state', 'AG': 'unitary_state', 'TK': 'unitary_state', 'LT': 'unitary_state',
        'LU': 'unitary_state', 'CZ': 'unitary_state', 'CM': 'unitary_state', 'TF': 'unitary_state',
        'NP': 'federal_state', 'KW': 'unitary_state', 'GB': 'quasi_federal_state', 'AO': 'unitary_state',
        'AQ': 'n/a', 'AR': 'federal_state', 'AS': 'unitary_state', 'AN': 'n/a', 'TD': 'unitary_state',
        'SJ': 'unitary_state', 'US': 'federal_state', 'TC': 'unitary_state', 'CN': 'unitary_state',
        'DE': 'federal_state', 'GD': 'unitary_state', 'GE': 'unitary_state', 'GF': 'unitary_state',
        'AT': 'federal_state', 'HT': 'unitary_state', 'IE': 'unitary_state', 'TJ': 'unitary_state',
        'TL': 'unitary_state', 'TM': 'unitary_state', 'GW': 'unitary_state', 'GY': 'unitary_state',
        'IL': 'unitary_state', 'IM': 'unitary_state', 'LV': 'unitary_state', 'LY': 'unitary_state',
        'MA': 'unitary_state', 'KR': 'unitary_state', 'TH': 'unitary_state', 'SC': 'unitary_state',
        'SD': 'unitary_state', 'MY': 'federal_state', 'SH': 'unitary_state', 'IT': 'quasi_federal_state',
        'TG': 'unitary_state', 'CO': 'unitary_state', 'VC': 'unitary_state', 'PM': 'unitary_state',
        'PN': 'unitary_state', 'PR': 'unitary_state', 'XK': 'unitary_state', 'TT': 'unitary_state',
        'TV': 'unitary_state', 'TW': 'unitary_state', 'UG': 'unitary_state', 'WS': 'unitary_state',
        'YE': 'unitary_state', 'YT': 'unitary_state', 'RO': 'unitary_state', 'RS': 'unitary_state',
        'MC': 'unitary_state', 'SN': 'unitary_state', 'SO': 'unitary_state', 'SR': 'unitary_state',
        'ME': 'unitary_state', 'SK': 'unitary_state', 'SL': 'unitary_state', 'SM': 'unitary_state',
        'ST': 'unitary_state', 'SV': 'unitary_state', 'PH': 'unitary_state', 'PY': 'unitary_state',
        'QA': 'unitary_state', 'GN': 'unitary_state', 'MF': 'unitary_state', 'MG': 'unitary_state',
        'MH': 'unitary_state', 'GL': 'quasi_federal_state', 'BW': 'unitary_state', 'GH': 'unitary_state',
        'LA': 'unitary_state', 'MK': 'unitary_state', 'ML': 'unitary_state', 'MM': 'unitary_state',
        'MN': 'unitary_state', 'MS': 'unitary_state', 'SA': 'unitary_state', 'SB': 'unitary_state',
        'CF': 'unitary_state', 'CI': 'unitary_state', 'TR': 'unitary_state', 'OM': 'unitary_state',
        'AW': 'quasi_federal_state', 'BA': 'federal_state', 'GG': 'unitary_state', 'NL': 'quasi_federal_state',
        'GI': 'unitary_state', 'PA': 'unitary_state', 'VA': 'unitary_state', 'GS': 'unitary_state',
        'GT': 'unitary_state', 'GU': 'unitary_state', 'HK': 'quasi_federal_state', 'HR': 'unitary_state',
        'VE': 'unitary_state', 'VG': 'unitary_state', 'BO': 'unitary_state', 'BQ': 'unitary_state',
        'BR': 'federal_state', 'BS': 'unitary_state', 'BT': 'unitary_state', 'BV': 'unitary_state',
        'FJ': 'unitary_state', 'FR': 'unitary_state', 'TN': 'unitary_state', 'GA': 'unitary_state',
        'TO': 'unitary_state', 'AF': 'unitary_state', 'JP': 'unitary_state', 'AU': 'federal_state',
        'PL': 'unitary_state', 'ZA': 'unitary_state', 'ZM': 'unitary_state', 'ZW': 'unitary_state',
        'EE': 'unitary_state', 'BB': 'unitary_state', 'KH': 'unitary_state', 'KI': 'unitary_state',
        'KM': 'unitary_state', 'KN': 'unitary_state', 'KP': 'unitary_state', 'AZ': 'unitary_state',
        'KY': 'unitary_state', 'KZ': 'unitary_state', 'LB': 'unitary_state', 'LC': 'unitary_state',
        'LI': 'unitary_state', 'LK': 'quasi_federal_state', 'LR': 'unitary_state', 'LS': 'unitary_state',
        'MT': 'unitary_state', 'MU': 'unitary_state', 'MV': 'unitary_state', 'SG': 'unitary_state',
        'SI': 'unitary_state', 'BY': 'unitary_state', 'IS': 'unitary_state', 'GM': 'unitary_state',
        'GP': 'unitary_state', 'GQ': 'unitary_state', 'GR': 'unitary_state', 'DJ': 'unitary_state',
        'IQ': 'quasi_federal_state', 'NZ': 'unitary_state', 'BD': 'unitary_state', 'BE': 'quasi_federal_state',
        'BG': 'unitary_state', 'CX': 'unitary_state', 'CY': 'unitary_state', 'DK': 'quasi_federal_state',
        'DM': 'unitary_state', 'DO': 'unitary_state', 'DZ': 'unitary_state', 'EC': 'unitary_state',
        'EG': 'unitary_state', 'EH': 'disputed territory', 'ER': 'unitary_state', 'SX': 'quasi_federal_state',
        'SY': 'unitary_state', 'SZ': 'unitary_state', 'MD': 'unitary_state', 'HU': 'unitary_state',
        'ID': 'unitary_state', 'CA': 'federal_state', 'IO': 'unitary_state', 'CC': 'unitary_state',
        'CD': 'unitary_state', 'CG': 'unitary_state', 'CH': 'federal_state', 'CK': 'quasi_federal_state',
        'CL': 'unitary_state', 'CR': 'unitary_state', 'CU': 'unitary_state', 'CV': 'unitary_state',
        'CW': 'quasi_federal_state', 'VN': 'unitary_state', 'VU': 'unitary_state', 'WF': 'unitary_state',
        'BF': 'unitary_state', 'HM': 'unitary_state', 'HN': 'unitary_state', 'UA': 'unitary_state',
        'CS': 'n/a', 'FK': 'unitary_state', 'MO': 'quasi_federal_state', 'MP': 'unitary_state',
        'MQ': 'unitary_state', 'BZ': 'unitary_state', 'AX': 'quasi_federal_state', 'MR': 'unitary_state',
        'MW': 'unitary_state', 'MX': 'federal_state', 'MZ': 'unitary_state', 'NA': 'unitary_state',
        'SS': 'unitary_state', 'SE': 'unitary_state', 'JO': 'unitary_state', 'PE': 'unitary_state',
        'PF': 'unitary_state', 'PG': 'unitary_state', 'PK': 'federal_state', 'NC': 'quasi_federal_state',
        'NE': 'unitary_state', 'NF': 'unitary_state', 'NG': 'federal_state', 'NI': 'unitary_state',
        'TZ': 'unitary_state', 'NO': 'unitary_state', 'NR': 'unitary_state', 'NU': 'quasi_federal_state',
        'IR': 'unitary_state', 'KG': 'unitary_state', 'RW': 'unitary_state', 'PS': 'unitary_state',
        'JM': 'unitary_state', 'PT': 'unitary_state', 'PW': 'unitary_state', 'FM': 'federal_state',
        'FO': 'quasi_federal_state', 'ES': 'quasi_federal_state', 'ET': 'federal_state', 'JE': 'unitary_state'
    }

    # Return category from dictionary or 'federal_state' if not found
    return country_data.get(country_code, 'federal_state')  # Since no data is available, assigning 'federal_state' else 'unknown'
