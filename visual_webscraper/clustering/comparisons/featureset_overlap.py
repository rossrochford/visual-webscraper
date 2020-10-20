
from util_core.util.comparison import jaccard_similarity


def featureset_overlap(ld1, ld2, context):
    sim = jaccard_similarity(
        ld1['feature_set'], ld2['feature_set']
    )
    return 1 - sim
