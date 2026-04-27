import json
from dataclasses import dataclass
from abc import ABC, abstractmethod

import numpy as np
import pythreejs as p3

def pos_rot_from_list(input_list):
    assert len(input_list) == 16
    T = np.array(input_list).reshape((4, 4))

    # Rotation matrix (top-left 3x3)
    R = T[:3, :3]

    # Position / translation vector (top-right 3 values)
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
    Returns quaternion as (x, y, z, w), suitable for pythreejs.
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
    """
    Convert a 3x3 rotation matrix to quaternion (x, y, z, w).
    Avoids needing scipy.
    """
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

@dataclass
class Transform:
    position: np.ndarray | None = None
    rotation_matrix: np.ndarray | None = None
    quaternion: tuple[float, float, float, float] | None = None

    def apply_to(self, obj):
        if self.position is not None:
            obj.position = tuple(np.asarray(self.position, dtype=float))

        if self.quaternion is not None:
            obj.quaternion = self.quaternion

        elif self.rotation_matrix is not None:
            obj.quaternion = quaternion_from_rotation_matrix(self.rotation_matrix)

        return obj