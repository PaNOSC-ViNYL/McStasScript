from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


def euler_to_rotation_matrix(angles, elevation=None, rotation=None) -> np.ndarray:
    """Convert McStas ``ROTATED`` angles to an active rotation matrix.

    McStas expresses component rotations as ``(x, y, z)`` in degrees. The
    generated C code constructs a coordinate-system rotation; its transpose
    is the active local-to-parent transform needed by the renderers.

    Parameters
    ----------
    angles : sequence or float
        Three angles in degrees, or the x angle when the other two arguments
        are supplied.

    Returns
    -------
    np.ndarray
        3x3 rotation matrix.
    """
    if elevation is None and rotation is None:
        angles = np.asarray(angles, dtype=float)
        if angles.shape != (3,):
            raise ValueError("Expected three Euler angles")
        x, y, z = angles
    else:
        if elevation is None or rotation is None:
            raise ValueError("Expected all three Euler angles")
        x, y, z = angles, elevation, rotation

    x, y, z = np.deg2rad([x, y, z])
    cx, sx = np.cos(x), np.sin(x)
    cy, sy = np.cos(y), np.sin(y)
    cz, sz = np.cos(z), np.sin(z)

    return np.array([
        [cy * cz, sx * sy * cz - cx * sz, sx * sz + cx * sy * cz],
        [cy * sz, sx * sy * sz + cx * cz, -sx * cz + cx * sy * sz],
        [-sy, cy * sx, cy * cx],
    ])


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


def quaternion_to_rotation_matrix(q):
    """Convert a quaternion (x, y, z, w) to a 3x3 rotation matrix."""
    x, y, z, w = np.asarray(q, dtype=float)
    return np.array([
        [1 - 2*(y*y + z*z),   2*(x*y - z*w),     2*(x*z + y*w)],
        [   2*(x*y + z*w), 1 - 2*(x*x + z*z),   2*(y*z - x*w)],
        [   2*(x*z - y*w),   2*(y*z + x*w), 1 - 2*(x*x + y*y)],
    ])


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
        quaternion = self.final_quaternion()
        if quaternion is not None:
            pts = pts @ quaternion_to_rotation_matrix(quaternion).T
        if self.position is not None:
            pts = pts + np.asarray(self.position, dtype=np.float64)
        return pts


class TransformResolutionError(ValueError):
    """Raised when component transforms cannot be resolved."""


def resolve_transforms(
    components: list[Any],
    variables: dict[str, float] | None = None,
) -> dict[str, Transform]:
    """Resolve global transforms for all components in an instrument.

    Recursively follows AT RELATIVE and ROTATED RELATIVE references,
    composing parent-frame offsets and relative rotations.

    Parameters
    ----------
    components : list
        Ordered list of component objects (must have .name, .AT_data,
        .AT_reference, .ROTATED_data, .ROTATED_reference, .ROTATED_specified).
    variables : dict, optional
        Variable name -> value mapping for expression evaluation.

    Returns
    -------
    dict[str, Transform]
        Mapping of component name -> global Transform.

    Raises
    ------
    TransformResolutionError
        On missing references, circular references, or unresolvable expressions.
    """
    from mcstasscript.geometry_viewer.expression import resolve_at_rotated_values

    name_to_comp = {c.name: c for c in components}
    resolved: dict[str, Transform] = {}
    resolving: set[str] = set()

    def _resolve(name: str) -> Transform:
        if name in resolved:
            return resolved[name]
        if name in resolving:
            raise TransformResolutionError(
                f"Circular reference detected involving component '{name}'"
            )
        if name not in name_to_comp:
            raise TransformResolutionError(
                f"Unknown component reference: '{name}'"
            )

        resolving.add(name)
        comp = name_to_comp[name]

        # Resolve local AT
        try:
            at_data = getattr(comp, "AT_data", [0, 0, 0])
            if not isinstance(at_data, (list, tuple, np.ndarray)):
                at_data = [0, 0, 0]
            local_pos = resolve_at_rotated_values(at_data, variables)
        except Exception as exc:
            raise TransformResolutionError(
                f"Cannot resolve AT for component '{name}': {exc}"
            ) from exc

        # Resolve local ROTATED
        local_rot = np.eye(3)
        if getattr(comp, "ROTATED_specified", False) is True:
            try:
                rotated_data = getattr(comp, "ROTATED_data", [0, 0, 0])
                if not isinstance(rotated_data, (list, tuple, np.ndarray)):
                    rotated_data = [0, 0, 0]
                rot_vals = resolve_at_rotated_values(rotated_data, variables)
                local_rot = euler_to_rotation_matrix(rot_vals)
            except Exception as exc:
                raise TransformResolutionError(
                    f"Cannot resolve ROTATED for component '{name}': {exc}"
                ) from exc

        # Determine parent frame
        at_ref = getattr(comp, "AT_reference", None)
        rot_ref = getattr(comp, "ROTATED_reference", None)

        def resolve_reference(reference):
            if not isinstance(reference, str) or reference == "ABSOLUTE":
                return None
            if reference == "PREVIOUS":
                index = next(i for i, item in enumerate(components) if item.name == name)
                return components[index - 1].name if index else None
            return reference

        at_ref = resolve_reference(at_ref)
        rot_ref = resolve_reference(rot_ref)

        # Use ROTATED_reference for rotation if specified, else AT_reference
        rot_parent_name = rot_ref if comp.ROTATED_specified else at_ref

        if at_ref is None:
            global_pos = np.array(local_pos, dtype=np.float64)
        else:
            parent_transform = _resolve(at_ref)
            parent_rot = parent_transform.rotation_matrix if parent_transform.rotation_matrix is not None else np.eye(3)
            global_pos = parent_transform.position + parent_rot @ np.asarray(local_pos)

        if rot_parent_name is None:
            global_rot = local_rot
        else:
            parent_transform = _resolve(rot_parent_name)
            parent_rot = parent_transform.rotation_matrix if parent_transform.rotation_matrix is not None else np.eye(3)
            global_rot = parent_rot @ local_rot

        result = Transform(position=global_pos, rotation_matrix=global_rot)
        resolving.discard(name)
        resolved[name] = result
        return result

    for comp in components:
        _resolve(comp.name)

    return resolved
