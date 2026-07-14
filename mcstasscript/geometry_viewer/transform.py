from dataclasses import dataclass

import numpy as np


def pos_rot_from_list(input_list):
    assert len(input_list) == 16
    T = np.array(input_list).reshape((4, 4))
    R = T[:3, :3]
    position = T[:3, 3]
    return position, R


def normalize(v):
    v = np.array(v, dtype=float)
    norm = np.linalg.norm(v)
    if norm == 0:
        raise ValueError("Cannot normalize zero-length vector")
    return v / norm


def quaternion_from_vectors(v0, v1):
    """
    Returns quaternion as (x, y, z, w).
    Rotates v0 onto v1.
    """
    v0 = normalize(v0)
    v1 = normalize(v1)

    c = np.cross(v0, v1)
    d = np.dot(v0, v1)

    if d < -0.999999:
        axis = np.cross([1, 0, 0], v0)
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross([0, 1, 0], v0)
        axis = normalize(axis)
        return (axis[0], axis[1], axis[2], 0.0)

    s = np.sqrt((1 + d) * 2)
    invs = 1 / s
    return (
        c[0] * invs,
        c[1] * invs,
        c[2] * invs,
        s * 0.5,
    )


def quaternion_from_rotation_matrix(R):
    """Convert a 3x3 rotation matrix to quaternion (x, y, z, w)."""
    R = np.asarray(R, dtype=float)
    trace = np.trace(R)

    if trace > 0:
        s = 2.0 * np.sqrt(trace + 1.0)
        qw = 0.25 * s
        qx = (R[2, 1] - R[1, 2]) / s
        qy = (R[0, 2] - R[2, 0]) / s
        qz = (R[1, 0] - R[0, 1]) / s

    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        qw = (R[2, 1] - R[1, 2]) / s
        qx = 0.25 * s
        qy = (R[0, 1] + R[1, 0]) / s
        qz = (R[0, 2] + R[2, 0]) / s

    elif R[1, 1] > R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        qw = (R[0, 2] - R[2, 0]) / s
        qx = (R[0, 1] + R[1, 0]) / s
        qy = 0.25 * s
        qz = (R[1, 2] + R[2, 1]) / s

    else:
        s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        qw = (R[1, 0] - R[0, 1]) / s
        qx = (R[0, 2] + R[2, 0]) / s
        qy = (R[1, 2] + R[2, 1]) / s
        qz = 0.25 * s

    return (qx, qy, qz, qw)


def normalize_quaternion(q):
    q = np.asarray(q, dtype=float)
    norm = np.linalg.norm(q)
    if norm == 0:
        raise ValueError("Cannot normalize zero-length quaternion")
    return tuple(q / norm)


def quaternion_multiply(q1, q2):
    """Hamilton product of two quaternions in (x, y, z, w) format. Returns q1 * q2."""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return normalize_quaternion((
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    ))


@dataclass
class Transform:
    position: np.ndarray | None = None
    rotation_matrix: np.ndarray | None = None
    quaternion: tuple[float, float, float, float] | None = None

    def final_quaternion(self):
        q = None
        if self.rotation_matrix is not None:
            q = normalize_quaternion(quaternion_from_rotation_matrix(self.rotation_matrix))
        if self.quaternion is not None:
            q_extra = normalize_quaternion(self.quaternion)
            if q is None:
                q = q_extra
            else:
                q = quaternion_multiply(q, q_extra)
        return q

    def transform_points(self, points: np.ndarray) -> np.ndarray:
        """Apply this transform to an (N, 3) array of points."""
        pts = np.asarray(points, dtype=np.float64)
        if self.rotation_matrix is not None:
            pts = pts @ self.rotation_matrix.T
        if self.position is not None:
            pts = pts + np.asarray(self.position, dtype=np.float64)
        return pts
