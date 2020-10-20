use super::super::descs;


pub fn areas_similar(rect1: &descs::RectDesc, rect2: &descs::RectDesc, context: &descs::Context) -> f32 {

    if rect1.width == rect2.width && rect1.height == rect2.height {
        return 0.0;
    }

    if rect1.height == rect2.height {
        if (rect1.width - rect2.width).abs() <= 6.0 {
            return 0.0;
        }
    }

    if rect1.width == 0.0 || rect2.width == 0.0 {
        if rect1.width == rect2.width {
            return 0.0;
        }
        return 1.0;
    }

    if rect1.height == 0.0 || rect2.height == 0.0 {
        if rect1.height == rect2.height {
            return 0.0;
        }
        return 1.0;
    }

    if rect1.area <= 1.0 && rect2.area <= 1.0 {
        return 0.22;   // area == 0 but height or width is different
    }

    if (rect1.area <= 1.0 && rect2.area > 1.0) || (rect2.area < 1.0 && rect1.area > 1.0) {
        return 1.0;
    }

    if rect1.area < 50.0 && rect2.area < 50.0 {
        return 0.5;
    }

    let ratio = rect1.area.max(rect2.area) / rect1.area.min(rect2.area);
    if ratio > 3.0 {
        return 1.0;
    }

    let width_similar = (rect1.width - rect2.width).abs() < 4.0;
    let height_similar = (rect1.height - rect2.height).abs() < 4.0;

    if width_similar && ratio < 1.5 {
        return 0.0;
    }
    if height_similar && ratio < 1.5 {
        return 0.0;
    }

    if width_similar && ratio < 2.0 {
        return 0.28;
    }
    if height_similar && ratio < 2.0 {
        return 0.28;
    }

    if ratio < 1.25 {  // (and neither heights nor widths are similar
        return 0.5;
    }

    return 1.0;
}

/*
ctypedef struct RectStruct:
    int x
    int y
    int height
    int width
    int area


cdef double areas_similar(RectStruct rect1, RectStruct rect2, Context context):

    if rect1.width == rect2.width and rect1.height == rect2.height:
        return 0

    if rect1.height == rect2.height:
        if abs_int(rect1.width - rect2.width) <= 6:
            return 0

    if rect1.width == 0 or rect2.width == 0:
        if rect1.width == rect2.width:
            return 0
        return 1

    if rect1.height == 0 or rect2.height == 0:
        if rect1.height == rect2.height:
            return 0
        return 1

    cdef int area1 = rect1.area
    cdef int area2 = rect2.area

    if area1 == 0 and area2 == 0:
        return 0.22  # area 0 but height or width is different

    if (area1 == 0 and area2 > 0) or (area2 == 0 and area1 > 0):
        return 1
    if area1 < 50 and area2 < 50:
        print('area small')
        return 0.5

    cdef double ratio = max_double(area1, area2) / min_double(area1, area2)
    if ratio > 3:  # too large
        return 1

    cdef bint width_similar = abs_int(rect1.width - rect2.width) < 4
    cdef bint height_similar = abs_int(rect1.height - rect2.height) < 4

    if width_similar and ratio < 1.5:
        return 0
    if height_similar and ratio < 1.5:
        return 0

    if width_similar and ratio < 2:
        return 0.28
    if height_similar and ratio < 2:
        return 0.28

    if ratio < 1.25:  # (and neither heights nor widths are similar
        return 0.5

    return 1


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