use super::super::descs;


pub fn spatially_aligned(rect1: &descs::RectDesc, rect2: &descs::RectDesc, context: &descs::Context) -> f32 {

    let y_diff = (rect1.y - rect2.y).abs();
    let x_diff = (rect1.x - rect2.x).abs();

    if rect1.x < 0.01 && rect1.y < 0.01 && (rect2.x > 0.1 || rect2.y > 0.1) {
        return 0.5;
    }
    if rect2.x < 0.01 && rect2.y < 0.01 && (rect1.x > 0.1 || rect1.y > 0.1) {
        return 0.5;
    }

    if (rect1.x-rect2.x).abs() < 8.0 && (rect1.y-rect2.y).abs() < 8.0 {
        return 0.5;
    }

    if x_diff < 4.0 {
        if y_diff < 3.0 {
            // unusual circumstance, two links have almost the same location
            return 0.5;
        }
        if y_diff < 800.0 {
            return 0.0;
        } else {
            // disregard aligned pairs that are too far apart
            return 0.5;
        }
    }

    if y_diff < 4.0 {
        if x_diff < 3.0 {
            // unusual circumstance, two links have almost the same location
            return 0.5;
        }
        if x_diff < 900.0 {
            return 0.0;
        } else {
            //  disregard aligned pairs that are too far apart
            return 0.5;
        }
    }

    if x_diff > 6.0 || y_diff > 6.0 {
        return 1.0;
    }

    return 0.5;
}
