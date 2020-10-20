use super::super::descs;


pub fn area_alignment_simple(rect1: &descs::RectDesc, rect2: &descs::RectDesc, context: &descs::Context) -> f32 {

    let sides_same: bool = (rect1.width - rect2.width).abs() <= 2.1 || (rect1.height - rect2.height).abs() <= 2.1;
    let is_aligned: bool = (rect1.y - rect2.y).abs() <= 2.1 || (rect1.x - rect2.x).abs() <= 2.1;

    let mut ans: f32 = 0.75;
    if sides_same && is_aligned {
        ans = 0.0;
    } else if sides_same || is_aligned {
        ans = 0.25;
    }

    let min_area = rect1.area.min(rect2.area);
    let max_area = rect1.area.max(rect2.area);

    let mut areas_different: bool = false;
    if max_area > 0.1 {
        areas_different = (min_area / max_area) < 0.6;
    }
    if areas_different == false {
        areas_different = (min_area-max_area).abs() > 1300.0;
    }

    if areas_different {
        ans *= 1.3;  // max will be 0.975
    }

    return ans.min(1.0);
}

/*


cdef double area_alignment_simple(RectStruct rect1, RectStruct rect2, Context context):

    cdef bint sides_same = abs_int(rect1.width - rect2.width) <= 2 or abs_int(rect1.height - rect2.height) <= 2
    cdef bint is_aligned = abs_int(rect1.y - rect2.y) <= 2 or abs_int(rect1.x - rect2.x) <= 2
    cdef double ans = 0

    if sides_same and is_aligned:
        ans = 0
    elif sides_same or is_aligned:
        ans = 0.25
    else:
        ans = 0.75

    cdef double min_area = min_double(rect1.area, rect2.area)
    cdef double max_area = max_double(rect1.area, rect2.area)

    cdef bint areas_different = False
    if max_area > 0:
        areas_different = (min_area / max_area) < 0.6
    areas_different = areas_different or abs_int(min_area-max_area) > 1300

    if areas_different:
        ans *= 1.3  # max will be 0.975

    return ans

*/