import random

import numpy as np

from util_core.util.comparison import jaccard_similarity


EXPECTED_COMPUTED_STYLE_KEYS = [
    '-moz-box-align', '-moz-box-flex', '-moz-box-ordinal-group', '-webkit-text-fill-color',
    '-webkit-text-stroke-color', 'align-content', 'align-items', 'animation-delay',
    'animation-duration', 'animation-fill-mode', 'animation-name', 'backface-visibility',
    'background-color', 'background-image', 'background-position', 'background-position-x',
    'background-position-y', 'background-repeat', 'background-size', 'border-bottom-color',
    'border-bottom-left-radius', 'border-bottom-right-radius', 'border-bottom-style',
    'border-bottom-width', 'border-collapse', 'border-left-color', 'border-left-style',
    'border-left-width', 'border-right-color', 'border-right-style', 'border-right-width',
    'border-spacing', 'border-top-color', 'border-top-left-radius', 'border-top-right-radius',
    'border-top-style', 'border-top-width', 'bottom', 'box-shadow', 'box-sizing', 'caret-color',
    'clear', 'clip', 'color', 'column-rule-color', 'cursor', 'display', 'filter', 'flex-basis',
    'flex-grow', 'flex-shrink', 'float', 'font-family', 'font-feature-settings', 'font-size',
    'font-size-adjust', 'font-style', 'font-variant', 'font-variant-ligatures', 'font-weight',
    'height', 'hyphens', 'justify-content', 'left', 'letter-spacing', 'line-height',
    'list-style-image', 'list-style-position', 'list-style-type',
    'margin-bottom', 'margin-left', 'margin-right', 'margin-top', 'max-width', 'min-height', 'min-width',
    'opacity', 'order', 'outline-color', 'outline-offset',
    'overflow', 'overflow-wrap', 'overflow-x', 'overflow-y',
    'padding-bottom', 'padding-left', 'padding-right', 'padding-top',
    'pointer-events', 'position', 'quotes', 'right', 'stroke', 'stroke-miterlimit',
    'text-align', 'text-decoration', 'text-decoration-color', 'text-decoration-line', 'text-emphasis-color',
    'text-indent', 'text-overflow', 'text-rendering', 'text-shadow', 'text-transform',
    'top', 'touch-action', 'transform', 'transition-delay', 'transition-duration', 'transition-property',
    'transition-timing-function', 'vertical-align', 'visibility', 'white-space', 'width',
    'word-break', 'word-spacing', 'z-index',

    'border-block-start-color', 'border-block-end-color', 'border-start-start-radius',
    'border-block-start-width', 'padding-inline-end', 'border-end-start-radius', 'border-inline-end-width',
    'padding-block-end', 'border-block-end-width', 'border-inline-start-width', 'border-inline-end-color',
    'border-end-end-radius', 'border-inline-start-color', 'padding-inline-start', 'padding-block-start',
    'border-start-end-radius'
]
NUM_KEYS = len(EXPECTED_COMPUTED_STYLE_KEYS)


def compare_computed_stylesEXPERIMENTAL(ld1, ld2, context):
    from scipy.interpolate import interp1d
    comp1 = ld1['all_computed_styles']
    comp2 = ld2['all_computed_styles']

    positive_points = []
    negative_points = []

    for k in EXPECTED_COMPUTED_STYLE_KEYS:
        if comp1.get(k) == comp2.get(k):
            if not comp1.get(k):
                continue
            weight = context['computed_style_weights'][(k, comp1.get(k) or comp2.get(k))]
            positive_points.append(min(0.44, weight/2))  # 0 -> 0, 1->0.5
        else:

            if comp1.get(k) is not None and comp2.get(k) is not None:
                weight1 = context['computed_style_weights'][(k, comp1.get(k))]
                weight2 = context['computed_style_weights'][(k, comp2.get(k))]

                if weight1 < 0.12 and weight2 < 0.12:
                    val = 0.75
                elif weight1 < 0.12 and weight2 > 0.75:
                    val = 1
                else:
                    val = 0.6
            else:
                if comp1.get(k) is not None:
                    weight = context['computed_style_weights'][(k, comp1.get(k))]
                else:
                    weight = context['computed_style_weights'][(k, comp2.get(k))]

                if weight < 0.1:
                    val = 0.6
                elif weight < 0.3:
                    val = 0.7
                else:
                    val = 0.8  # higher because None is relatively more unusual when the other is more usual
            negative_points.append(val)

    return np.mean(positive_points + negative_points)

    # weight positive matches by half
    val = sum(negative_points) + (sum(positive_points) * 0.5)
    val = max(-16, min(13, val))

    return float(interp1d((-16, 13), (1, 0))(val))


def compare_computed_styles_jaccard(ld1, ld2, context):

    comp1 = ld1['all_computed_styles']
    comp2 = ld2['all_computed_styles']

    comp1 = ['%s__%s' % (k, v) for (k, v) in comp1.items()]
    comp2 = ['%s__%s' % (k, v) for (k, v) in comp2.items()]

    return 1 - jaccard_similarity(comp1, comp2)

# TODO: the javascript was filtering out some keys, we should add them to the list and update the ML model (not sure what to do with the ground-truth files though)


def compare_computed_stylesOLD(ld1, ld2, context):
    from scipy.interpolate import interp1d

    comp1 = ld1['all_computed_styles']
    comp2 = ld2['all_computed_styles']

    positive_points, negative_points = [], []

    for k in EXPECTED_COMPUTED_STYLE_KEYS:
        if comp1.get(k) == comp2.get(k):
            if not comp1.get(k):
                continue
            positive_points.append(1)
        else:
            negative_points.append(-1)

    # weight positive matches by half
    val = sum(negative_points) + (sum(positive_points) * 0.5)
    val = max(-16, min(13, val))

    return float(interp1d((-16, 13), (1, 0))(val))


# cc_interp = interp1d((-16, 13), (1, 0))


def compare_computed_styles(ld1, ld2, context):

    comp1_array = ld1['all_computed_styles__array']
    comp2_array = ld2['all_computed_styles__array']
    # todo: benchmark this with https://www.weld.rs/weldnumpy/  (though I notice sum() isn't in list of operations?)
    num_equal = np.sum(np.array(np.char.equal(comp1_array, comp2_array), dtype=np.int))
    num_unequal = NUM_KEYS - num_equal
    for i, val in enumerate(comp1_array):
        if not val:
            if not comp2_array[i]:
                num_equal -= 1  # discount match because they were both blank

    # weight positive matches by half
    # val = sum(negative_points) + (sum(positive_points) * 0.5)
    val = (-1 * num_unequal) + (num_equal * 0.5)
    val = max(-16, min(13, val))
    if val == -16:
        return 1
    return 1 - ((val + 16) / 29)
    #return float(cc_interp(val))
