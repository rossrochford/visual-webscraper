from webextractor.clustering.comparisons.featureset_overlap import featureset_overlap
from webextractor.clustering.comparisons.content import compare_content
from webextractor.clustering.comparisons.is_visible import compare_visibility
from webextractor.clustering.comparisons.spatial_alignment import spatially_aligned
from webextractor.clustering.comparisons.url_similarity import url_similarity
#from webextractor.clustering.comparisons.visual_similarity import visually_similar
from webextractor.clustering.comparisons.area_similarity import areas_similar
from webextractor.clustering.comparisons.area_alignment import area_alignment_simple
from webextractor.clustering.comparisons.euclidean_distance import (
    adjusted_euclidean_distance, standard_euclidean_distance
)
from webextractor.clustering.comparisons.computed_styles import (
    compare_computed_styles, compare_computed_styles_jaccard
)

COMPARISON_FUNCTIONS = [
    adjusted_euclidean_distance,
    area_alignment_simple,
    areas_similar,
    compare_computed_styles,
    #compare_computed_styles_jaccard,
    compare_content,
    #compare_navigation_status,
    compare_visibility,
    featureset_overlap,
    spatially_aligned,
    #standard_euclidean_distance,
    url_similarity,
    #visually_similar
]


def get_matrix_results__python(elem_descriptions, context):

    elem_descriptions = elem_descriptions

    matrix_results = {}

    for func in COMPARISON_FUNCTIONS:
        sims = []
        for i, ed1 in enumerate(elem_descriptions):
            for j, ed2 in enumerate(elem_descriptions):
                if i >= j:
                    continue
                sims.append(
                    func(ed1, ed2, context)
                )
        matrix_results[func.__name__] = sims

    return matrix_results
