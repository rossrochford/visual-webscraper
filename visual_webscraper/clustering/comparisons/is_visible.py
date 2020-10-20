import numpy as np

'''

signals:

    css__visibility != 'visible'

    is_displayed__full is False

    spatial_visibility don't match and one is IN_PAGE
    spatial_visibility match and are not IN_PAGE

    jquery__is_hidden is True

'''

# explanation of isDisplayed() behavior:
# https://webdriver.io/docs/api/element/isDisplayed.html


def _compare_spatial_visibility(ld1, ld2):
    """
    Return 0 if both values are equal and not 'IN_PAGE';
    Return 1 if values aren't equal and one is 'IN_PAGE'
    """
    val1, val2 = ld1['spatial_visibility'], ld2['spatial_visibility']

    if val1 == val2:
        if val1 != 'IN_PAGE':
            return 0
        return None
    # val1 != val2
    if val1 == 'IN_PAGE' or val2 == 'IN_PAGE':
        return 1

    return None


def _compare_is_displayed(ld1, ld2):
    """
    Compare is_displayed. Ignore case where both are displayed.
    """
    val1, val2 = ld1['driver__is_displayed'], ld2['driver__is_displayed']

    if val1 == val2:
        if val1 is False:
            return 0
        return None

    return 1


def _compare_css_display(ld1, ld2):

    val1, val2 = ld1['cssComputed__display'], ld2['cssComputed__display']

    return int(val1 != val2)  # 0 when matching


def _compare_css_is_hidden(ld1, ld2):

    val1, val2 = ld1['jquery__is_hidden'], ld2['jquery__is_hidden']

    if val1 == val2:
        if val1 is True:
            return 0
        return None
    return 1


def _compare_css_computed_visibility(ld1, ld2):

    val1, val2 = ld1['cssComputed__visibility'], ld2['cssComputed__visibility']

    if val1 == val2:
        if val1 == 'visible':
            return None
        return 0

    return 1


FUNCTIONS = [
    _compare_spatial_visibility,
    _compare_is_displayed,
    _compare_css_display,
    _compare_css_is_hidden,
    _compare_css_computed_visibility
]


# not sure about this, it returns 0.5 when driver__is_displayed matches and _compare_css_display doesn't, should they cancel themselves out like that?


def compare_visibility(ld1, ld2, context):
    """ Collect signals and average them """

    if ld1['visibility__ALL_VISIBLE'] and ld2['visibility__ALL_VISIBLE']:
        return 0.5

    signals = [func(ld1, ld2) for func in FUNCTIONS]
    signals = [val for val in signals if val is not None]

    if len(signals) == 0:
        return 0.5

    return float(np.mean(signals))
