
from webextractor.clustering.comparisons.area_similarity import areas_similar
from webextractor.clustering.comparisons.computed_styles import compare_computed_styles
from webextractor.clustering.comparisons.content import compare_content
from webextractor.clustering.comparisons.euclidean_distance import adjusted_euclidean_distance
from webextractor.clustering.comparisons.featureset_overlap import featureset_overlap
from webextractor.clustering.comparisons.is_visible import compare_visibility
from webextractor.clustering.comparisons.spatial_alignment import spatially_aligned
from webextractor.clustering.comparisons.url_similarity import url_similarity
from webextractor.clustering.comparisons.visual_similarity import visually_similar


COMPARISON_FUNCTIONS = [
    areas_similar,
    compare_computed_styles,
    compare_content,
    adjusted_euclidean_distance,
    featureset_overlap,
    compare_visibility,
    spatially_aligned,
    url_similarity,
    visually_similar
]