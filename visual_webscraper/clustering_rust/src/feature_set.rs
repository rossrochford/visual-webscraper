use super::descs;


// todo: consider using a BTreeSet: https://doc.rust-lang.org/std/collections/btree_set/struct.BTreeSet.html

pub fn featureset_overlap(ed1: &descs::FeatureSetDesc, ed2: &descs::FeatureSetDesc, context: &descs::Context) -> f32 {

    let set1 = &ed1.feature_set_int;
    let set2 = &ed2.feature_set_int;

    let intersection_cardinality = set1.intersection(set2).count();

    let union_cardinality = set1.union(set2).count();

    if union_cardinality == 0 {
        return 0.0;
    }

    let jaccard_sim = (intersection_cardinality as f32) / (union_cardinality as f32);

    return 1.0 - jaccard_sim;
}
