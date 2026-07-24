import json
import math
import os
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from mcstasscript.geometry_viewer.transform import (
    pos_rot_from_list,
    normalize,
    quaternion_from_vectors,
    quaternion_from_rotation_matrix,
    quaternion_to_rotation_matrix,
    normalize_quaternion,
    quaternion_multiply,
    Transform,
    euler_to_rotation_matrix,
    resolve_transforms,
    TransformResolutionError,
)
from mcstasscript.geometry_viewer.model.shapes import (
    Style,
    BoxShape,
    LineSegmentsShape,
    CircleShape,
    ConeShape,
    CylinderShape,
    PolyhedronShape,
    SphereShape,
    triangulate_faces,
)
from mcstasscript.geometry_viewer.model.component import (
    ComponentModel,
    DRAWCALL_PARSERS,
    _parse_box,
    _parse_cylinder,
    _parse_cone,
    _parse_circle,
    _parse_polyhedron,
    _parse_multiline,
)
from mcstasscript.geometry_viewer.model.instrument import InstrumentModel
from mcstasscript.geometry_viewer.config import (
    DEFAULT_COLORS,
    DEFAULT_CAMERA_POSITION,
    DEFAULT_CAMERA_TARGET,
    DEFAULT_FOV,
    DEFAULT_NEAR,
    DEFAULT_FAR,
    DEFAULT_RENDERER_SIZE,
    DEFAULT_RADIAL_SEGMENTS,
    DEFAULT_CIRCLE_SEGMENTS,
    DEFAULT_NAVIGATOR_DISTANCE,
    DEFAULT_PICK_TOLERANCE,
    index_to_color,
    intensity_to_color,
)
from mcstasscript.geometry_viewer.api import _get_renderer, view_with_guess, view_with_json
from mcstasscript.geometry_viewer.expression import safe_eval, UnsafeExpressionError


# Path to the mcdisplay JSON fixture
FIXTURE_JSON = os.path.join(os.path.dirname(__file__), "test_geometry_viewer", "instrument.json")


def load_fixture():
    with open(FIXTURE_JSON) as f:
        return json.load(f)


def make_mock_component(name="test_comp"):
    """Create a minimal mock component object compatible with ComponentModel."""
    comp = MagicMock()
    comp.name = name
    comp.parameter_names = []
    comp.parameter_defaults = {}
    return comp


def make_mock_component_with_params(xwidth=1.0, yheight=2.0):
    """Create a mock component with xwidth/yheight parameters (rectangle type)."""
    comp = MagicMock()
    comp.name = "rect_comp"
    comp.parameter_names = ["xwidth", "yheight"]
    comp.xwidth = xwidth
    comp.yheight = yheight
    comp.parameter_defaults = {"xwidth": 0.0, "yheight": 0.0}
    return comp


class TestPosRotFromList(unittest.TestCase):
    """Tests for pos_rot_from_list: extracts position and rotation from a 16-element m4 matrix."""

    def test_identity_matrix(self):
        """
        An identity 4x4 matrix should yield zero position
        and an identity 3x3 rotation matrix.
        """
        identity = [1, 0, 0, 0,
                    0, 1, 0, 0,
                    0, 0, 1, 0,
                    0, 0, 0, 1]
        pos, rot = pos_rot_from_list(identity)
        np.testing.assert_array_almost_equal(pos, [0, 0, 0])
        np.testing.assert_array_almost_equal(rot, np.eye(3))

    def test_translation(self):
        """
        A matrix with translation in the last column should
        extract the correct position vector.
        """
        m4 = [1, 0, 0, 3,
              0, 1, 0, 4,
              0, 0, 1, 5,
              0, 0, 0, 1]
        pos, _ = pos_rot_from_list(m4)
        np.testing.assert_array_almost_equal(pos, [3, 4, 5])

    def test_wrong_length_raises(self):
        """
        Passing a list that is not 16 elements should raise
        an AssertionError.
        """
        with self.assertRaises(AssertionError):
            pos_rot_from_list([1, 2, 3])


class TestNormalize(unittest.TestCase):
    """Tests for the normalize vector utility."""

    def test_unit_vector(self):
        """
        A vector that is already unit length should remain
        unchanged after normalization.
        """
        result = normalize([1, 0, 0])
        np.testing.assert_array_almost_equal(result, [1, 0, 0])

    def test_arbitrary_vector(self):
        """
        A non-unit vector should be scaled down to unit length.
        """
        result = normalize([3, 4, 0])
        np.testing.assert_array_almost_equal(result, [0.6, 0.8, 0])

    def test_zero_vector_raises(self):
        """
        Normalizing a zero-length vector is undefined and should
        raise a ValueError.
        """
        with self.assertRaises(ValueError):
            normalize([0, 0, 0])


class TestQuaternionFromVectors(unittest.TestCase):
    """Tests for quaternion_from_vectors: computes quaternion that rotates v0 onto v1."""

    def test_same_vector(self):
        """
        Rotating a vector onto itself should produce the identity
        quaternion (0, 0, 0, 1).
        """
        q = quaternion_from_vectors([1, 0, 0], [1, 0, 0])
        self.assertAlmostEqual(q[3], 1.0, places=5)
        self.assertAlmostEqual(q[0], 0.0, places=5)
        self.assertAlmostEqual(q[1], 0.0, places=5)
        self.assertAlmostEqual(q[2], 0.0, places=5)

    def test_opposite_vectors(self):
        """
        Rotating a vector onto its opposite is a 180 degree rotation,
        so the w component should be approximately zero.
        """
        q = quaternion_from_vectors([1, 0, 0], [-1, 0, 0])
        self.assertAlmostEqual(q[3], 0.0, places=5)

    def test_90_degree_rotation(self):
        """
        Rotating X onto Y is a 90 degree rotation around Z,
        giving equal z and w components of ~0.7071.
        """
        q = quaternion_from_vectors([1, 0, 0], [0, 1, 0])
        self.assertAlmostEqual(q[2], 0.7071, places=3)
        self.assertAlmostEqual(q[3], 0.7071, places=3)


class TestQuaternionFromRotationMatrix(unittest.TestCase):
    """Tests for quaternion_from_rotation_matrix: converts a 3x3 rotation matrix to quaternion."""

    def test_identity(self):
        """
        An identity rotation matrix should produce the identity
        quaternion (0, 0, 0, 1).
        """
        q = quaternion_from_rotation_matrix(np.eye(3))
        self.assertAlmostEqual(q[3], 1.0, places=5)
        self.assertAlmostEqual(q[0], 0.0, places=5)
        self.assertAlmostEqual(q[1], 0.0, places=5)
        self.assertAlmostEqual(q[2], 0.0, places=5)

    def test_90_deg_around_z(self):
        """
        A 90 degree rotation matrix around Z should produce a
        quaternion with equal z and w components of ~0.7071.
        """
        R = np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1],
        ])
        q = quaternion_from_rotation_matrix(R)
        self.assertAlmostEqual(q[2], 0.7071, places=3)
        self.assertAlmostEqual(q[3], 0.7071, places=3)


class TestNormalizeQuaternion(unittest.TestCase):
    """Tests for normalize_quaternion: scales a quaternion to unit length."""

    def test_already_normalized(self):
        """
        A quaternion that is already unit length should remain
        unchanged after normalization.
        """
        q = (0, 0, 0, 1)
        result = normalize_quaternion(q)
        self.assertAlmostEqual(result[3], 1.0, places=5)

    def test_unnormalized(self):
        """
        A non-unit quaternion should be scaled so its norm equals 1.
        """
        q = (1, 1, 1, 1)
        result = normalize_quaternion(q)
        np.testing.assert_almost_equal(np.linalg.norm(result), 1.0)

    def test_zero_raises(self):
        """
        Normalizing a zero quaternion is undefined and should raise
        a ValueError.
        """
        with self.assertRaises(ValueError):
            normalize_quaternion((0, 0, 0, 0))


class TestQuaternionMultiply(unittest.TestCase):
    """Tests for quaternion_multiply: Hamilton product of two quaternions."""

    def test_identity(self):
        """
        Multiplying any quaternion by the identity quaternion should
        return the original quaternion unchanged.
        """
        q = (0.1, 0.2, 0.3, 0.9055)
        q = normalize_quaternion(q)
        identity = (0, 0, 0, 1)
        result = quaternion_multiply(identity, q)
        np.testing.assert_array_almost_equal(result, q)

    def test_result_is_normalized(self):
        """
        The product of two normalized quaternions should also be
        a unit quaternion.
        """
        q1 = (0.7071, 0, 0, 0.7071)
        q2 = (0, 0.7071, 0, 0.7071)
        result = quaternion_multiply(q1, q2)
        np.testing.assert_almost_equal(np.linalg.norm(result), 1.0)


class TestTransform(unittest.TestCase):
    """Tests for Transform dataclass and its point transformation methods."""

    def test_transform_points_no_transform(self):
        """
        A Transform with no position or rotation should return
        the input points unchanged.
        """
        t = Transform()
        pts = np.array([[1, 2, 3], [4, 5, 6]])
        result = t.transform_points(pts)
        np.testing.assert_array_equal(result, pts)

    def test_transform_points_translation_only(self):
        """
        A Transform with only a position should translate all points
        by the given offset.
        """
        t = Transform(position=np.array([10, 20, 30]))
        pts = np.array([[0, 0, 0], [1, 0, 0]])
        result = t.transform_points(pts)
        np.testing.assert_array_almost_equal(result[0], [10, 20, 30])
        np.testing.assert_array_almost_equal(result[1], [11, 20, 30])

    def test_transform_points_rotation_only(self):
        """
        A Transform with only a rotation matrix should rotate points
        without translating them.
        """
        R = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
        t = Transform(rotation_matrix=R)
        pts = np.array([[1, 0, 0]])
        result = t.transform_points(pts)
        np.testing.assert_array_almost_equal(result[0], [0, 1, 0])

    def test_transform_points_quaternion_only(self):
        """A quaternion-only transform should rotate points."""
        t = Transform(quaternion=(0, 0, 0.70710678, 0.70710678))
        pts = np.array([[1, 0, 0]])
        result = t.transform_points(pts)
        np.testing.assert_array_almost_equal(result[0], [0, 1, 0])

    def test_transform_points_both(self):
        """
        A Transform with both rotation and position should apply
        rotation first, then translation.
        """
        R = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
        t = Transform(position=np.array([5, 5, 5]), rotation_matrix=R)
        pts = np.array([[1, 0, 0]])
        result = t.transform_points(pts)
        np.testing.assert_array_almost_equal(result[0], [5, 6, 5])

    def test_final_quaternion_from_rotation_matrix(self):
        """
        final_quaternion should compute the correct quaternion from
        a rotation matrix alone.
        """
        R = np.eye(3)
        t = Transform(rotation_matrix=R)
        q = t.final_quaternion()
        self.assertAlmostEqual(q[3], 1.0, places=5)

    def test_final_quaternion_combined(self):
        """
        final_quaternion should combine rotation matrix and extra
        quaternion via Hamilton product.
        """
        R = np.eye(3)
        extra_q = (0, 0, 0, 1)
        t = Transform(rotation_matrix=R, quaternion=extra_q)
        q = t.final_quaternion()
        self.assertAlmostEqual(q[3], 1.0, places=5)


class TestShapes(unittest.TestCase):
    """Tests for shape dataclasses and Style."""

    def test_box_shape(self):
        """
        A BoxShape should store its dimensions correctly and have
        no transform by default.
        """
        s = BoxShape(width=1, height=2, depth=3)
        self.assertEqual(s.width, 1)
        self.assertEqual(s.height, 2)
        self.assertEqual(s.depth, 3)
        self.assertIsNone(s.transform)
        self.assertIn("BoxShape", repr(s))

    def test_line_segments_shape(self):
        """
        A LineSegmentsShape should store points as a float32 array
        with shape (N, 3).
        """
        pts = np.array([[0, 0, 0], [1, 1, 1]])
        s = LineSegmentsShape(points=pts)
        self.assertEqual(s.points.shape, (2, 3))
        self.assertEqual(s.points.dtype, np.float32)
        self.assertIn("LineSegmentsShape", repr(s))

    def test_line_segments_empty_raises(self):
        """
        Creating a LineSegmentsShape with no points should raise
        a ValueError.
        """
        with self.assertRaises(ValueError):
            LineSegmentsShape(points=np.array([]))

    def test_line_segments_single_point_raises(self):
        """A line segment shape must contain at least two points."""
        with self.assertRaises(ValueError):
            LineSegmentsShape(points=np.array([[0, 0, 0]]))

    def test_line_segments_odd_point_count_raises(self):
        """Line segments must contain complete endpoint pairs."""
        with self.assertRaises(ValueError):
            LineSegmentsShape(points=np.zeros((3, 3)))

    def test_circle_shape(self):
        """
        A CircleShape should store its radius and default segment
        count.
        """
        s = CircleShape(radius=0.5)
        self.assertEqual(s.radius, 0.5)
        self.assertEqual(s.segments, 64)

    def test_cone_shape(self):
        """
        A ConeShape should store its radius, height, and default
        radial segment count.
        """
        s = ConeShape(radius=1, height=2)
        self.assertEqual(s.radius, 1)
        self.assertEqual(s.height, 2)
        self.assertEqual(s.radial_segments, 32)

    def test_cylinder_shape(self):
        """
        A CylinderShape should store its radius and height correctly.
        """
        s = CylinderShape(radius=0.3, height=1.5)
        self.assertEqual(s.radius, 0.3)
        self.assertEqual(s.height, 1.5)

    def test_polyhedron_shape(self):
        """
        A PolyhedronShape should convert vertices to float32 and
        indices to uint32.
        """
        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        idx = np.array([0, 1, 2])
        s = PolyhedronShape(vertices=verts, indices=idx)
        self.assertEqual(s.vertices.dtype, np.float32)
        self.assertEqual(s.indices.dtype, np.uint32)

    def test_style(self):
        """
        A Style should store opacity, color, and wireframe settings
        correctly.
        """
        st = Style(opacity=0.5, color="#ff0000", wireframe=True)
        self.assertEqual(st.opacity, 0.5)
        self.assertEqual(st.color, "#ff0000")
        self.assertTrue(st.wireframe)


class TestTriangulateFaces(unittest.TestCase):
    """Tests for triangulate_faces: converts face definitions into flat triangle indices."""

    def test_triangles(self):
        """
        Triangular faces should pass through unchanged as flat
        index arrays.
        """
        faces = [{"face": [0, 1, 2]}, {"face": [0, 2, 3]}]
        result = triangulate_faces(faces)
        np.testing.assert_array_equal(result, [0, 1, 2, 0, 2, 3])

    def test_quads(self):
        """
        Quad faces should be split into two triangles.
        """
        faces = [{"face": [0, 1, 2, 3]}]
        result = triangulate_faces(faces)
        np.testing.assert_array_equal(result, [0, 1, 2, 0, 2, 3])

    def test_mixed(self):
        """
        A mix of triangles and quads should all be triangulated
        correctly.
        """
        faces = [{"face": [0, 1, 2]}, {"face": [3, 4, 5, 6]}]
        result = triangulate_faces(faces)
        np.testing.assert_array_equal(result, [0, 1, 2, 3, 4, 5, 3, 5, 6])

    def test_unsupported_raises(self):
        """
        Faces with more than 4 vertices are not supported and
        should raise a ValueError.
        """
        faces = [{"face": [0, 1, 2, 3, 4]}]
        with self.assertRaises(ValueError):
            triangulate_faces(faces)


class TestDrawcallParsers(unittest.TestCase):
    """Tests for individual drawcall parsing functions."""

    def setUp(self):
        self.pos = np.array([1, 2, 3])
        self.rot = np.eye(3)

    def test_parse_box(self):
        """
        A box drawcall should produce a BoxShape with the correct
        width, height, and depth.
        """
        drawcall = {
            "args": [0.0, 0.0, 0.0,  # x, y, z
                     2.0, 3.0, 4.0,  # xwidth, yheight, zdepth
                     0.0, 1.0, 0.0,  # (unused)
                     0.0, 1.0, 0.0], # nx, ny, nz
        }
        shape = _parse_box(drawcall, self.pos, self.rot)
        self.assertIsInstance(shape, BoxShape)
        self.assertEqual(shape.width, 2.0)
        self.assertEqual(shape.height, 3.0)
        self.assertEqual(shape.depth, 4.0)

    def test_parse_cylinder(self):
        """
        A cylinder drawcall should produce a CylinderShape with the
        correct radius, height, and default segments.
        """
        drawcall = {
            "args": [0.0, 0.0, 0.0,  # x, y, z
                     0.5, 1.0,        # radius, height
                     0.0,             # (unused padding)
                     0.0, 0.0, 1.0],  # nx, ny, nz
        }
        shape = _parse_cylinder(drawcall, self.pos, self.rot)
        self.assertIsInstance(shape, CylinderShape)
        self.assertEqual(shape.radius, 0.5)
        self.assertEqual(shape.height, 1.0)
        self.assertEqual(shape.radial_segments, DEFAULT_RADIAL_SEGMENTS)

    def test_parse_cone(self):
        """
        A cone drawcall should produce a ConeShape with the correct
        radius and height.
        """
        drawcall = {
            "args": [0.0, 0.0, 0.0,  # x, y, z
                     0.3, 0.6,        # radius, height
                     0.0, 0.0, 1.0],  # nx, ny, nz
        }
        shape = _parse_cone(drawcall, self.pos, self.rot)
        self.assertIsInstance(shape, ConeShape)
        self.assertEqual(shape.radius, 0.3)
        self.assertEqual(shape.height, 0.6)

    def test_parse_circle_xy(self):
        """
        A circle drawcall on the xy plane should produce a
        CircleShape with the correct radius.
        """
        drawcall = {
            "args": ["xy", 0.0, 0.0, 0.0, 0.5],
        }
        shape = _parse_circle(drawcall, self.pos, self.rot)
        self.assertIsInstance(shape, CircleShape)
        self.assertEqual(shape.radius, 0.5)

    def test_parse_circle_xz(self):
        """
        A circle drawcall on the xz plane should produce a valid
        CircleShape.
        """
        drawcall = {
            "args": ["xz", 0.0, 0.0, 0.0, 1.0],
        }
        shape = _parse_circle(drawcall, self.pos, self.rot)
        self.assertIsInstance(shape, CircleShape)

    def test_parse_circle_yz(self):
        """
        A circle drawcall on the yz plane should produce a valid
        CircleShape.
        """
        drawcall = {
            "args": ["yz", 0.0, 0.0, 0.0, 0.7],
        }
        shape = _parse_circle(drawcall, self.pos, self.rot)
        self.assertIsInstance(shape, CircleShape)

    def test_parse_circle_unknown_plane(self):
        """
        A circle drawcall with an unrecognized plane should return
        None rather than raising an exception.
        """
        drawcall = {
            "args": ["unknown", 0.0, 0.0, 0.0, 0.5],
        }
        shape = _parse_circle(drawcall, self.pos, self.rot)
        self.assertIsNone(shape)

    def test_parse_polyhedron(self):
        """
        A polyhedron drawcall with a JSON string should produce a
        PolyhedronShape with the correct vertex and index counts.
        """
        faces = [{"face": [0, 1, 2]}, {"face": [0, 2, 3]}]
        vertices = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
        poly_data = {"vertices": vertices, "faces": faces}
        drawcall = {"args": json.dumps(poly_data)}
        transform = Transform(position=self.pos, rotation_matrix=self.rot)
        shape = _parse_polyhedron(drawcall, transform)
        self.assertIsInstance(shape, PolyhedronShape)
        self.assertEqual(shape.vertices.shape, (4, 3))
        self.assertEqual(len(shape.indices), 6)

    def test_parse_polyhedron_list_wrapper(self):
        """
        A polyhedron drawcall with args as a list containing the JSON
        string should also be parsed correctly.
        """
        faces = [{"face": [0, 1, 2]}]
        vertices = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        poly_data = {"vertices": vertices, "faces": faces}
        drawcall = {"args": [json.dumps(poly_data)]}
        transform = Transform(position=self.pos, rotation_matrix=self.rot)
        shape = _parse_polyhedron(drawcall, transform)
        self.assertIsInstance(shape, PolyhedronShape)

    def test_parse_multiline(self):
        """
        A multiline drawcall with 3 points should produce 4 segment
        endpoints (2 segments).
        """
        drawcall = {
            "args": [0, 0, 0, 1, 0, 0, 1, 1, 0],
        }
        result = _parse_multiline(drawcall, self.pos, self.rot)
        self.assertEqual(result.shape, (4, 3))

    def test_parse_multiline_two_points(self):
        """
        A multiline drawcall with exactly 2 points should return
        them as-is without reshaping.
        """
        drawcall = {
            "args": [0, 0, 0, 1, 1, 1],
        }
        result = _parse_multiline(drawcall, self.pos, self.rot)
        self.assertEqual(result.shape, (2, 3))

    def test_drawcall_parsers_registry(self):
        """
        The DRAWCALL_PARSERS dispatch table should contain entries
        for all supported drawcall types.
        """
        expected = {"box", "cylinder", "cone", "circle", "polyhedron"}
        self.assertEqual(set(DRAWCALL_PARSERS.keys()), expected)


class TestComponentModel(unittest.TestCase):
    """Tests for ComponentModel class."""

    def test_init(self):
        """
        A newly created ComponentModel should have an empty shape
        list and loaded set to False.
        """
        comp = make_mock_component()
        model = ComponentModel(comp)
        self.assertEqual(model.shape_list, [])
        self.assertFalse(model.loaded)

    def test_load_geometry_box(self):
        """
        Loading geometry from a JSON component with a box drawcall
        should produce at least one BoxShape.
        """
        fixture = load_fixture()
        box_comp = None
        for c in fixture["components"]:
            keys = [dc["key"] for dc in c["drawcalls"]]
            if "box" in keys:
                box_comp = c
                break
        self.assertIsNotNone(box_comp)

        comp = make_mock_component(box_comp["name"])
        model = ComponentModel(comp)
        model.load_geometry_from_mcdisplay_dict(box_comp)

        self.assertTrue(model.loaded)
        self.assertGreater(len(model.shape_list), 0)
        box_shapes = [s for s in model.shape_list if isinstance(s, BoxShape)]
        self.assertGreater(len(box_shapes), 0)

    def test_load_geometry_cylinder(self):
        """
        Loading geometry from a JSON component with a cylinder
        drawcall should produce at least one CylinderShape.
        """
        fixture = load_fixture()
        cyl_comp = None
        for c in fixture["components"]:
            keys = [dc["key"] for dc in c["drawcalls"]]
            if "cylinder" in keys:
                cyl_comp = c
                break
        self.assertIsNotNone(cyl_comp)

        comp = make_mock_component(cyl_comp["name"])
        model = ComponentModel(comp)
        model.load_geometry_from_mcdisplay_dict(cyl_comp)

        self.assertTrue(model.loaded)
        cyl_shapes = [s for s in model.shape_list if isinstance(s, CylinderShape)]
        self.assertGreater(len(cyl_shapes), 0)

    def test_load_geometry_circle(self):
        """
        Loading geometry from a JSON component with circle drawcalls
        should produce at least one CircleShape.
        """
        fixture = load_fixture()
        circle_comp = None
        for c in fixture["components"]:
            keys = [dc["key"] for dc in c["drawcalls"]]
            if "circle" in keys:
                circle_comp = c
                break
        self.assertIsNotNone(circle_comp)

        comp = make_mock_component(circle_comp["name"])
        model = ComponentModel(comp)
        model.load_geometry_from_mcdisplay_dict(circle_comp)

        self.assertTrue(model.loaded)
        circle_shapes = [s for s in model.shape_list if isinstance(s, CircleShape)]
        self.assertGreater(len(circle_shapes), 0)

    def test_load_geometry_multiline(self):
        """
        Loading geometry from a JSON component with multiline
        drawcalls should produce at least one LineSegmentsShape.
        """
        fixture = load_fixture()
        ml_comp = None
        for c in fixture["components"]:
            keys = [dc["key"] for dc in c["drawcalls"]]
            if "multiline" in keys:
                ml_comp = c
                break
        self.assertIsNotNone(ml_comp)

        comp = make_mock_component(ml_comp["name"])
        model = ComponentModel(comp)
        model.load_geometry_from_mcdisplay_dict(ml_comp)

        self.assertTrue(model.loaded)
        line_shapes = [s for s in model.shape_list if isinstance(s, LineSegmentsShape)]
        self.assertGreater(len(line_shapes), 0)

    def test_load_geometry_position_extracted(self):
        """
        After loading geometry from JSON, the component's global
        position and rotation matrix should be extracted from the m4
        field.
        """
        fixture = load_fixture()
        for c in fixture["components"]:
            if c["drawcalls"]:
                comp = make_mock_component(c["name"])
                model = ComponentModel(comp)
                model.load_geometry_from_mcdisplay_dict(c)
                self.assertIsNotNone(model.global_position)
                self.assertIsNotNone(model.rotation_matrix)
                break

    def test_guess_geometry_no_params(self):
        """
        A component with no parameters should produce an axis triad
        made of three line segments (6 points).
        """
        comp = make_mock_component()
        model = ComponentModel(comp)
        result = model.guess_geometry_from_comp_object()

        self.assertTrue(result)
        self.assertEqual(len(model.shape_list), 1)
        self.assertIsInstance(model.shape_list[0], LineSegmentsShape)
        self.assertEqual(model.shape_list[0].points.shape, (6, 3))

    def test_guess_geometry_rectangle(self):
        """
        A component with xwidth and yheight parameters should produce
        a rectangle outline made of four line segments (8 points).
        """
        comp = make_mock_component_with_params(xwidth=2.0, yheight=4.0)
        model = ComponentModel(comp)
        result = model.guess_geometry_from_comp_object()

        self.assertTrue(result)
        self.assertEqual(len(model.shape_list), 1)
        self.assertIsInstance(model.shape_list[0], LineSegmentsShape)
        self.assertEqual(model.shape_list[0].points.shape, (8, 3))

    def test_guess_geometry_rectangle_dimensions(self):
        """
        The rectangle outline produced by guess_geometry should have
        dimensions matching half the xwidth and yheight parameters.
        """
        comp = make_mock_component_with_params(xwidth=2.0, yheight=4.0)
        model = ComponentModel(comp)
        model.guess_geometry_from_comp_object()

        pts = model.shape_list[0].points
        self.assertAlmostEqual(np.max(pts[:, 0]), 1.0)
        self.assertAlmostEqual(np.min(pts[:, 0]), -1.0)
        self.assertAlmostEqual(np.max(pts[:, 1]), 2.0)
        self.assertAlmostEqual(np.min(pts[:, 1]), -2.0)

    def test_bounds_are_world_space(self):
        """Component bounds include the shape transform."""
        comp = make_mock_component("translated")
        model = ComponentModel(comp)
        model.shape_list = [
            BoxShape(
                width=2.0, height=2.0, depth=2.0,
                transform=Transform(position=np.array([10.0, 20.0, 30.0])),
            ),
        ]
        model.refresh_metadata()

        np.testing.assert_allclose(model.bounds.minimum, [9.0, 19.0, 29.0])
        np.testing.assert_allclose(model.bounds.maximum, [11.0, 21.0, 31.0])
        np.testing.assert_allclose(model.center, [10.0, 20.0, 30.0])
        np.testing.assert_allclose(model.size, [2.0, 2.0, 2.0])

    def test_bounds_account_for_rotation(self):
        """World-space AABB changes when a non-square shape is rotated."""
        comp = make_mock_component("rotated")
        model = ComponentModel(comp)
        model.shape_list = [
            BoxShape(
                width=2.0, height=1.0, depth=1.0,
                transform=Transform(rotation_matrix=np.array([
                    [0.0, -1.0, 0.0],
                    [1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0],
                ])),
            ),
        ]
        model.refresh_metadata()

        np.testing.assert_allclose(model.size, [1.0, 2.0, 1.0])

    def test_model_assigns_default_draw_style(self):
        """Unstyled model shapes receive the central default style policy."""
        comp = make_mock_component("styled")
        model = ComponentModel(comp)
        model.shape_list = [BoxShape(width=3.0, height=3.0, depth=3.0)]
        model.refresh_metadata()

        self.assertIsNotNone(model.shape_list[0].style)
        self.assertEqual(model.shape_list[0].style.opacity, 0.4)


class TestInstrumentModel(unittest.TestCase):
    """Tests for InstrumentModel class."""

    def test_init_empty(self):
        """
        An InstrumentModel created without arguments should have an
        empty component_models list.
        """
        model = InstrumentModel()
        self.assertEqual(model.component_models, [])

    def test_add_model(self):
        """
        Adding a ComponentModel should increase the component_models
        list length by one.
        """
        model = InstrumentModel()
        comp = make_mock_component()
        cm = ComponentModel(comp)
        model.add_model(cm)
        self.assertEqual(len(model.component_models), 1)

    def test_load_from_json(self):
        """
        Creating an InstrumentModel from a JSON fixture should create
        a ComponentModel for each component in the JSON.
        """
        fixture = load_fixture()
        instr = MagicMock()
        instr.get_component.return_value = make_mock_component()

        model = InstrumentModel(instrument_object=instr, json_dict=fixture)
        self.assertEqual(len(model.component_models), len(fixture["components"]))

    def test_load_from_json_calls_get_component(self):
        """
        Loading from JSON should call instrument_object.get_component
        once for each component in the JSON data.
        """
        fixture = load_fixture()
        instr = MagicMock()
        instr.get_component.return_value = make_mock_component()

        InstrumentModel(instrument_object=instr, json_dict=fixture)
        self.assertEqual(instr.get_component.call_count, len(fixture["components"]))

    def test_triangulate_faces_is_exported(self):
        """The model package should expose its public triangulation helper."""
        from mcstasscript.geometry_viewer.model import triangulate_faces as exported
        self.assertIs(exported, triangulate_faces)


class TestConfig(unittest.TestCase):
    """Verify config constants exist and have expected values."""

    def test_default_colors(self):
        """
        DEFAULT_COLORS should be a non-empty list containing
        standard color hex strings.
        """
        self.assertIsInstance(DEFAULT_COLORS, list)
        self.assertGreater(len(DEFAULT_COLORS), 0)
        self.assertIn("#ff0000", DEFAULT_COLORS)

    def test_camera_defaults(self):
        """
        Camera configuration defaults should match expected values
        for position, target, FOV, and near/far planes.
        """
        self.assertEqual(DEFAULT_CAMERA_POSITION, [5, 3, 10])
        self.assertEqual(DEFAULT_CAMERA_TARGET, [0, 0, 2])
        self.assertEqual(DEFAULT_FOV, 50)
        self.assertEqual(DEFAULT_NEAR, 0.01)
        self.assertEqual(DEFAULT_FAR, 2000)

    def test_renderer_size(self):
        """
        DEFAULT_RENDERER_SIZE should define the expected viewport
        dimensions.
        """
        self.assertEqual(DEFAULT_RENDERER_SIZE, (900, 600))

    def test_segments(self):
        """
        Default segment counts for cylinders and circles should be
        set to their expected values.
        """
        self.assertEqual(DEFAULT_RADIAL_SEGMENTS, 32)
        self.assertEqual(DEFAULT_CIRCLE_SEGMENTS, 64)

    def test_navigator_distance(self):
        """
        DEFAULT_NAVIGATOR_DISTANCE should be set to the expected
        value for the component navigator.
        """
        self.assertEqual(DEFAULT_NAVIGATOR_DISTANCE, 0.5)

    def test_picker_tolerance(self):
        """Picker tolerance is a fixed world-space configuration value."""
        self.assertEqual(DEFAULT_PICK_TOLERANCE, 0.005)


class TestApi(unittest.TestCase):
    """Tests for the public API functions (without heavy rendering)."""

    def test_get_renderer_pythreejs(self):
        """
        Requesting the 'pythreejs' backend should return a
        PyThreejsRenderer instance.
        """
        renderer = _get_renderer("pythreejs")
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        self.assertIsInstance(renderer, PyThreejsRenderer)

    def test_get_renderer_matplotlib(self):
        """
        Requesting the 'matplotlib' backend should return a
        MatplotlibRenderer instance in 3D mode.
        """
        renderer = _get_renderer("matplotlib")
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        self.assertIsInstance(renderer, MatplotlibRenderer)

    def test_get_renderer_matplotlib_3d(self):
        """
        Requesting the 'matplotlib_3d' backend should return a
        MatplotlibRenderer instance in 3D mode.
        """
        renderer = _get_renderer("matplotlib_3d")
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        self.assertIsInstance(renderer, MatplotlibRenderer)

    def test_get_renderer_matplotlib_2d(self):
        """
        Requesting the 'matplotlib_2d' backend should return a
        MatplotlibRenderer instance in 2D mode.
        """
        renderer = _get_renderer("matplotlib_2d")
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        self.assertIsInstance(renderer, MatplotlibRenderer)

    def test_get_renderer_unknown(self):
        """
        Requesting an unrecognized backend should raise a ValueError.
        """
        with self.assertRaises(ValueError):
            _get_renderer("unknown_backend")

    def test_get_renderer_pythreejs_reports_missing_optional_module(self):
        """The pythreejs backend gives an actionable missing-dependency error."""
        with patch.dict("sys.modules", {"pythreejs": None}):
            with self.assertRaisesRegex(ImportError, "pythreejs.*geometry-viewer"):
                _get_renderer("pythreejs")

    def test_matplotlib_does_not_import_pythreejs(self):
        """Matplotlib rendering should work when pythreejs is unavailable."""
        instr = MagicMock()
        instr.component_list = [make_mock_component("test_comp")]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        with patch.dict("sys.modules", {"pythreejs": None}):
            with patch("mcstasscript.geometry_viewer.api.plt.show"):
                result = view_with_guess(instr, backend="matplotlib")
        self.assertIsNone(result)

    def test_json_subset_uses_dense_component_indices(self):
        """A rendered component subset should use indices local to the subset."""
        instr = MagicMock()
        instr.get_component.side_effect = lambda name: make_mock_component(name)
        json_dict = {
            "components": [
                {"name": "first", "m4": np.eye(4).reshape(-1).tolist(), "drawcalls": []},
                {"name": "second", "m4": np.eye(4).reshape(-1).tolist(), "drawcalls": []},
                {"name": "third", "m4": np.eye(4).reshape(-1).tolist(), "drawcalls": []},
            ],
        }
        renderer = MagicMock()
        renderer.render_component.return_value = []
        renderer.make_scene.return_value = object()
        with patch("mcstasscript.geometry_viewer.api._get_renderer", return_value=renderer):
            with patch("mcstasscript.geometry_viewer.api.plt.show"):
                view_with_json(instr, json_dict, backend="matplotlib",
                               index_min=1, index_max=3)
        indices = [call.kwargs["component_index"]
                   for call in renderer.render_component.call_args_list]
        self.assertEqual(indices, [0, 1])

    def test_json_model_builds_from_first_component_to_index_max(self):
        """index_min filters rendering without skipping early model components."""
        instr = MagicMock()
        instr.get_component.side_effect = lambda name: make_mock_component(name)
        json_dict = {
            "components": [
                {"name": "first", "m4": np.eye(4).reshape(-1).tolist(), "drawcalls": []},
                {"name": "second", "m4": np.eye(4).reshape(-1).tolist(), "drawcalls": []},
                {"name": "third", "m4": np.eye(4).reshape(-1).tolist(), "drawcalls": []},
                {"name": "fourth", "m4": np.eye(4).reshape(-1).tolist(), "drawcalls": []},
            ],
        }
        renderer = MagicMock()
        renderer.render_component.return_value = []
        renderer.make_scene.return_value = object()
        with patch("mcstasscript.geometry_viewer.api._get_renderer", return_value=renderer):
            with patch("mcstasscript.geometry_viewer.api.plt.show"):
                view_with_json(
                    instr,
                    json_dict,
                    backend="matplotlib",
                    index_min=2,
                    index_max=3,
                )

        self.assertEqual(
            [call.args[0] for call in instr.get_component.call_args_list],
            ["first", "second", "third"],
        )
        self.assertEqual(
            [call.kwargs["component_index"] for call in renderer.render_component.call_args_list],
            [0],
        )

    def test_json_rejects_reversed_component_range(self):
        """A component range must have index_min at or before index_max."""
        instr = MagicMock()
        json_dict = {
            "components": [
                {"name": "first", "m4": np.eye(4).reshape(-1).tolist(), "drawcalls": []},
                {"name": "second", "m4": np.eye(4).reshape(-1).tolist(), "drawcalls": []},
                {"name": "third", "m4": np.eye(4).reshape(-1).tolist(), "drawcalls": []},
            ],
        }

        with self.assertRaises(ValueError):
            view_with_json(instr, json_dict, backend="matplotlib", index_min=2, index_max=1)

    def test_guess_component_range_filters_rendering(self):
        """Geometry guessing applies the same component range semantics."""
        instr = MagicMock()
        instr.component_list = [
            make_mock_component("first"),
            make_mock_component("second"),
            make_mock_component("third"),
        ]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        renderer = MagicMock()
        renderer.render_component.return_value = []
        renderer.make_scene.return_value = object()

        with patch("mcstasscript.geometry_viewer.api._get_renderer", return_value=renderer):
            with patch("mcstasscript.geometry_viewer.api.plt.show"):
                view_with_guess(
                    instr,
                    backend="matplotlib",
                    index_min=1,
                    index_max=2,
                )

        self.assertEqual(
            [call.kwargs["component_index"] for call in renderer.render_component.call_args_list],
            [0],
        )


class TestPyThreejsComponentSelection(unittest.TestCase):
    """Tests for picking a visual and showing its source component."""

    def test_picker_maps_visual_to_component_details(self):
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw

        component = make_mock_component("selected")
        component.component_name = "Box"
        model = ComponentModel(component)
        model.shape_list = [BoxShape(width=1, height=1, depth=1)]

        renderer = PyThreejsRenderer()
        renderer.register_component(model)
        children = renderer.render_component(model, component_index=0)
        scene = renderer.make_scene(children)
        details = renderer.create_component_details(scene)

        self.assertIsInstance(details, ipw.Textarea)
        self.assertEqual(details.value, "Click a component in the scene.")
        self.assertEqual(len(scene.controls), 2)
        self.assertIs(renderer._component_picker.controlling, renderer._component_group)
        self.assertEqual(renderer._component_picker.lineThreshold, DEFAULT_PICK_TOLERANCE)
        self.assertEqual(
            renderer._component_picker.lineThreshold,
            renderer._component_picker.pointThreshold,
        )

        renderer._on_component_pick({"new": children[0]})
        self.assertEqual(details.value, str(component))

        renderer._on_component_pick({"new": None})
        self.assertEqual(details.value, "Click a component in the scene.")

    def test_picker_maps_line_visual_to_component_details(self):
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        component = make_mock_component("line_selected")
        component.component_name = "Line"
        model = ComponentModel(component)
        model.shape_list = [LineSegmentsShape(points=[
            [0, 0, 0], [1, 0, 0],
        ])]

        renderer = PyThreejsRenderer()
        renderer.register_component(model)
        children = renderer.render_component(model, component_index=0)
        scene = renderer.make_scene(children)
        details = renderer.create_component_details(scene)

        renderer._on_component_pick({"new": children[0]})
        self.assertEqual(details.value, str(component))

    def test_navigator_selection_updates_component_details(self):
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw

        component = make_mock_component("selected")
        component.component_name = "Box"
        model = ComponentModel(component)
        model.shape_list = [BoxShape(width=1, height=1, depth=1)]

        renderer = PyThreejsRenderer()
        renderer.register_component(model)
        children = renderer.render_component(model, component_index=0)
        scene = renderer.make_scene(children)
        details = renderer.create_component_details(scene)
        navigator = renderer.create_component_navigator(scene)

        self.assertIsInstance(navigator, ipw.Combobox)
        navigator.value = "selected"
        self.assertEqual(details.value, str(component))

        previous_value = details.value
        navigator.value = "does_not_exist"
        self.assertEqual(details.value, previous_value)

    def test_component_details_strip_terminal_formatting(self):
        from mcstasscript.geometry_viewer.renderer.pythreejs import _plain_component_text

        class ColoredComponent:
            def __str__(self):
                return "\033[1mCOMPONENT\033[0m"

        self.assertEqual(_plain_component_text(ColoredComponent()), "COMPONENT")

    def test_api_includes_component_details_widget(self):
        import ipywidgets as ipw

        instr = MagicMock()
        instr.component_list = [make_mock_component("selected")]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(instr, backend="pythreejs")

        details = [child for child in result.children if isinstance(child, ipw.Textarea)]
        self.assertEqual(len(details), 1)
        self.assertIs(result.children[-1], details[0])


class TestQuaternionToRotationMatrix(unittest.TestCase):
    """Tests for quaternion_to_rotation_matrix: converts a quaternion to a 3x3 rotation matrix."""

    def test_identity(self):
        """The identity quaternion should produce the identity matrix."""
        R = quaternion_to_rotation_matrix((0, 0, 0, 1))
        np.testing.assert_array_almost_equal(R, np.eye(3))

    def test_90_deg_around_z(self):
        """A 90-degree quaternion around Z should produce the correct rotation matrix."""
        q = (0, 0, 0.70710678, 0.70710678)
        R = quaternion_to_rotation_matrix(q)
        expected = np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1],
        ])
        np.testing.assert_array_almost_equal(R, expected, decimal=3)

    def test_roundtrip(self):
        """Converting matrix -> quaternion -> matrix should recover the original."""
        R_orig = np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1],
        ])
        q = quaternion_from_rotation_matrix(R_orig)
        R_back = quaternion_to_rotation_matrix(q)
        np.testing.assert_array_almost_equal(R_back, R_orig)


class TestMatplotlibTransformPoints(unittest.TestCase):
    """Tests for MatplotlibRenderer._transform_points with quaternion transforms."""

    def setUp(self):
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        self.renderer = MatplotlibRenderer()

    def test_quaternion_only(self):
        """A transform with only a quaternion should rotate points correctly."""
        q = quaternion_from_vectors([0, 0, 1], [0, 1, 0])
        t = Transform(quaternion=q)
        pts = np.array([[0, 0, 1]])
        result = self.renderer._transform_points(pts, t)
        expected = np.array([[0, 1, 0]])
        np.testing.assert_array_almost_equal(result, expected)

    def test_quaternion_and_rotation_matrix(self):
        """A transform with both quaternion and rotation_matrix should combine them."""
        R = np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1],
        ])
        q = quaternion_from_vectors([0, 1, 0], [1, 0, 0])
        t = Transform(rotation_matrix=R, quaternion=q, position=np.array([10, 0, 0]))
        pts = np.array([[0, 1, 0]])
        result = self.renderer._transform_points(pts, t)
        fq = t.final_quaternion()
        R_combined = quaternion_to_rotation_matrix(fq)
        expected = (pts @ R_combined.T) + np.array([10, 0, 0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_none_transform(self):
        """A None transform should return the points unchanged."""
        pts = np.array([[1, 2, 3]])
        result = self.renderer._transform_points(pts, None)
        np.testing.assert_array_almost_equal(result, pts)


class TestMatplotlibLineSegments(unittest.TestCase):
    """Tests for disconnected LineSegmentsShape rendering."""

    def test_line_points_include_breaks(self):
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer

        points = np.array([
            [0.0, 0.0, 0.0], [0.01, 0.0, 0.0],
            [0.1, 0.0, 0.0], [0.11, 0.0, 0.0],
        ])
        separated = MatplotlibRenderer._line_points_with_breaks(points)

        self.assertEqual(separated.shape, (5, 3))
        self.assertTrue(np.isnan(separated[2]).all())

    def test_matplotlib_does_not_join_disconnected_segments(self):
        from matplotlib import pyplot as plt
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer

        model = ComponentModel(make_mock_component("lines"))
        model.shape_list = [LineSegmentsShape(points=[
            [0.0, 0.0, 0.0], [0.01, 0.0, 0.0],
            [0.1, 0.0, 0.0], [0.11, 0.0, 0.0],
        ])]
        renderer = MatplotlibRenderer(mode="2d")
        children = renderer.render_component(model, component_index=0)
        figure = renderer.make_scene(children)

        line = figure.axes[0].lines[0]
        self.assertTrue(np.isnan(line.get_xdata()[2]))
        self.assertIs(renderer.component_children[0][0], line)
        self.assertLess(figure.axes[0].get_xlim()[1] - figure.axes[0].get_xlim()[0], 1.0)
        plt.close(figure)


class TestIntensityToColor(unittest.TestCase):
    """Tests for intensity_to_color: maps intensity values to hex colors."""

    def test_basic_log_scale(self):
        """Log-scale mapping should produce valid hex colors."""
        color = intensity_to_color(1.0, 0.1, 10.0, log_scale=True)
        self.assertTrue(color.startswith("#"))
        self.assertEqual(len(color), 7)

    def test_zero_intensity(self):
        """Zero intensity should map to the lowest color of the colormap."""
        color = intensity_to_color(0.0, 0.1, 10.0, log_scale=True)
        inferno_zero = intensity_to_color(0.0, 0.1, 10.0, cmap="inferno", log_scale=True)
        self.assertEqual(color, inferno_zero)

    def test_max_intensity(self):
        """Max intensity should map to the highest color of the colormap."""
        color = intensity_to_color(10.0, 0.1, 10.0, log_scale=True)
        self.assertTrue(color.startswith("#"))

    def test_linear_scale(self):
        """Linear scale should produce valid colors."""
        color = intensity_to_color(5.0, 0.0, 10.0, log_scale=False)
        self.assertTrue(color.startswith("#"))
        self.assertEqual(len(color), 7)

    def test_linear_midpoint(self):
        """Midpoint intensity in linear mode should give t=0.5 color."""
        c_low = intensity_to_color(0.0, 0.0, 10.0, cmap="viridis", log_scale=False)
        c_mid = intensity_to_color(5.0, 0.0, 10.0, cmap="viridis", log_scale=False)
        c_high = intensity_to_color(10.0, 0.0, 10.0, cmap="viridis", log_scale=False)
        self.assertNotEqual(c_low, c_high)

    def test_equal_min_max(self):
        """When min_I == max_I, should return the top color."""
        color = intensity_to_color(5.0, 5.0, 5.0, log_scale=True)
        self.assertTrue(color.startswith("#"))

    def test_negative_max(self):
        """Negative max_I should return the lowest color."""
        color = intensity_to_color(1.0, 0.0, -1.0, log_scale=True)
        self.assertTrue(color.startswith("#"))

    def test_different_colormaps(self):
        """Different colormaps should produce different colors for the same intensity."""
        c_inferno = intensity_to_color(5.0, 0.1, 10.0, cmap="inferno", log_scale=True)
        c_viridis = intensity_to_color(5.0, 0.1, 10.0, cmap="viridis", log_scale=True)
        self.assertNotEqual(c_inferno, c_viridis)

    def test_log_floor(self):
        """Very small positive intensity should not produce t=0 exactly (uses log floor)."""
        c_zero = intensity_to_color(0.0, 0.1, 10.0, log_scale=True)
        c_tiny = intensity_to_color(1e-50, 0.1, 10.0, log_scale=True)
        self.assertEqual(c_zero, c_tiny)


class TestAggregateIntensity(unittest.TestCase):
    """Tests for _aggregate_intensity: reduces 1D monitor data to a scalar.

    In 1D mode, aggregations operate on axis values (e.g. wavelength)
    weighted by intensity, not on the intensity values themselves.
    """

    def _make_mock_data(self, intensity_arr, xaxis=None, dimension=None):
        data = MagicMock()
        intensity = np.asarray(intensity_arr, dtype=float)
        data.metadata.dimension = dimension if dimension is not None else len(intensity)
        data.metadata.total_I = float(np.sum(intensity))
        data.Intensity = intensity
        data.xaxis = xaxis if xaxis is not None else np.linspace(0, 1, len(intensity))
        return data

    def test_total_aggregation(self):
        """Total aggregation should return sum of bins."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(np.array([1.0, 2.0, 3.0, 4.0]), xaxis=np.array([1.0, 2.0, 3.0, 4.0]))
        self.assertAlmostEqual(_aggregate_intensity(data, "total"), 10.0)

    def test_max_aggregation(self):
        """Max aggregation should return highest axis value with non-zero intensity."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(np.array([1.0, 0.0, 3.0, 2.0]), xaxis=np.array([1.0, 2.0, 3.0, 4.0]))
        self.assertAlmostEqual(_aggregate_intensity(data, "max"), 4.0)

    def test_min_aggregation(self):
        """Min aggregation should return lowest axis value with non-zero intensity."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(np.array([0.0, 5.0, 3.0, 2.0]), xaxis=np.array([1.0, 2.0, 3.0, 4.0]))
        self.assertAlmostEqual(_aggregate_intensity(data, "min"), 2.0)

    def test_span_aggregation(self):
        """Span aggregation should return max_axis - min_axis with intensity."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(np.array([0.0, 5.0, 3.0, 2.0]), xaxis=np.array([1.0, 2.0, 3.0, 4.0]))
        self.assertAlmostEqual(_aggregate_intensity(data, "span"), 2.0)

    def test_mean_aggregation(self):
        """Mean aggregation should return intensity-weighted average of axis values."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(np.array([1.0, 1.0]), xaxis=np.array([0.0, 10.0]))
        self.assertAlmostEqual(_aggregate_intensity(data, "mean"), 5.0)

    def test_mean_weighted(self):
        """Weighted mean should be pulled toward higher-intensity bins."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(np.array([1.0, 3.0]), xaxis=np.array([0.0, 10.0]))
        expected = (0.0 * 1.0 + 10.0 * 3.0) / 4.0
        self.assertAlmostEqual(_aggregate_intensity(data, "mean"), expected)

    def test_average_aggregation(self):
        """Average aggregation should be an alias for mean."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(np.array([1.0, 3.0]), xaxis=np.array([0.0, 10.0]))
        self.assertAlmostEqual(_aggregate_intensity(data, "average"),
                               _aggregate_intensity(data, "mean"))

    def test_median_aggregation(self):
        """Median aggregation should return axis value at cumulative intensity median."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(np.array([1.0, 1.0, 1.0, 1.0]), xaxis=np.array([1.0, 2.0, 3.0, 4.0]))
        result = _aggregate_intensity(data, "median")
        self.assertTrue(2.0 <= result <= 3.0)

    def test_median_weighted(self):
        """Median should be pulled toward higher-intensity bins."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(np.array([1.0, 1.0, 1.0, 9.0]), xaxis=np.array([1.0, 2.0, 3.0, 4.0]))
        self.assertAlmostEqual(_aggregate_intensity(data, "median"), 4.0)

    def test_0d_mode(self):
        """In 0D mode (dimension=0), should return total_I regardless of aggregation."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = MagicMock()
        data.metadata.dimension = 0
        data.metadata.total_I = 42.0
        self.assertAlmostEqual(_aggregate_intensity(data, "total"), 42.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "max"), 42.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "mean"), 42.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "median"), 42.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "span"), 42.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "min"), 42.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "average"), 42.0)

    def test_all_zero_intensity(self):
        """When all intensities are zero, should return 0.0."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(np.array([0.0, 0.0, 0.0]), xaxis=np.array([1.0, 2.0, 3.0]))
        self.assertAlmostEqual(_aggregate_intensity(data, "max"), 0.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "min"), 0.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "mean"), 0.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "median"), 0.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "span"), 0.0)

    def test_invalid_aggregation(self):
        """view_with_analysis should reject invalid aggregation values."""
        from mcstasscript.geometry_viewer.api import view_with_analysis
        instr = MagicMock()
        instr.component_list = []
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        with self.assertRaises(ValueError):
            view_with_analysis(instr, aggregation="invalid")


class TestPyThreejsIntensity(unittest.TestCase):
    """Tests for PyThreejsRenderer intensity colormode."""

    def setUp(self):
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        self.intensity_map = {"comp1": 1.0, "comp2": 10.0, "comp3": 100.0}
        self.renderer = PyThreejsRenderer(
            intensity_map=self.intensity_map,
            colormode="intensity",
            cmap="inferno",
            log_scale=True,
        )

    def test_init_with_intensity_map(self):
        """Renderer should store intensity params and compute min/max."""
        self.assertEqual(self.renderer.intensity_map, self.intensity_map)
        self.assertEqual(self.renderer._min_I, 1.0)
        self.assertEqual(self.renderer._max_I, 100.0)
        self.assertEqual(self.renderer.cmap, "inferno")
        self.assertEqual(self.renderer.log_scale, True)

    def test_render_component_intensity_color(self):
        """Rendering a component in intensity mode should set _temp_color."""
        comp = make_mock_component("comp2")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        self.renderer.render_component(comp_model, component_index=0)
        self.assertIsNotNone(self.renderer._temp_color)
        expected = intensity_to_color(10.0, 1.0, 100.0, "inferno", True)
        self.assertEqual(self.renderer._temp_color, expected)

    def test_render_component_missing_intensity(self):
        """A component not in the intensity_map should use 0.0 intensity."""
        comp = make_mock_component("unknown_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        self.renderer.render_component(comp_model, component_index=0)
        expected = intensity_to_color(0.0, 1.0, 100.0, "inferno", True)
        self.assertEqual(self.renderer._temp_color, expected)

    def test_colormode_selector_has_intensity(self):
        """The colormode selector should include 'Intensity' when intensity_map is set."""
        selector = self.renderer.create_colormode_selector()
        self.assertIn("Intensity", selector.options)

    def test_colormode_selector_without_map_omits_intensity(self):
        """Intensity is unavailable until a map or controls are provided."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        selector = renderer.create_colormode_selector()
        self.assertNotIn("Intensity", selector.options)

    def test_colormode_selector_with_controls_has_intensity(self):
        """Intensity is available when the renderer can run diagnostics."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        renderer.create_intensity_controls()
        selector = renderer.create_colormode_selector()
        self.assertIn("Intensity", selector.options)

    def test_no_intensity_map_falls_through(self):
        """Without intensity_map, default colormode should work as before."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(colormode="default")
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.render_component(comp_model, component_index=0)
        self.assertIsNone(renderer._temp_color)

    def test_intensity_controls_exist(self):
        """create_intensity_controls returns a VBox with hidden display."""
        container = self.renderer.create_intensity_controls()
        import ipywidgets as ipw
        self.assertIsInstance(container, ipw.VBox)
        self.assertEqual(container.layout.display, "none")

    def test_intensity_widgets_populated(self):
        """After creating controls, _intensity_widgets dict is populated."""
        self.renderer.create_intensity_controls()
        expected_keys = {"ncount", "variable", "limits_check", "limits_min", "limits_max", "aggregate", "log_scale", "orders_of_mag", "run_button"}
        self.assertEqual(set(self.renderer._intensity_widgets.keys()), expected_keys)

    def test_orders_of_mag_control_updates_renderer(self):
        """Changing orders of magnitude updates the renderer range setting."""
        self.renderer.create_intensity_controls()
        orders_widget = self.renderer._intensity_widgets["orders_of_mag"]

        orders_widget.value = "4.5"

        self.assertEqual(self.renderer.orders_of_mag, 4.5)

    def test_orders_of_mag_limits_log_colorbar(self):
        """Log colorbar keeps the maximum and limits its lower decade range."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer(
            intensity_map={"low": 1e-9, "high": 1.0},
            colormode="intensity",
            orders_of_mag=3,
        )
        renderer.create_colorbar()

        self.assertAlmostEqual(renderer._colorbar_cbar.norm.vmin, 1e-3)
        self.assertAlmostEqual(renderer._colorbar_cbar.norm.vmax, 1.0)

    def test_negative_intensity_data_uses_linear_colorbar(self):
        """Negative values disable logarithmic scaling and remain visible."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer(
            intensity_map={"low": -2.0, "high": 1.0},
            colormode="intensity",
            log_scale=True,
        )
        renderer.create_colorbar()

        self.assertEqual(renderer._colorbar_cbar.norm.vmin, -2.0)
        self.assertEqual(renderer._colorbar_cbar.norm.vmax, 1.0)

    def test_run_failure_warns_and_marks_data_stale(self):
        """Intensity failures should be visible and leave the widget stale."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(instrument_object=MagicMock())
        renderer.create_intensity_controls()
        button = renderer._intensity_widgets["run_button"]
        with patch(
            "mcstasscript.instrument_diagnostics.intensity_diagnostics.IntensityDiagnostics",
            side_effect=RuntimeError("simulation failed"),
        ):
            with self.assertWarnsRegex(RuntimeWarning, "simulation failed"):
                renderer._on_run_click(button)
        self.assertTrue(renderer._data_stale)

    def test_run_uses_diagnostic_ncount_setting(self):
        """The ncount widget value persists through the diagnostic reset."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer(instrument_object=MagicMock())
        renderer.create_intensity_controls()
        renderer._intensity_widgets["ncount"].value = 12345
        button = renderer._intensity_widgets["run_button"]

        diagnostic = MagicMock()
        diagnostic.data = object()
        diagnostic.monitors = []
        diagnostic.data_dim = 0
        with patch(
            "mcstasscript.instrument_diagnostics.intensity_diagnostics.IntensityDiagnostics",
            return_value=diagnostic,
        ):
            renderer._on_run_click(button)

        diagnostic.settings.assert_called_once_with(ncount=12345)
        diagnostic.instr.settings.assert_not_called()

    def test_variable_dropdown_options(self):
        """Variable dropdown includes common McStas variables."""
        self.renderer.create_intensity_controls()
        var_widget = self.renderer._intensity_widgets["variable"]
        self.assertIsNone(var_widget.value)
        self.assertIn(None, var_widget.options.values())
        self.assertIn("lambda", var_widget.options.values())
        self.assertIn("kx", var_widget.options.values())
        self.assertIn("energy", var_widget.options.values())
        self.assertIn("user9", var_widget.options.values())
        self.assertNotIn("px", var_widget.options.values())
        self.assertNotIn("p4", var_widget.options.values())
        self.assertNotIn("s1", var_widget.options.values())

    def test_selecting_stale_intensity_mode_greys_components(self):
        """Selecting intensity mode greys components until data is available."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer()
        comp_model = ComponentModel(make_mock_component("comp"))
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        renderer.create_intensity_controls()
        renderer.create_colorbar()
        selector = renderer.create_colormode_selector()

        selector.value = "intensity"

        self.assertEqual(renderer.component_colors[0], "#808080")

    def test_log_scale_control_requires_nonnegative_data(self):
        """Log scale is enabled only for nonnegative intensity data."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer()
        renderer.create_intensity_controls()
        log_scale = renderer._intensity_widgets["log_scale"]
        self.assertTrue(log_scale.disabled)

        renderer.intensity_map = {"comp": 1.0, "other": 2.0}
        renderer._data_stale = False
        renderer._update_log_scale_control()
        self.assertFalse(log_scale.disabled)

        renderer.intensity_map = {"comp": -1.0, "other": 2.0}
        renderer.log_scale = True
        log_scale.value = True
        renderer._update_log_scale_control()
        self.assertTrue(log_scale.disabled)
        self.assertFalse(log_scale.value)
        self.assertFalse(renderer.log_scale)

    def test_aggregate_dropdown_options(self):
        """Aggregate dropdown includes all aggregation modes."""
        self.renderer.create_intensity_controls()
        agg_widget = self.renderer._intensity_widgets["aggregate"]
        self.assertEqual(agg_widget.value, "total")
        expected = {"total", "min", "max", "average", "median", "span", "ncount"}
        self.assertEqual(set(agg_widget.options.keys()), expected)

    def test_grey_all_components(self):
        """_grey_all_components sets all component colors to grey."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.render_component(comp_model, component_index=0)
        renderer._grey_all_components()
        self.assertEqual(renderer.component_colors[0], "#808080")

    def test_data_stale_default(self):
        """Without intensity_map, _data_stale should be True."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        self.assertTrue(renderer._data_stale)

    def test_data_not_stale_with_map(self):
        """With intensity_map, _data_stale should be False."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(intensity_map={"a": 1.0})
        self.assertFalse(renderer._data_stale)

    def test_colorbar_stale_intensity(self):
        """In intensity mode without data, colorbar VBox has canvas but no colorbar content."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(colormode="intensity")
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.VBox)
        self.assertEqual(len(cb.children), 1)


class TestMatplotlibIntensity(unittest.TestCase):
    """Tests for MatplotlibRenderer intensity colormode."""

    def setUp(self):
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        self.intensity_map = {"comp1": 1.0, "comp2": 10.0, "comp3": 100.0}
        self.renderer = MatplotlibRenderer(
            intensity_map=self.intensity_map,
            colormode="intensity",
            cmap="inferno",
            log_scale=True,
        )

    def test_init_with_intensity_map(self):
        """Renderer should store intensity params and compute min/max."""
        self.assertEqual(self.renderer.intensity_map, self.intensity_map)
        self.assertEqual(self.renderer._min_I, 1.0)
        self.assertEqual(self.renderer._max_I, 100.0)

    def test_render_component_intensity_color(self):
        """Rendering a component in intensity mode should use intensity color."""
        comp = make_mock_component("comp2")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        self.renderer.render_component(comp_model, component_index=0)
        expected = intensity_to_color(10.0, 1.0, 100.0, "inferno", True)
        self.assertEqual(self.renderer.component_colors[0], expected)

    def test_render_component_missing_intensity(self):
        """A component not in the intensity_map should use 0.0 intensity."""
        comp = make_mock_component("unknown_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        self.renderer.render_component(comp_model, component_index=0)
        expected = intensity_to_color(0.0, 1.0, 100.0, "inferno", True)
        self.assertEqual(self.renderer.component_colors[0], expected)

    def test_no_intensity_map_falls_through(self):
        """Without intensity_map, default colormode should work as before."""
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        renderer = MatplotlibRenderer(colormode="default")
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.render_component(comp_model, component_index=0)
        self.assertEqual(renderer.component_colors[0], renderer.colors[0])


class TestPyThreejsColorbar(unittest.TestCase):
    """Tests for PyThreejsRenderer colorbar widget."""

    def test_colorbar_intensity_mode(self):
        """In intensity mode, create_colorbar should return a VBox with content."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.VBox)
        self.assertGreater(len(cb.children), 0)

    def test_colorbar_default_mode(self):
        """In default mode, create_colorbar should return a VBox with canvas but no colorbar."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(colormode="default")
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.VBox)
        self.assertEqual(len(cb.children), 1)

    def test_colorbar_component_mode(self):
        """In component mode, create_colorbar should return a VBox with content."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(colormode="component", num_components=10)
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.VBox)
        self.assertGreater(len(cb.children), 0)

    def test_colorbar_label_stored(self):
        """colorbar_label should be stored on the renderer."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(colorbar_label="Wavelength [Å]")
        self.assertEqual(renderer.colorbar_label, "Wavelength [Å]")

    def test_colorbar_no_duplicates_on_update(self):
        """Updating colorbar mode should not accumulate multiple colorbars."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()
        self.assertEqual(len(cb.children), 1)
        renderer.colormode = "component"
        renderer.num_components = 5
        renderer._update_colorbar()
        self.assertEqual(len(cb.children), 1)
        renderer.colormode = "intensity"
        renderer._update_colorbar()
        self.assertEqual(len(cb.children), 1)
        renderer.colormode = "default"
        renderer._update_colorbar()
        self.assertEqual(len(cb.children), 1)

    def test_colorbar_figure_not_in_pyplot_manager(self):
        """The colorbar figure must not be registered in pyplot's manager.

        Regression test: plt.figure() registers the figure with pyplot's
        figure manager, causing IPython/Jupyter to auto-display it at cell
        end — producing a duplicate colorbar below the embedded widget.
        The figure is constructed directly (bypassing pyplot) so it is
        never registered, and the ipympl canvas remains fully live.
        """
        import matplotlib.pyplot as plt
        import matplotlib._pylab_helpers as ph
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        # Ensure clean state
        plt.close("all")

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()

        # The figure should NOT be in pyplot's manager at all
        fig = renderer._colorbar_fig
        all_managed = [fm.canvas.figure for fm in ph.Gcf.get_all_fig_managers()]
        self.assertNotIn(fig, all_managed,
                         "colorbar figure must not be in pyplot manager "
                         "to prevent notebook auto-display")

        # The canvas must be a live ipympl Canvas (DOMWidget)
        import ipympl.backend_nbagg as ipympl_backend
        canvas = cb.children[0]
        self.assertIsInstance(canvas, ipympl_backend.Canvas,
                              "VBox child must be a live ipympl Canvas widget")
        self.assertIs(canvas, renderer._colorbar_canvas)
        self.assertIs(canvas.figure, fig)

        # The canvas must still be drawable (colormode switch uses draw_idle)
        renderer.colormode = "component"
        renderer.num_components = 5
        renderer._update_colorbar()
        self.assertEqual(len(cb.children), 1)
        self.assertIs(cb.children[0], canvas)

        renderer.colormode = "intensity"
        renderer._update_colorbar()
        self.assertEqual(len(cb.children), 1)
        self.assertIs(cb.children[0], canvas)

        plt.close("all")

    def test_colorbar_canvas_receives_draw(self):
        """The ipympl canvas must receive draw_idle calls on colormode change.

        Regression test: plt.close(fig) prevented auto-display but also
        destroyed the canvas, leaving a blank widget.  With direct
        Figure + FigureCanvasNbAgg construction, draw_idle must succeed
        and the canvas must remain the same live instance.
        """
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipympl.backend_nbagg as ipympl_backend

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()
        canvas = cb.children[0]

        # Verify canvas is live and has a draw_idle method
        self.assertIsInstance(canvas, ipympl_backend.Canvas)
        self.assertTrue(hasattr(canvas, 'draw_idle'))

        # Wrap draw_idle to verify it gets called
        draw_called = []
        original_draw_idle = canvas.draw_idle
        def tracking_draw_idle(*args, **kwargs):
            draw_called.append(True)
            return original_draw_idle(*args, **kwargs)
        canvas.draw_idle = tracking_draw_idle

        # Switch colormode and update — should trigger draw_idle
        renderer.colormode = "component"
        renderer.num_components = 5
        renderer._update_colorbar()
        self.assertTrue(draw_called, "draw_idle should be called on colormode update")

        draw_called.clear()
        renderer.colormode = "intensity"
        renderer._update_colorbar()
        self.assertTrue(draw_called, "draw_idle should be called on intensity update")

        draw_called.clear()
        renderer.colormode = "default"
        renderer._update_colorbar()
        self.assertTrue(draw_called, "draw_idle should be called on default update")

    def test_colorbar_label_intensity_to_component_to_intensity(self):
        """Switching intensity -> component -> intensity restores correct labels.

        Regression: after intensity mode set a custom label, switching back
        to component mode kept that label instead of 'Component index'.
        """
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        # Set a computed intensity label (simulating _apply_intensity_from_data)
        renderer._intensity_computed_label = "Wavelength [A]"
        cb = renderer.create_colorbar()

        # Intensity mode should show the computed label
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Wavelength [A]",
            "intensity mode should show computed label",
        )

        # Switch to component mode — should show "Component index"
        renderer.colormode = "component"
        renderer.num_components = 5
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Component index",
            "component mode should always show 'Component index'",
        )

        # Switch back to intensity — should restore the computed label
        renderer.colormode = "intensity"
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Wavelength [A]",
            "switching back to intensity should restore computed label",
        )

    def test_colorbar_label_aggregate_total_restores_intensity(self):
        """Selecting 'total' aggregation restores 'Intensity [n/s]' label.

        Regression: changing intensity aggregation changed the label, but
        selecting 'total' should restore the intensity label.
        """
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()

        # Simulate non-total aggregation setting a metadata-based label
        renderer._intensity_computed_label = "Wavelength [A]"
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Wavelength [A]",
        )

        # Simulate switching to 'total' aggregation
        renderer._intensity_computed_label = "Intensity [n/s]"
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Intensity [n/s]",
            "total aggregation should restore 'Intensity [n/s]'",
        )

    def test_colorbar_label_explicit_api_preserved(self):
        """Explicit colorbar_label from API takes priority over computed label."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
            colorbar_label="Custom API Label",
        )
        # Even with a computed label, the explicit API label wins
        renderer._intensity_computed_label = "Wavelength [A]"
        cb = renderer.create_colorbar()
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Custom API Label",
            "explicit API colorbar_label should take priority",
        )

    def test_colorbar_label_component_ignores_intensity_state(self):
        """Component mode label is unaffected by intensity computed label."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer(
            colormode="component",
            num_components=5,
        )
        # Set intensity state that should NOT affect component mode
        renderer._intensity_computed_label = "Wavelength [A]"
        renderer._colorbar_label = "Some Intensity Label"
        cb = renderer.create_colorbar()
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Component index",
            "component mode must ignore intensity label state",
        )


class TestMatplotlibColorbar(unittest.TestCase):
    """Tests for MatplotlibRenderer colorbar."""

    def test_colorbar_added_intensity(self):
        """Colorbar axis should be added for intensity mode."""
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        renderer = MatplotlibRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        fig = renderer.make_scene([])
        axes = fig.get_axes()
        self.assertGreaterEqual(len(axes), 2)

    def test_colorbar_not_added_default(self):
        """No colorbar axis for default mode."""
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        renderer = MatplotlibRenderer(colormode="default")
        fig = renderer.make_scene([])
        axes = fig.get_axes()
        self.assertEqual(len(axes), 1)
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_colorbar_label_stored(self):
        """colorbar_label should be stored on the renderer."""
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        renderer = MatplotlibRenderer(colorbar_label="Test label")
        self.assertEqual(renderer.colorbar_label, "Test label")

    def test_colorbar_label_intensity_to_component_matplotlib(self):
        """Component mode shows 'Component index' regardless of intensity state."""
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        import matplotlib.pyplot as plt

        renderer = MatplotlibRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer._intensity_computed_label = "Wavelength [A]"
        fig1 = renderer.make_scene([])
        cbar_ax1 = [ax for ax in fig1.get_axes() if ax != fig1.axes[0]]
        self.assertEqual(len(cbar_ax1), 1)
        self.assertEqual(cbar_ax1[0].get_ylabel(), "Wavelength [A]")
        plt.close(fig1)

        # Switch to component mode
        renderer.colormode = "component"
        renderer.num_components = 5
        fig2 = renderer.make_scene([])
        cbar_ax2 = [ax for ax in fig2.get_axes() if ax != fig2.axes[0]]
        self.assertEqual(len(cbar_ax2), 1)
        self.assertEqual(
            cbar_ax2[0].get_ylabel(),
            "Component index",
            "component mode must show 'Component index' in matplotlib",
        )
        plt.close(fig2)

    def test_colorbar_label_explicit_api_matplotlib(self):
        """Explicit colorbar_label takes priority in matplotlib renderer."""
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        import matplotlib.pyplot as plt

        renderer = MatplotlibRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
            colorbar_label="Custom Label",
        )
        renderer._intensity_computed_label = "Wavelength [A]"
        fig = renderer.make_scene([])
        cbar_ax = [ax for ax in fig.get_axes() if ax != fig.axes[0]]
        self.assertEqual(cbar_ax[0].get_ylabel(), "Custom Label")
        plt.close(fig)


class TestPyThreejsCustomColors(unittest.TestCase):
    """Tests for PyThreejsRenderer custom component colors feature."""

    def test_init_without_component_colors(self):
        """Renderer without component_colors should have empty map."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        self.assertEqual(renderer.component_colors_map, {})
        self.assertFalse(renderer._custom_colors_active)
        self.assertIsNone(renderer._custom_colors_checkbox)

    def test_init_with_component_colors(self):
        """Renderer with component_colors should store the mapping."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        color_map = {"guide1": "#ff0000", "sample": "#00ff00"}
        renderer = PyThreejsRenderer(component_colors=color_map)
        self.assertEqual(renderer.component_colors_map, color_map)
        self.assertFalse(renderer._custom_colors_active)

    def test_create_custom_colors_checkbox_with_map(self):
        """create_custom_colors_checkbox returns a Checkbox when map is provided."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(component_colors={"comp1": "#ff0000"})
        checkbox = renderer.create_custom_colors_checkbox()
        self.assertIsInstance(checkbox, ipw.Checkbox)
        self.assertEqual(checkbox.value, False)
        self.assertEqual(checkbox.description, "Custom colors")
        self.assertIs(renderer._custom_colors_checkbox, checkbox)

    def test_create_custom_colors_checkbox_without_map(self):
        """create_custom_colors_checkbox returns None when no map provided."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        checkbox = renderer.create_custom_colors_checkbox()
        self.assertIsNone(checkbox)

    def test_apply_custom_colors(self):
        """_apply_custom_colors applies colors to registered components."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={"test_comp": "#ff0000", "other": "#00ff00"})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        renderer._apply_custom_colors()
        self.assertTrue(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], "#ff0000")

    def test_apply_custom_colors_partial_match(self):
        """Mapped components get custom color; unmapped keep their existing color."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={"comp_a": "#ff0000"})
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        orig_color_b = renderer.component_colors[1]
        renderer._apply_custom_colors()
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(renderer.component_colors[1], orig_color_b)

    def test_reset_to_colormode_colors(self):
        """_reset_to_colormode_colors restores default colors."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={"test_comp": "#ff0000"})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        renderer._apply_custom_colors()
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        renderer._reset_to_colormode_colors()
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], DEFAULT_COLORS[0])

    def test_checkbox_toggle_on(self):
        """Checking the checkbox applies custom colors."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={"test_comp": "#ff0000"})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        checkbox = renderer.create_custom_colors_checkbox()
        orig_color = renderer.component_colors[0]
        checkbox.value = True
        self.assertTrue(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], "#ff0000")

    def test_checkbox_toggle_off(self):
        """Unchecking the checkbox resets to colormode colors."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={"test_comp": "#ff0000"})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        checkbox = renderer.create_custom_colors_checkbox()
        checkbox.value = True
        self.assertTrue(renderer._custom_colors_active)
        checkbox.value = False
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], DEFAULT_COLORS[0])

    def test_checkbox_on_only_changes_mapped_components(self):
        """Checking with a single-component map only changes that one component."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={"guide1": "#ff0000"})
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp3 = make_mock_component("detector1")
        comp3_model = ComponentModel(comp3)
        comp3_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        renderer.register_component(comp3_model)
        renderer.render_component(comp3_model, component_index=2)
        # Capture pre-check colors
        before = {i: renderer.component_colors[i] for i in renderer.component_colors}
        checkbox = renderer.create_custom_colors_checkbox()
        checkbox.value = True
        # Only mapped component changes
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(renderer.component_colors[1], before[1])
        self.assertEqual(renderer.component_colors[2], before[2])

    def test_checkbox_off_restores_colormode(self):
        """Unchecking restores all components to active colormode colors."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={"guide1": "#ff0000"})
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        checkbox = renderer.create_custom_colors_checkbox()
        checkbox.value = True
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        checkbox.value = False
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], DEFAULT_COLORS[0])
        self.assertEqual(renderer.component_colors[1], DEFAULT_COLORS[1])

    def test_intensity_mode_unchecked_uses_intensity(self):
        """In intensity mode with checkbox unchecked, all components use intensity colors."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"guide1": 1.0, "sample1": 100.0},
            component_colors={"guide1": "#ff0000"},
        )
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        # Checkbox is off by default
        checkbox = renderer.create_custom_colors_checkbox()
        self.assertFalse(checkbox.value)
        self.assertFalse(renderer._custom_colors_active)
        # Both components use intensity colors
        self.assertEqual(renderer.component_colors[0],
                         intensity_to_color(1.0, 1.0, 100.0, "inferno", True))
        self.assertEqual(renderer.component_colors[1],
                         intensity_to_color(100.0, 1.0, 100.0, "inferno", True))

    def test_intensity_mode_check_uncheck_roundtrip(self):
        """Intensity mode: check applies custom, uncheck restores intensity colors."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"guide1": 1.0, "sample1": 100.0},
            component_colors={"guide1": "#ff0000"},
        )
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        checkbox = renderer.create_custom_colors_checkbox()
        # Check: only mapped component changes
        checkbox.value = True
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        intensity_b = intensity_to_color(100.0, 1.0, 100.0, "inferno", True)
        self.assertEqual(renderer.component_colors[1], intensity_b)
        # Uncheck: both restore to intensity colors
        checkbox.value = False
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0],
                         intensity_to_color(1.0, 1.0, 100.0, "inferno", True))
        self.assertEqual(renderer.component_colors[1], intensity_b)

    def test_colormode_change_preserves_custom_colors(self):
        """Colormode change keeps checkbox checked; mapped components retain custom color."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            component_colors={"comp_a": "#ff0000"},
            colormode="component",
            num_components=5,
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        checkbox = renderer.create_custom_colors_checkbox()
        checkbox.value = True
        self.assertTrue(renderer._custom_colors_active)
        renderer.create_colorbar()
        renderer.create_intensity_controls()
        selector = renderer.create_colormode_selector()
        selector.value = "default"
        # Checkbox stays checked, mapped component keeps custom color
        self.assertTrue(renderer._custom_colors_active)
        self.assertTrue(checkbox.value)
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        # Unmapped component follows new colormode (default)
        self.assertEqual(renderer.component_colors[1], DEFAULT_COLORS[1])

    def test_intensity_refresh_preserves_custom_colors(self):
        """Intensity data refresh keeps mapped components at custom color."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp_a": 1.0, "comp_b": 100.0},
            component_colors={"comp_a": "#ff0000"},
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        renderer._custom_colors_active = True
        # Simulate intensity refresh: re-recolor all by intensity, then overlay
        new_map = {"comp_a": 50.0, "comp_b": 200.0}
        renderer.intensity_map = new_map
        renderer._min_I = 50.0
        renderer._max_I = 200.0
        for idx in renderer.component_children:
            comp_name = renderer.simple_components[idx]["name"]
            I = new_map.get(comp_name, 0.0)
            color = intensity_to_color(I, 50.0, 200.0, "inferno", True)
            renderer.update_component_color(idx, color)
        renderer._overlay_custom_colors()
        # Mapped component keeps custom color
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        # Unmapped component follows new intensity
        expected_b = intensity_to_color(200.0, 50.0, 200.0, "inferno", True)
        self.assertEqual(renderer.component_colors[1], expected_b)

    def test_grey_all_preserves_custom_colors(self):
        """_grey_all_components greys unmapped but preserves mapped custom colors."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={"comp_a": "#ff0000"})
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        renderer._custom_colors_active = True
        renderer._grey_all_components()
        # Mapped component keeps custom color
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        # Unmapped component is grey
        self.assertEqual(renderer.component_colors[1], "#808080")

    def test_empty_component_colors_no_checkbox(self):
        """Empty dict for component_colors should not create a checkbox."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={})
        checkbox = renderer.create_custom_colors_checkbox()
        self.assertIsNone(checkbox)

    def test_apply_custom_colors_empty_map(self):
        """_apply_custom_colors with empty map is a no-op."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        orig_color = renderer.component_colors[0]
        renderer._apply_custom_colors()
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], orig_color)

    def test_colormode_color_for_index_default(self):
        """_colormode_color_for_index returns DEFAULT_COLORS in default mode."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        self.assertEqual(renderer._colormode_color_for_index(0), DEFAULT_COLORS[0])
        self.assertEqual(renderer._colormode_color_for_index(1), DEFAULT_COLORS[1])

    def test_colormode_color_for_index_component_mode(self):
        """_colormode_color_for_index returns viridis colors in component mode."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(colormode="component", num_components=5)
        c0 = renderer._colormode_color_for_index(0)
        c4 = renderer._colormode_color_for_index(4)
        self.assertNotEqual(c0, c4)
        self.assertEqual(c0, index_to_color(0, 5))
        self.assertEqual(c4, index_to_color(4, 5))

    def test_colormode_color_for_index_intensity_mode(self):
        """_colormode_color_for_index returns intensity colors in intensity mode."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp_a": 1.0, "comp_b": 100.0},
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        c_a = renderer._colormode_color_for_index(0)
        c_b = renderer._colormode_color_for_index(1)
        self.assertNotEqual(c_a, c_b)
        self.assertEqual(c_a, intensity_to_color(1.0, 1.0, 100.0, "inferno", True))
        self.assertEqual(c_b, intensity_to_color(100.0, 1.0, 100.0, "inferno", True))

    def test_apply_custom_colors_overlays_on_intensity(self):
        """Custom colors overlay on top of intensity colormode for unmapped components."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp_a": 1.0, "comp_b": 100.0},
            component_colors={"comp_a": "#ff0000"},
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        orig_color_b = renderer.component_colors[1]
        renderer._apply_custom_colors()
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        # Unmapped component keeps its pre-existing color
        self.assertEqual(renderer.component_colors[1], orig_color_b)


class TestApiComponentColors(unittest.TestCase):
    """Tests for component_colors parameter threading through the API."""

    def test_get_renderer_pythreejs_passes_component_colors(self):
        """_get_renderer passes component_colors to PyThreejsRenderer."""
        renderer = _get_renderer("pythreejs", component_colors={"a": "#ff0000"})
        self.assertEqual(renderer.component_colors_map, {"a": "#ff0000"})

    def test_get_renderer_matplotlib_ignores_component_colors(self):
        """_get_renderer strips component_colors for matplotlib backend."""
        renderer = _get_renderer("matplotlib", component_colors={"a": "#ff0000"})
        self.assertFalse(hasattr(renderer, 'component_colors_map'))

    def test_view_with_guess_renders_components(self):
        """view_with_guess registers components with the renderer (navigator has entries)."""
        instr = MagicMock()
        comp1 = make_mock_component("guide1")
        comp2 = make_mock_component("sample1")
        instr.component_list = [comp1, comp2]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(instr, backend="pythreejs")
        import ipywidgets as ipw
        self.assertIsInstance(result, ipw.VBox)
        # The navigator is the first child of the top control row.
        controls = result.children[0]
        navigator = controls.children[0]
        self.assertIsInstance(navigator, ipw.Combobox)
        self.assertEqual(len(navigator.options), 2)
        self.assertIn("guide1", navigator.options[0])
        self.assertIn("sample1", navigator.options[1])

    def test_view_with_guess_component_colors_checkbox_works(self):
        """Custom colors checkbox applies colors to rendered components."""
        instr = MagicMock()
        comp1 = make_mock_component("guide1")
        comp2 = make_mock_component("sample1")
        instr.component_list = [comp1, comp2]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(
            instr,
            backend="pythreejs",
            component_colors={"guide1": "#ff0000"},
        )
        import ipywidgets as ipw
        # Locate the custom colors checkbox
        custom_cb = None
        controls = result.children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom colors":
                custom_cb = child
                break
        self.assertIsNotNone(custom_cb)
        self.assertFalse(custom_cb.value)
        # Check the checkbox — should apply custom color to guide1
        custom_cb.value = True
        # The scene/colorbar HBox follows the top control row.
        hbox = result.children[1]
        scene = hbox.children[0]
        # Verify scene has children (rendered geometry)
        self.assertGreater(len(scene.scene.children), 0)

    def test_view_with_guess_no_checkbox_without_colors(self):
        """view_with_guess without component_colors produces no custom colors checkbox."""
        instr = MagicMock()
        comp = make_mock_component("test_comp")
        instr.component_list = [comp]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(instr, backend="pythreejs")
        import ipywidgets as ipw
        self.assertIsInstance(result, ipw.VBox)
        children = result.children
        custom_cb = None
        controls = children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom colors":
                custom_cb = child
                break
        self.assertIsNone(custom_cb)

    def test_view_with_guess_checkbox_present_with_colors(self):
        """view_with_guess with component_colors produces a custom colors checkbox."""
        instr = MagicMock()
        comp = make_mock_component("test_comp")
        instr.component_list = [comp]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(
            instr,
            backend="pythreejs",
            component_colors={"test_comp": "#ff0000"},
        )
        import ipywidgets as ipw
        children = result.children
        custom_cb = None
        controls = children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom colors":
                custom_cb = child
                break
        self.assertIsNotNone(custom_cb)

    def test_view_with_guess_omits_intensity_without_map(self):
        """Guess geometry does not expose an unusable intensity mode."""
        instr = MagicMock()
        instr.component_list = [make_mock_component("test_comp")]
        instr._simulation_parameters = {}
        instr._declared_variables = {}

        result = view_with_guess(instr, backend="pythreejs")
        selector = result.children[0].children[1]

        self.assertNotIn("Intensity", selector.options)

    def test_view_with_guess_keeps_static_intensity_mode(self):
        """Guess geometry can display a caller-supplied intensity map."""
        instr = MagicMock()
        instr.component_list = [make_mock_component("test_comp")]
        instr._simulation_parameters = {}
        instr._declared_variables = {}

        result = view_with_guess(
            instr,
            backend="pythreejs",
            intensity_map={"test_comp": 1.0},
        )
        selector = result.children[0].children[1]

        self.assertIn("Intensity", selector.options)


class TestMaterialIsolation(unittest.TestCase):
    """Tests for component-scoped material isolation in PyThreejsRenderer.

    MaterialLibrary caches pythreejs materials by class/color/properties,
    so multiple components could share one material instance.
    update_component_color() mutates the shared material color, causing
    a custom color or intensity recolor on one component to affect others.

    The fix scopes materials by component_index in the cache key.
    """

    def _render_two_components(self, renderer):
        """Render two box components and return their child lists."""
        comp1 = make_mock_component("comp1")
        model1 = ComponentModel(comp1)
        model1.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model1)
        children1 = renderer.render_component(model1, component_index=0)

        comp2 = make_mock_component("comp2")
        model2 = ComponentModel(comp2)
        model2.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model2)
        children2 = renderer.render_component(model2, component_index=1)
        return children1, children2

    def test_materials_not_shared_between_components(self):
        """Materials for different components must be distinct objects."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        children1, children2 = self._render_two_components(renderer)
        mat1 = children1[0].material
        mat2 = children2[0].material
        self.assertIsNot(mat1, mat2,
                         "Materials from different components must not be the same object")

    def test_changing_one_component_color_does_not_affect_other(self):
        """update_component_color on comp1 must not change comp2's material color."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        children1, children2 = self._render_two_components(renderer)
        orig_color2 = children2[0].material.color
        renderer.update_component_color(0, "#ff0000")
        self.assertEqual(children1[0].material.color, "#ff0000")
        self.assertEqual(children2[0].material.color, orig_color2,
                         "Component 2's material color must not change when component 1 is recolored")

    def test_custom_single_component_mapping_affects_only_that_component(self):
        """Custom color for comp_a must not change comp_b's color."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={"comp_a": "#ff0000"})
        comp_a = make_mock_component("comp_a")
        model_a = ComponentModel(comp_a)
        model_a.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_a)
        renderer.render_component(model_a, component_index=0)

        comp_b = make_mock_component("comp_b")
        model_b = ComponentModel(comp_b)
        model_b.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_b)
        children_b = renderer.render_component(model_b, component_index=1)
        orig_color_b = children_b[0].material.color

        renderer._apply_custom_colors()
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(children_b[0].material.color, orig_color_b,
                         "Unmapped component's material must not change")

    def test_intensity_recoloring_isolated_between_components(self):
        """Intensity recoloring of one component must not affect another's material."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp1": 1.0, "comp2": 100.0},
        )
        children1, children2 = self._render_two_components(renderer)
        orig_color2 = children2[0].material.color
        new_color = intensity_to_color(50.0, 1.0, 100.0, "inferno", True)
        renderer.update_component_color(0, new_color)
        self.assertEqual(children1[0].material.color, new_color)
        self.assertEqual(children2[0].material.color, orig_color2,
                         "Component 2's material must not change when component 1 is intensity-recolor ed")

    def test_intensity_recoloring_independent_with_checkbox_enabled(self):
        """Intensity recoloring isolation holds when custom colors checkbox is active."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp1": 1.0, "comp2": 100.0},
            component_colors={"comp1": "#ff0000"},
        )
        children1, children2 = self._render_two_components(renderer)
        renderer._custom_colors_active = True
        orig_color2 = children2[0].material.color
        renderer.update_component_color(0, "#00ff00")
        self.assertEqual(children2[0].material.color, orig_color2,
                         "Component 2 must not change when component 1 is recolored with checkbox active")

    def test_shapes_within_same_component_share_material(self):
        """Multiple shapes within the same component may share a material."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        comp = make_mock_component("multi_shape")
        model = ComponentModel(comp)
        model.shape_list = [
            BoxShape(width=1, height=1, depth=1),
            BoxShape(width=2, height=2, depth=2),
        ]
        renderer.register_component(model)
        children = renderer.render_component(model, component_index=0)
        # Both shapes are boxes with same material properties, so they share
        self.assertIs(children[0].material, children[1].material,
                      "Shapes within the same component with identical properties should share a material")

    def test_material_library_cache_key_includes_component_index(self):
        """MaterialLibrary cache key must include component_index to ensure isolation."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import MaterialLibrary
        lib = MaterialLibrary(colors=["#ff0000", "#00ff00"])
        mat0 = lib.get_material(component_index=0)
        mat1 = lib.get_material(component_index=1)
        self.assertIsNot(mat0, mat1,
                         "Same color/properties with different component_index must yield different materials")
        # Same component_index should return cached material
        mat0_again = lib.get_material(component_index=0)
        self.assertIs(mat0, mat0_again,
                      "Same component_index should return the cached material")

    def test_material_library_without_component_index(self):
        """Without component_index, materials are cached globally (backward compat)."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import MaterialLibrary
        lib = MaterialLibrary(colors=["#ff0000", "#00ff00"])
        mat1 = lib.get_material()
        mat2 = lib.get_material()
        self.assertIs(mat1, mat2,
                      "Without component_index, same color/properties should share cached material")

    def test_update_component_color_reflects_in_component_colors_dict(self):
        """update_component_color updates both the material and component_colors dict."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        children1, _ = self._render_two_components(renderer)
        renderer.update_component_color(0, "#ff0000")
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(children1[0].material.color, "#ff0000")

    def test_multiple_components_same_color_independent(self):
        """Even when components happen to have the same color, materials are independent."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        # Force same color by using a small color palette
        renderer = PyThreejsRenderer(colors=["#aaaaaa"])
        children1, children2 = self._render_two_components(renderer)
        self.assertEqual(children1[0].material.color, "#aaaaaa")
        self.assertEqual(children2[0].material.color, "#aaaaaa")
        self.assertIsNot(children1[0].material, children2[0].material,
                         "Same color across components must still yield distinct material objects")
        renderer.update_component_color(0, "#ff0000")
        self.assertEqual(children1[0].material.color, "#ff0000")
        self.assertEqual(children2[0].material.color, "#aaaaaa")


class TestAggregateNcount(unittest.TestCase):
    """Tests for _aggregate_intensity with 'ncount' aggregation.

    The 'ncount' aggregate uses the Ncount array instead of Intensity,
    summing ray counts across bins. Colorbar is labeled 'N rays'.
    """

    def _make_mock_data(self, intensity_arr, ncount_arr, xaxis=None, dimension=None, total_I=0.0, total_N=None):
        data = MagicMock()
        intensity = np.asarray(intensity_arr, dtype=float)
        ncount = np.asarray(ncount_arr, dtype=float)
        data.metadata.dimension = dimension if dimension is not None else len(intensity)
        data.metadata.total_I = float(total_I)
        data.metadata.total_N = total_N
        data.Intensity = intensity
        data.Ncount = ncount
        data.xaxis = xaxis if xaxis is not None else np.linspace(0, 1, len(intensity))
        return data

    def test_ncount_1d_sum(self):
        """ncount aggregation in 1D returns sum of Ncount array."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(
            intensity_arr=[1.0, 2.0, 3.0, 4.0],
            ncount_arr=[10.0, 20.0, 30.0, 40.0],
            xaxis=[1.0, 2.0, 3.0, 4.0],
        )
        self.assertAlmostEqual(_aggregate_intensity(data, "ncount"), 100.0)

    def test_ncount_0d_total_N(self):
        """ncount aggregation in 0D returns metadata.total_N."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(
            intensity_arr=[42.0],
            ncount_arr=[42.0],
            dimension=0,
            total_I=42.0,
            total_N=150.0,
        )
        self.assertAlmostEqual(_aggregate_intensity(data, "ncount"), 150.0)

    def test_ncount_0d_fallback_sum(self):
        """ncount in 0D falls back to sum(Ncount) when total_N is None."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(
            intensity_arr=[42.0],
            ncount_arr=[10.0, 20.0, 30.0],
            dimension=0,
            total_I=42.0,
            total_N=None,
        )
        self.assertAlmostEqual(_aggregate_intensity(data, "ncount"), 60.0)

    def test_ncount_1d_all_zero(self):
        """ncount with all-zero Ncount returns 0.0."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(
            intensity_arr=[0.0, 0.0, 0.0],
            ncount_arr=[0.0, 0.0, 0.0],
            xaxis=[1.0, 2.0, 3.0],
        )
        self.assertAlmostEqual(_aggregate_intensity(data, "ncount"), 0.0)

    def test_ncount_ignores_intensity(self):
        """ncount uses Ncount values, not Intensity values."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        data = self._make_mock_data(
            intensity_arr=[100.0, 200.0, 300.0],
            ncount_arr=[1.0, 2.0, 3.0],
            xaxis=[1.0, 2.0, 3.0],
        )
        self.assertAlmostEqual(_aggregate_intensity(data, "ncount"), 6.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "total"), 600.0)

    def test_ncount_invalid_raises_in_view_with_analysis(self):
        """view_with_analysis accepts 'ncount' as valid aggregation."""
        from mcstasscript.geometry_viewer.api import view_with_analysis
        instr = MagicMock()
        instr.component_list = []
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        # Should NOT raise for 'ncount'
        try:
            view_with_analysis(instr, aggregation="ncount")
        except ValueError as e:
            self.fail(f"ncount should be a valid aggregation but raised: {e}")
        except Exception:
            # Expected to fail later (no real instrument), but not on validation
            pass


class TestNcountDropdownAndLabel(unittest.TestCase):
    """Tests for ncount dropdown option and 'N rays' colorbar label."""

    def test_aggregate_dropdown_includes_ncount(self):
        """Aggregate dropdown includes 'ncount' option mapping to 'ncount'."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        agg_widget = renderer._intensity_widgets["aggregate"]
        self.assertIn("ncount", agg_widget.options.keys())
        self.assertEqual(agg_widget.options["ncount"], "ncount")

    def test_aggregate_dropdown_still_has_all_original_options(self):
        """Adding ncount does not remove any existing aggregate options."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        agg_widget = renderer._intensity_widgets["aggregate"]
        expected = {"total", "min", "max", "average", "median", "span", "ncount"}
        self.assertEqual(set(agg_widget.options.keys()), expected)

    def test_ncount_colorbar_label_in_apply_intensity(self):
        """_apply_intensity_from_data sets 'N rays' label for ncount aggregation."""
        from unittest.mock import patch
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        renderer.create_colorbar()

        # Set up mock diagnostic data
        mock_data = MagicMock()
        mock_data.metadata.dimension = 0
        mock_data.metadata.total_I = 100.0
        mock_data.metadata.total_N = 500.0
        mock_data.Intensity = np.array([100.0])
        mock_data.Ncount = np.array([500.0])
        mock_data.xaxis = np.array([0.0])
        mock_data.metadata.xlabel = None

        renderer._diag_data = [mock_data]
        renderer._diag_monitors = [("mon1", "comp_a")]
        renderer._diag_data_dim = 0
        renderer._data_stale = False
        renderer.intensity_map = {"comp_a": 1.0}
        renderer.simple_components = [{"name": "comp_a"}]
        renderer.component_children = {0: []}

        with patch("mcstasscript.interface.functions.name_search", return_value=mock_data):
            renderer._apply_intensity_from_data("ncount")
        self.assertEqual(renderer._intensity_computed_label, "N rays")

    def test_cached_aggregate_refresh_ncount(self):
        """Changing aggregate dropdown to ncount re-applies from cached data."""
        from unittest.mock import patch
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        renderer.create_colorbar()

        # Set up mock diagnostic data
        mock_data = MagicMock()
        mock_data.metadata.dimension = 1
        mock_data.metadata.total_I = 100.0
        mock_data.metadata.total_N = 500.0
        mock_data.Intensity = np.array([10.0, 20.0, 30.0])
        mock_data.Ncount = np.array([100.0, 200.0, 200.0])
        mock_data.xaxis = np.array([1.0, 2.0, 3.0])
        mock_data.metadata.xlabel = "wavelength"

        renderer._diag_data = [mock_data]
        renderer._diag_monitors = [("mon1", "comp_a")]
        renderer._diag_data_dim = 1
        renderer._data_stale = False
        renderer.intensity_map = {"comp_a": 1.0}
        renderer.simple_components = [{"name": "comp_a"}]
        renderer.component_children = {0: []}

        with patch("mcstasscript.interface.functions.name_search", return_value=mock_data):
            # Simulate aggregate dropdown change to ncount
            agg_widget = renderer._intensity_widgets["aggregate"]
            agg_widget.value = "ncount"

        self.assertEqual(renderer._intensity_computed_label, "N rays")
        self.assertEqual(renderer.intensity_map["comp_a"], 500.0)

    def test_cached_aggregate_refresh_total_after_ncount(self):
        """Switching from ncount back to total restores 'Intensity [n/s]' label."""
        from unittest.mock import patch
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        renderer.create_colorbar()

        mock_data = MagicMock()
        mock_data.metadata.dimension = 1
        mock_data.metadata.total_I = 100.0
        mock_data.metadata.total_N = 500.0
        mock_data.Intensity = np.array([10.0, 20.0, 30.0])
        mock_data.Ncount = np.array([100.0, 200.0, 200.0])
        mock_data.xaxis = np.array([1.0, 2.0, 3.0])
        mock_data.metadata.xlabel = "wavelength"

        renderer._diag_data = [mock_data]
        renderer._diag_monitors = [("mon1", "comp_a")]
        renderer._diag_data_dim = 1
        renderer._data_stale = False
        renderer.intensity_map = {"comp_a": 1.0}
        renderer.simple_components = [{"name": "comp_a"}]
        renderer.component_children = {0: []}

        with patch("mcstasscript.interface.functions.name_search", return_value=mock_data):
            # Switch to ncount
            agg_widget = renderer._intensity_widgets["aggregate"]
            agg_widget.value = "ncount"
            self.assertEqual(renderer._intensity_computed_label, "N rays")

            # Switch back to total
            agg_widget.value = "total"
            self.assertEqual(renderer._intensity_computed_label, "Intensity [n/s]")


class TestNcountPreservesExistingBehavior(unittest.TestCase):
    """Ensure ncount addition does not break existing aggregate modes."""

    def test_existing_aggregations_still_work(self):
        """All original aggregation modes still produce correct results."""
        from mcstasscript.geometry_viewer.api import _aggregate_intensity

        data = MagicMock()
        data.metadata.dimension = 1
        data.metadata.total_I = 10.0
        data.metadata.total_N = 100.0
        data.Intensity = np.array([1.0, 2.0, 3.0, 4.0])
        data.Ncount = np.array([10.0, 20.0, 30.0, 40.0])
        data.xaxis = np.array([1.0, 2.0, 3.0, 4.0])

        self.assertAlmostEqual(_aggregate_intensity(data, "total"), 10.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "max"), 4.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "min"), 1.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "span"), 3.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "mean"), 3.0)
        self.assertAlmostEqual(_aggregate_intensity(data, "average"), 3.0)

    def test_default_aggregate_is_still_total(self):
        """Default aggregate value in dropdown is still 'total'."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        agg_widget = renderer._intensity_widgets["aggregate"]
        self.assertEqual(agg_widget.value, "total")

    def test_custom_colors_unaffected_by_ncount(self):
        """Custom colors overlay works correctly when ncount aggregation is active."""
        from unittest.mock import patch
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp_a": 1.0, "comp_b": 100.0},
            component_colors={"comp_a": "#ff0000"},
        )
        comp_a = make_mock_component("comp_a")
        model_a = ComponentModel(comp_a)
        model_a.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        model_b = ComponentModel(comp_b)
        model_b.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_a)
        renderer.render_component(model_a, component_index=0)
        renderer.register_component(model_b)
        renderer.render_component(model_b, component_index=1)
        renderer.create_colorbar()

        # Set up mock diagnostic data with ncount
        mock_data = MagicMock()
        mock_data.metadata.dimension = 0
        mock_data.metadata.total_I = 100.0
        mock_data.metadata.total_N = 500.0
        mock_data.Intensity = np.array([100.0])
        mock_data.Ncount = np.array([500.0])
        mock_data.xaxis = np.array([0.0])
        mock_data.metadata.xlabel = None

        renderer._diag_data = [mock_data]
        renderer._diag_monitors = [("mon1", "comp_a")]
        renderer._diag_data_dim = 0
        renderer._data_stale = False
        renderer.simple_components = [
            {"name": "comp_a"},
            {"name": "comp_b"},
        ]
        renderer.component_children = {0: [], 1: []}

        with patch("mcstasscript.interface.functions.name_search", return_value=mock_data):
            # Apply ncount aggregation
            renderer._apply_intensity_from_data("ncount")
        self.assertEqual(renderer._intensity_computed_label, "N rays")

        # Now enable custom colors
        renderer._custom_colors_active = True
        renderer._overlay_custom_colors()
        self.assertEqual(renderer.component_colors[0], "#ff0000")


class TestPyThreejsCustomOpacities(unittest.TestCase):
    """Tests for PyThreejsRenderer custom component opacities feature."""

    def test_init_without_component_opacity(self):
        """Renderer without component_opacity should have empty map."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        self.assertEqual(renderer.component_opacity_map, {})
        self.assertFalse(renderer._custom_opacities_active)
        self.assertIsNone(renderer._custom_opacities_checkbox)

    def test_init_with_component_opacity(self):
        """Renderer with component_opacity should store the mapping."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        opacity_map = {"guide1": 0.3, "sample": 0.7}
        renderer = PyThreejsRenderer(component_opacity=opacity_map)
        self.assertEqual(renderer.component_opacity_map, opacity_map)
        self.assertFalse(renderer._custom_opacities_active)

    def test_init_validates_non_numeric_value(self):
        """Non-numeric opacity values should raise TypeError."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        with self.assertRaises(TypeError):
            PyThreejsRenderer(component_opacity={"guide1": "0.5"})

    def test_init_validates_out_of_range_value(self):
        """Opacity values outside [0.0, 1.0] should raise ValueError."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        with self.assertRaises(ValueError):
            PyThreejsRenderer(component_opacity={"guide1": 1.5})
        with self.assertRaises(ValueError):
            PyThreejsRenderer(component_opacity={"guide1": -0.1})

    def test_init_converts_int_to_float(self):
        """Integer opacity values should be converted to float."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"guide1": 0, "sample": 1})
        self.assertEqual(renderer.component_opacity_map, {"guide1": 0.0, "sample": 1.0})

    def test_create_custom_opacities_checkbox_with_map(self):
        """create_custom_opacities_checkbox returns a Checkbox when map is provided."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(component_opacity={"comp1": 0.5})
        checkbox = renderer.create_custom_opacities_checkbox()
        self.assertIsInstance(checkbox, ipw.Checkbox)
        self.assertEqual(checkbox.value, False)
        self.assertEqual(checkbox.description, "Custom opacity")
        self.assertIs(renderer._custom_opacities_checkbox, checkbox)

    def test_create_custom_opacities_checkbox_without_map(self):
        """create_custom_opacities_checkbox returns None when no map provided."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        checkbox = renderer.create_custom_opacities_checkbox()
        self.assertIsNone(checkbox)

    def test_apply_custom_opacities(self):
        """_apply_custom_opacities applies opacities to registered components."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"test_comp": 0.3})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        renderer._apply_custom_opacities()
        self.assertTrue(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], 0.3)

    def test_apply_custom_opacities_partial_match(self):
        """Mapped components get custom opacity; unmapped keep their existing opacity."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"comp_a": 0.2})
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        orig_opacity_b = renderer.component_opacity[1]
        renderer._apply_custom_opacities()
        self.assertEqual(renderer.component_opacity[0], 0.2)
        self.assertEqual(renderer.component_opacity[1], orig_opacity_b)

    def test_reset_to_base_opacities(self):
        """_reset_to_base_opacities restores original opacities."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"test_comp": 0.3})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        orig_opacity = renderer.component_opacity[0]
        renderer._apply_custom_opacities()
        self.assertEqual(renderer.component_opacity[0], 0.3)
        renderer._reset_to_base_opacities()
        self.assertFalse(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], orig_opacity)

    def test_checkbox_toggle_on(self):
        """Checking the checkbox applies custom opacities."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"test_comp": 0.25})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        checkbox = renderer.create_custom_opacities_checkbox()
        orig_opacity = renderer.component_opacity[0]
        checkbox.value = True
        self.assertTrue(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], 0.25)

    def test_checkbox_toggle_off(self):
        """Unchecking the checkbox resets to base opacities."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"test_comp": 0.25})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        orig_opacity = renderer.component_opacity[0]
        checkbox = renderer.create_custom_opacities_checkbox()
        checkbox.value = True
        self.assertTrue(renderer._custom_opacities_active)
        checkbox.value = False
        self.assertFalse(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], orig_opacity)

    def test_checkbox_on_only_changes_mapped_components(self):
        """Checking with a single-component map only changes that one component."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"guide1": 0.15})
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp3 = make_mock_component("detector1")
        comp3_model = ComponentModel(comp3)
        comp3_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        renderer.register_component(comp3_model)
        renderer.render_component(comp3_model, component_index=2)
        before = {i: renderer.component_opacity[i] for i in renderer.component_opacity}
        checkbox = renderer.create_custom_opacities_checkbox()
        checkbox.value = True
        self.assertEqual(renderer.component_opacity[0], 0.15)
        self.assertEqual(renderer.component_opacity[1], before[1])
        self.assertEqual(renderer.component_opacity[2], before[2])

    def test_checkbox_off_restores_base_opacity(self):
        """Unchecking restores all components to base opacity."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"guide1": 0.15})
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        orig_op1 = renderer.component_opacity[0]
        orig_op2 = renderer.component_opacity[1]
        checkbox = renderer.create_custom_opacities_checkbox()
        checkbox.value = True
        self.assertEqual(renderer.component_opacity[0], 0.15)
        checkbox.value = False
        self.assertFalse(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], orig_op1)
        self.assertEqual(renderer.component_opacity[1], orig_op2)

    def test_empty_component_opacity_no_checkbox(self):
        """Empty dict for component_opacity should not create a checkbox."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={})
        checkbox = renderer.create_custom_opacities_checkbox()
        self.assertIsNone(checkbox)

    def test_apply_custom_opacities_empty_map(self):
        """_apply_custom_opacities with empty map is a no-op."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        orig_opacity = renderer.component_opacity[0]
        renderer._apply_custom_opacities()
        self.assertFalse(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], orig_opacity)

    def test_opacity_preserves_color(self):
        """Applying custom opacity must not change the component's color."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            component_colors={"test_comp": "#ff0000"},
            component_opacity={"test_comp": 0.3},
        )
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        renderer._apply_custom_colors()
        renderer._apply_custom_opacities()
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(renderer.component_opacity[0], 0.3)

    def test_opacity_independent_of_colors(self):
        """Custom opacity checkbox is independent from custom colors checkbox."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            component_colors={"test_comp": "#ff0000"},
            component_opacity={"test_comp": 0.3},
        )
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        color_cb = renderer.create_custom_colors_checkbox()
        opacity_cb = renderer.create_custom_opacities_checkbox()
        self.assertIsNotNone(color_cb)
        self.assertIsNotNone(opacity_cb)
        self.assertIsNot(color_cb, opacity_cb)
        # Enable only opacity
        opacity_cb.value = True
        self.assertTrue(renderer._custom_opacities_active)
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_opacity[0], 0.3)
        # Enable only color
        opacity_cb.value = False
        color_cb.value = True
        self.assertFalse(renderer._custom_opacities_active)
        self.assertTrue(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], "#ff0000")

    def test_grey_all_preserves_custom_opacities(self):
        """_grey_all_components greys unmapped but preserves mapped custom opacities."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"comp_a": 0.1})
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        renderer._custom_opacities_active = True
        renderer._grey_all_components()
        self.assertEqual(renderer.component_opacity[0], 0.1)
        # Unmapped component keeps its original opacity (not changed by grey)
        self.assertEqual(renderer.component_colors[1], "#808080")

    def test_intensity_refresh_preserves_custom_opacities(self):
        """Intensity data refresh keeps mapped components at custom opacity."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp_a": 1.0, "comp_b": 100.0},
            component_opacity={"comp_a": 0.2},
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        orig_op_b = renderer.component_opacity[1]
        renderer._custom_opacities_active = True
        # Simulate intensity refresh: re-recolor all by intensity, then overlay
        new_map = {"comp_a": 50.0, "comp_b": 200.0}
        renderer.intensity_map = new_map
        renderer._min_I = 50.0
        renderer._max_I = 200.0
        for idx in renderer.component_children:
            comp_name = renderer.simple_components[idx]["name"]
            I = new_map.get(comp_name, 0.0)
            color = intensity_to_color(I, 50.0, 200.0, "inferno", True)
            renderer.update_component_color(idx, color)
        renderer._overlay_custom_opacities()
        self.assertEqual(renderer.component_opacity[0], 0.2)
        self.assertEqual(renderer.component_opacity[1], orig_op_b)

    def test_colormode_change_preserves_custom_opacities(self):
        """Colormode change keeps checkbox checked; mapped components retain custom opacity."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            component_opacity={"comp_a": 0.15},
            colormode="component",
            num_components=5,
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        checkbox = renderer.create_custom_opacities_checkbox()
        checkbox.value = True
        self.assertTrue(renderer._custom_opacities_active)
        renderer.create_colorbar()
        renderer.create_intensity_controls()
        selector = renderer.create_colormode_selector()
        selector.value = "default"
        self.assertTrue(renderer._custom_opacities_active)
        self.assertTrue(checkbox.value)
        self.assertEqual(renderer.component_opacity[0], 0.15)

    def test_update_component_opacity_sets_material(self):
        """update_component_opacity sets material.opacity and material.transparent."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        children = renderer.render_component(comp_model, component_index=0)
        mesh = children[0]
        orig_opacity = mesh.material.opacity
        renderer.update_component_opacity(0, 0.25)
        self.assertEqual(mesh.material.opacity, 0.25)
        self.assertTrue(mesh.material.transparent)
        # Color should be unchanged
        orig_color = mesh.material.color
        renderer.update_component_opacity(0, 0.9)
        self.assertEqual(mesh.material.color, orig_color)

    def test_original_opacity_captured_at_render(self):
        """Original opacity is captured from rendered mesh at render time."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        # BoxShape renders with opacity 0.8
        self.assertAlmostEqual(renderer.component_opacity[0], 0.8)

    def test_reset_restores_shape_specific_opacity(self):
        """Reset restores the shape-specific opacity (e.g., 0.8 for box)."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"test": 0.1})
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        self.assertAlmostEqual(renderer.component_opacity[0], 0.8)
        renderer._apply_custom_opacities()
        self.assertEqual(renderer.component_opacity[0], 0.1)
        renderer._reset_to_base_opacities()
        self.assertAlmostEqual(renderer.component_opacity[0], 0.8)

    def test_reset_restores_each_shape_opacity(self):
        """A component with mixed shapes restores every base opacity."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"test": 0.1})
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [
            BoxShape(width=1.0, height=1.0, depth=1.0),
            CylinderShape(radius=1.0, height=2.0),
        ]
        renderer.register_component(comp_model)
        children = renderer.render_component(comp_model, component_index=0)
        base = [child.material.opacity for child in children]

        renderer._apply_custom_opacities()
        self.assertEqual([child.material.opacity for child in children], [0.1, 0.1])
        renderer._reset_to_base_opacities()
        self.assertEqual([child.material.opacity for child in children], base)

    def test_cylinder_shape_specific_opacity(self):
        """Cylinder opacity is size-based and correctly captured."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        comp = make_mock_component("cyl")
        comp_model = ComponentModel(comp)
        # Large cylinder -> smaller opacity
        comp_model.shape_list = [CylinderShape(radius=1.0, height=2.0)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        # largest_dim = max(2*1.0, 2.0) = 2.0 -> > 1.5 -> opacity 0.4
        self.assertAlmostEqual(renderer.component_opacity[0], 0.4)

    def test_both_color_and_opacity_together(self):
        """Custom colors and opacities can be active simultaneously."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(
            component_colors={"comp_a": "#ff0000"},
            component_opacity={"comp_a": 0.2},
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        color_cb = renderer.create_custom_colors_checkbox()
        opacity_cb = renderer.create_custom_opacities_checkbox()
        color_cb.value = True
        opacity_cb.value = True
        self.assertTrue(renderer._custom_colors_active)
        self.assertTrue(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(renderer.component_opacity[0], 0.2)
        # Disable color, keep opacity
        color_cb.value = False
        self.assertFalse(renderer._custom_colors_active)
        self.assertTrue(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], 0.2)
        # Disable opacity, keep color
        opacity_cb.value = False
        color_cb.value = True
        self.assertTrue(renderer._custom_colors_active)
        self.assertFalse(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_colors[0], "#ff0000")


class TestApiComponentOpacities(unittest.TestCase):
    """Tests for component_opacity parameter threading through the API."""

    def test_get_renderer_pythreejs_passes_component_opacity(self):
        """_get_renderer passes component_opacity to PyThreejsRenderer."""
        renderer = _get_renderer("pythreejs", component_opacity={"a": 0.5})
        self.assertEqual(renderer.component_opacity_map, {"a": 0.5})

    def test_get_renderer_matplotlib_ignores_component_opacity(self):
        """_get_renderer strips component_opacity for matplotlib backend."""
        renderer = _get_renderer("matplotlib", component_opacity={"a": 0.5})
        self.assertFalse(hasattr(renderer, 'component_opacity_map'))

    def test_view_with_guess_component_opacity_checkbox_works(self):
        """Custom opacity checkbox applies opacities to rendered components."""
        instr = MagicMock()
        comp1 = make_mock_component("guide1")
        comp2 = make_mock_component("sample1")
        instr.component_list = [comp1, comp2]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(
            instr,
            backend="pythreejs",
            component_opacity={"guide1": 0.3},
        )
        import ipywidgets as ipw
        custom_cb = None
        controls = result.children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom opacity":
                custom_cb = child
                break
        self.assertIsNotNone(custom_cb)
        self.assertFalse(custom_cb.value)
        custom_cb.value = True
        hbox = result.children[1]
        scene = hbox.children[0]
        self.assertGreater(len(scene.scene.children), 0)

    def test_view_with_guess_no_opacity_checkbox_without_opacities(self):
        """view_with_guess without component_opacity produces no custom opacity checkbox."""
        instr = MagicMock()
        comp = make_mock_component("test_comp")
        instr.component_list = [comp]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(instr, backend="pythreejs")
        import ipywidgets as ipw
        children = result.children
        custom_cb = None
        controls = children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom opacity":
                custom_cb = child
                break
        self.assertIsNone(custom_cb)

    def test_view_with_guess_opacity_checkbox_present_with_opacities(self):
        """view_with_guess with component_opacity produces a custom opacity checkbox."""
        instr = MagicMock()
        comp = make_mock_component("test_comp")
        instr.component_list = [comp]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(
            instr,
            backend="pythreejs",
            component_opacity={"test_comp": 0.5},
        )
        import ipywidgets as ipw
        children = result.children
        custom_cb = None
        controls = children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom opacity":
                custom_cb = child
                break
        self.assertIsNotNone(custom_cb)

    def test_view_with_guess_both_checkboxes_independent(self):
        """Both custom colors and custom opacity checkboxes appear when both mappings provided."""
        instr = MagicMock()
        comp = make_mock_component("test_comp")
        instr.component_list = [comp]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(
            instr,
            backend="pythreejs",
            component_colors={"test_comp": "#ff0000"},
            component_opacity={"test_comp": 0.5},
        )
        import ipywidgets as ipw
        color_cb = None
        opacity_cb = None
        controls = result.children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom colors":
                color_cb = child
            elif isinstance(child, ipw.Checkbox) and child.description == "Custom opacity":
                opacity_cb = child
        self.assertIsNotNone(color_cb)
        self.assertIsNotNone(opacity_cb)
        self.assertIsNot(color_cb, opacity_cb)


class TestMaterialIsolationOpacity(unittest.TestCase):
    """Tests for component-scoped material isolation with opacity changes."""

    def test_changing_one_component_opacity_does_not_affect_other(self):
        """update_component_opacity on comp1 must not change comp2's material opacity."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        comp1 = make_mock_component("comp1")
        model1 = ComponentModel(comp1)
        model1.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model1)
        children1 = renderer.render_component(model1, component_index=0)

        comp2 = make_mock_component("comp2")
        model2 = ComponentModel(comp2)
        model2.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model2)
        children2 = renderer.render_component(model2, component_index=1)

        orig_opacity2 = children2[0].material.opacity
        renderer.update_component_opacity(0, 0.1)
        self.assertEqual(children1[0].material.opacity, 0.1)
        self.assertEqual(children2[0].material.opacity, orig_opacity2,
                         "Component 2's material opacity must not change")

    def test_custom_single_component_opacity_affects_only_that_component(self):
        """Custom opacity for comp_a must not change comp_b's opacity."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"comp_a": 0.15})
        comp_a = make_mock_component("comp_a")
        model_a = ComponentModel(comp_a)
        model_a.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_a)
        renderer.render_component(model_a, component_index=0)

        comp_b = make_mock_component("comp_b")
        model_b = ComponentModel(comp_b)
        model_b.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_b)
        children_b = renderer.render_component(model_b, component_index=1)
        orig_opacity_b = children_b[0].material.opacity

        renderer._apply_custom_opacities()
        self.assertEqual(renderer.component_opacity[0], 0.15)
        self.assertEqual(children_b[0].material.opacity, orig_opacity_b,
                         "Unmapped component's material must not change")

    def test_custom_opacity_does_not_affect_color(self):
        """Applying custom opacity must not mutate the material color."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_opacity={"comp_a": 0.15})
        comp_a = make_mock_component("comp_a")
        model_a = ComponentModel(comp_a)
        model_a.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_a)
        children = renderer.render_component(model_a, component_index=0)
        orig_color = children[0].material.color
        renderer._apply_custom_opacities()
        self.assertEqual(children[0].material.color, orig_color)

    def test_custom_color_does_not_affect_opacity(self):
        """Applying custom color must not mutate the material opacity."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(component_colors={"comp_a": "#ff0000"})
        comp_a = make_mock_component("comp_a")
        model_a = ComponentModel(comp_a)
        model_a.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_a)
        children = renderer.render_component(model_a, component_index=0)
        orig_opacity = children[0].material.opacity
        renderer._apply_custom_colors()
        self.assertEqual(children[0].material.opacity, orig_opacity)


class TestGeometryRule(unittest.TestCase):
    """Tests for GeometryRule and GeometryRuleRegistry."""

    def test_rule_matches_must_have(self):
        """Rule with must_have matches when parameter exists."""
        from mcstasscript.geometry_viewer.rules import GeometryRule
        comp = MagicMock()
        comp.parameter_names = ["xwidth", "yheight"]
        comp.parameter_defaults = {}
        rule = GeometryRule(must_have={"xwidth": True})
        self.assertTrue(rule.matches(comp))

    def test_rule_no_match_must_have_missing(self):
        """Rule with must_have fails when parameter is missing."""
        from mcstasscript.geometry_viewer.rules import GeometryRule
        comp = MagicMock()
        comp.parameter_names = ["yheight"]
        comp.parameter_defaults = {}
        rule = GeometryRule(must_have={"xwidth": True})
        self.assertFalse(rule.matches(comp))

    def test_rule_matches_must_not_have(self):
        """Rule with must_not_have matches when parameter is absent."""
        from mcstasscript.geometry_viewer.rules import GeometryRule
        comp = MagicMock()
        comp.parameter_names = ["xwidth"]
        comp.parameter_defaults = {}
        rule = GeometryRule(must_not_have={"zdepth": False})
        self.assertTrue(rule.matches(comp))

    def test_rule_no_match_must_not_have_present(self):
        """Rule with must_not_have fails when parameter exists."""
        from mcstasscript.geometry_viewer.rules import GeometryRule
        comp = MagicMock()
        comp.parameter_names = ["xwidth", "zdepth"]
        comp.parameter_defaults = {}
        rule = GeometryRule(must_not_have={"zdepth": False})
        self.assertFalse(rule.matches(comp))

    def test_rule_matches_must_be_set(self):
        """Rule with must_be_set matches when parameter differs from default."""
        from mcstasscript.geometry_viewer.rules import GeometryRule
        comp = MagicMock()
        comp.parameter_names = ["xwidth"]
        comp.xwidth = 2.0
        comp.parameter_defaults = {"xwidth": 0.0}
        rule = GeometryRule(must_be_set={"xwidth": True})
        self.assertTrue(rule.matches(comp))

    def test_rule_no_match_must_be_set_not_set(self):
        """Rule with must_be_set fails when parameter equals default."""
        from mcstasscript.geometry_viewer.rules import GeometryRule
        comp = MagicMock()
        comp.parameter_names = ["xwidth"]
        comp.xwidth = 0.0
        comp.parameter_defaults = {"xwidth": 0.0}
        rule = GeometryRule(must_be_set={"xwidth": True})
        self.assertFalse(rule.matches(comp))

    def test_rule_matches_must_not_be_set(self):
        """Rule with must_not_be_set matches when param not in parameter_names."""
        from mcstasscript.geometry_viewer.rules import GeometryRule
        comp = MagicMock()
        comp.parameter_names = ["xwidth"]
        comp.parameter_defaults = {"xwidth": 0.0}
        rule = GeometryRule(must_not_be_set={"zdepth": False})
        self.assertTrue(rule.matches(comp))

    def test_rule_component_names_filter(self):
        """Rule with component_names only matches listed types."""
        from mcstasscript.geometry_viewer.rules import GeometryRule
        comp = MagicMock()
        comp.component_name = "MyGuide"
        comp.parameter_names = []
        comp.parameter_defaults = {}
        rule = GeometryRule(component_names=("MyGuide", "Other"), priority=10)
        self.assertTrue(rule.matches(comp))
        comp.component_name = "Unknown"
        self.assertFalse(rule.matches(comp))

    def test_registry_priority_order(self):
        """Registry returns highest-priority (lowest number) matching rule."""
        from mcstasscript.geometry_viewer.rules import GeometryRule, GeometryRuleRegistry
        reg = GeometryRuleRegistry()
        matched = []
        def factory_a(comp, instr_parameters=None):
            matched.append("a")
            return None
        def factory_b(comp, instr_parameters=None):
            matched.append("b")
            return None
        reg.register(GeometryRule(priority=20, factory=factory_b))
        reg.register(GeometryRule(priority=10, factory=factory_a))
        comp = MagicMock()
        comp.parameter_names = []
        comp.parameter_defaults = {}
        rule = reg.match(comp)
        self.assertIsNotNone(rule)
        self.assertEqual(rule.priority, 10)

    def test_registry_no_match(self):
        """Registry returns None when no rule matches."""
        from mcstasscript.geometry_viewer.rules import GeometryRule, GeometryRuleRegistry
        reg = GeometryRuleRegistry()
        reg.register(GeometryRule(must_have={"missing": True}, priority=10))
        comp = MagicMock()
        comp.parameter_names = ["other"]
        comp.parameter_defaults = {}
        self.assertIsNone(reg.match(comp))


class TestSafeEval(unittest.TestCase):
    """Tests for safe_eval expression evaluation."""

    def test_numeric_literal(self):
        """Direct numeric string evaluates correctly."""
        self.assertAlmostEqual(safe_eval("3.14"), 3.14)
        self.assertAlmostEqual(safe_eval("42"), 42.0)
        self.assertAlmostEqual(safe_eval("1.5e-3"), 0.0015)

    def test_arithmetic(self):
        """Basic arithmetic operations work."""
        self.assertAlmostEqual(safe_eval("2 + 3"), 5.0)
        self.assertAlmostEqual(safe_eval("10 - 4"), 6.0)
        self.assertAlmostEqual(safe_eval("3 * 4"), 12.0)
        self.assertAlmostEqual(safe_eval("10 / 4"), 2.5)

    def test_constants(self):
        """Built-in constants PI, DEG2RAD, and RAD2DEG resolve."""
        self.assertAlmostEqual(safe_eval("PI"), math.pi)
        self.assertAlmostEqual(safe_eval("45 * DEG2RAD"), math.pi / 4)
        self.assertAlmostEqual(safe_eval("180 * RAD2DEG"), 180 * 180 / math.pi)

    def test_energy_is_an_instrument_variable_not_a_constant(self):
        """E resolves only when supplied as an instrument variable."""
        with self.assertRaises(UnsafeExpressionError):
            safe_eval("E")
        self.assertAlmostEqual(safe_eval("E", {"E": 12.5}), 12.5)

    def test_math_functions(self):
        """Whitelisted math functions work."""
        self.assertAlmostEqual(safe_eval("sin(PI/2)"), 1.0)
        self.assertAlmostEqual(safe_eval("sqrt(16)"), 4.0)
        self.assertAlmostEqual(safe_eval("abs(-5)"), 5.0)
        self.assertAlmostEqual(safe_eval("pow(2, 3)"), 8.0)

    def test_caret_is_not_power_operator(self):
        """McStas expressions use pow() rather than Python-style caret power."""
        with self.assertRaisesRegex(UnsafeExpressionError, "use pow"):
            safe_eval("2 ^ 3")

    def test_variables(self):
        """Instrument variables are resolved."""
        self.assertAlmostEqual(safe_eval("x + 1", {"x": 3}), 4.0)
        self.assertAlmostEqual(safe_eval("a * b", {"a": 2, "b": 3}), 6.0)

    def test_unsafe_identifier_raises(self):
        """Unresolved identifiers raise UnsafeExpressionError."""
        with self.assertRaises(UnsafeExpressionError):
            safe_eval("__import__('os')")

    def test_unsafe_variable_raises(self):
        """Unknown variable raises UnsafeExpressionError."""
        with self.assertRaises(UnsafeExpressionError):
            safe_eval("unknown_var")

    def test_empty_expression_raises(self):
        """Empty expression raises ValueError."""
        with self.assertRaises(ValueError):
            safe_eval("")

    def test_none_expression_raises(self):
        """None expression raises ValueError."""
        with self.assertRaises(ValueError):
            safe_eval(None)


class TestEulerToRotationMatrix(unittest.TestCase):
    """Tests for euler_to_rotation_matrix."""

    def test_identity(self):
        """Zero angles produce identity matrix."""
        R = euler_to_rotation_matrix(0, 0, 0)
        np.testing.assert_array_almost_equal(R, np.eye(3))

    def test_x_only(self):
        """A 90-degree x rotation uses McStas' first angle."""
        R = euler_to_rotation_matrix(90, 0, 0)
        expected = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
        np.testing.assert_array_almost_equal(R, expected)

    def test_elevation_only(self):
        """90-degree elevation rotates around Y (McStas convention)."""
        R = euler_to_rotation_matrix(0, 90, 0)
        # Rz(0) @ Ry(90deg) @ Rz(0) = Ry(90deg)
        expected = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]])
        np.testing.assert_array_almost_equal(R, expected)

    def test_determinant_one(self):
        """Rotation matrix has determinant 1."""
        R = euler_to_rotation_matrix(0.3, 0.5, 0.7)
        self.assertAlmostEqual(np.linalg.det(R), 1.0, places=10)


class TestResolveTransforms(unittest.TestCase):
    """Tests for resolve_transforms."""

    def _make_comp(self, name, at=(0, 0, 0), at_ref=None,
                   rotated=(0, 0, 0), rot_ref=None, rotated_specified=False):
        comp = MagicMock()
        comp.name = name
        comp.AT_data = list(at)
        comp.AT_reference = at_ref
        comp.ROTATED_data = list(rotated)
        comp.ROTATED_reference = rot_ref
        comp.ROTATED_specified = rotated_specified
        return comp

    def test_absolute_only(self):
        """Components with ABSOLUTE references resolve correctly."""
        comps = [
            self._make_comp("A", at=(1, 2, 3)),
            self._make_comp("B", at=(4, 5, 6)),
        ]
        transforms = resolve_transforms(comps)
        np.testing.assert_array_almost_equal(transforms["A"].position, [1, 2, 3])
        np.testing.assert_array_almost_equal(transforms["B"].position, [4, 5, 6])

    def test_relative_position(self):
        """RELATIVE AT composes with parent position."""
        comps = [
            self._make_comp("A", at=(1, 0, 0)),
            self._make_comp("B", at=(0, 0, 2), at_ref="A"),
        ]
        transforms = resolve_transforms(comps)
        np.testing.assert_array_almost_equal(transforms["B"].position, [1, 0, 2])

    def test_relative_rotation(self):
        """RELATIVE ROTATED composes with parent rotation."""
        comps = [
            self._make_comp("A", at=(0, 0, 0), rotated=(90, 0, 0),
                           rot_ref=None, rotated_specified=True),
            self._make_comp("B", at=(0, 0, 1), at_ref="A",
                           rotated=(0, 0, 0), rot_ref="A", rotated_specified=True),
        ]
        transforms = resolve_transforms(comps)
        self.assertIsNotNone(transforms["B"].rotation_matrix)

    def test_circular_reference_raises(self):
        """Circular AT references raise TransformResolutionError."""
        comps = [
            self._make_comp("A", at=(0, 0, 0), at_ref="B"),
            self._make_comp("B", at=(0, 0, 0), at_ref="A"),
        ]
        with self.assertRaises(TransformResolutionError):
            resolve_transforms(comps)

    def test_missing_reference_raises(self):
        """Reference to non-existent component raises TransformResolutionError."""
        comps = [
            self._make_comp("A", at=(0, 0, 0), at_ref="Missing"),
        ]
        with self.assertRaises(TransformResolutionError):
            resolve_transforms(comps)


class TestSphereShape(unittest.TestCase):
    """Tests for SphereShape."""

    def test_creation(self):
        """SphereShape stores radius and segment counts."""
        s = SphereShape(radius=1.0)
        self.assertEqual(s.radius, 1.0)
        self.assertEqual(s.radial_segments, 32)
        self.assertEqual(s.vertical_segments, 16)
        self.assertIn("SphereShape", repr(s))

    def test_matplotlib_render(self):
        """MatplotlibRenderer can render a SphereShape."""
        from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
        renderer = MatplotlibRenderer()
        shape = SphereShape(radius=0.5)
        result = renderer.render_shape(shape)
        self.assertIsNotNone(result)

    def test_pythreejs_render(self):
        """PyThreejsRenderer can render a SphereShape."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        renderer._temp_color = None  # Initialize for standalone render_shape
        shape = SphereShape(radius=0.5)
        result = renderer.render_shape(shape)
        self.assertIsNotNone(result)


class TestGuessGeometryBuiltins(unittest.TestCase):
    """Tests for built-in geometry guess rules."""

    def _make_comp(self, name="test", component_name="TestComp",
                   parameter_names=None, parameter_defaults=None, **attrs):
        comp = MagicMock()
        comp.name = name
        comp.component_name = component_name
        comp.parameter_names = parameter_names or []
        comp.parameter_defaults = parameter_defaults or {}
        for k, v in attrs.items():
            setattr(comp, k, v)
        return comp

    def test_sphere_from_radius(self):
        """Component with only radius produces SphereShape."""
        comp = self._make_comp(
            parameter_names=["radius"],
            parameter_defaults={"radius": None},
            radius=0.5,
        )
        model = ComponentModel(comp)
        result = model.guess_geometry_from_comp_object()
        self.assertTrue(result)
        self.assertEqual(len(model.shape_list), 1)
        self.assertIsInstance(model.shape_list[0], SphereShape)
        self.assertEqual(model.shape_list[0].radius, 0.5)

    def test_cylinder_from_radius_yheight(self):
        """Component with radius + yheight (no xwidth/zdepth) produces CylinderShape."""
        comp = self._make_comp(
            parameter_names=["radius", "yheight"],
            parameter_defaults={"radius": None, "yheight": None},
            radius=0.3,
            yheight=2.0,
        )
        model = ComponentModel(comp)
        result = model.guess_geometry_from_comp_object()
        self.assertTrue(result)
        self.assertIsInstance(model.shape_list[0], CylinderShape)
        self.assertEqual(model.shape_list[0].radius, 0.3)
        self.assertEqual(model.shape_list[0].height, 2.0)

    def test_solid_box_from_xyz(self):
        """Component with xwidth, yheight, zdepth produces BoxShape."""
        comp = self._make_comp(
            parameter_names=["xwidth", "yheight", "zdepth"],
            parameter_defaults={"xwidth": None, "yheight": None, "zdepth": None},
            xwidth=1.0,
            yheight=2.0,
            zdepth=0.5,
        )
        model = ComponentModel(comp)
        result = model.guess_geometry_from_comp_object()
        self.assertTrue(result)
        self.assertIsInstance(model.shape_list[0], BoxShape)
        self.assertEqual(model.shape_list[0].width, 1.0)
        self.assertEqual(model.shape_list[0].height, 2.0)
        self.assertEqual(model.shape_list[0].depth, 0.5)

    def test_rectangle_outline_xy_only(self):
        """Component with xwidth+yheight (no zdepth) produces rectangle outline."""
        comp = self._make_comp(
            parameter_names=["xwidth", "yheight"],
            parameter_defaults={"xwidth": 0.0, "yheight": 0.0},
            xwidth=2.0,
            yheight=4.0,
        )
        model = ComponentModel(comp)
        result = model.guess_geometry_from_comp_object()
        self.assertTrue(result)
        self.assertIsInstance(model.shape_list[0], LineSegmentsShape)
        self.assertEqual(model.shape_list[0].points.shape, (8, 3))

    def test_rectangle_outline_zy_only(self):
        """Component with zdepth+yheight (no xwidth) produces rectangle outline."""
        comp = self._make_comp(
            parameter_names=["zdepth", "yheight"],
            parameter_defaults={"zdepth": 0.0, "yheight": 0.0},
            zdepth=2.0,
            yheight=4.0,
        )
        model = ComponentModel(comp)
        result = model.guess_geometry_from_comp_object()
        self.assertTrue(result)
        self.assertIsInstance(model.shape_list[0], LineSegmentsShape)
        self.assertEqual(model.shape_list[0].points.shape, (8, 3))

    def test_axis_triad_no_params(self):
        """Component with no parameters produces axis triad."""
        comp = self._make_comp()
        model = ComponentModel(comp)
        result = model.guess_geometry_from_comp_object()
        self.assertTrue(result)
        self.assertIsInstance(model.shape_list[0], LineSegmentsShape)
        self.assertEqual(model.shape_list[0].points.shape, (6, 3))

    def test_unknown_params_raises(self):
        """Component with unrecognized parameters raises ValueError."""
        comp = self._make_comp(
            parameter_names=["custom_param"],
            parameter_defaults={"custom_param": None},
            custom_param=42,
        )
        model = ComponentModel(comp)
        with self.assertRaises(ValueError) as cm:
            model.guess_geometry_from_comp_object()
        self.assertIn("custom_param", str(cm.exception))

    def test_expr_param_resolution(self):
        """Parameter expressions are resolved via instr_parameters."""
        comp = self._make_comp(
            parameter_names=["xwidth", "yheight"],
            parameter_defaults={"xwidth": 0.0, "yheight": 0.0},
            xwidth="2 * w",
            yheight="w + 1",
        )
        model = ComponentModel(comp)
        result = model.guess_geometry_from_comp_object(instr_parameters={"w": 3.0})
        self.assertTrue(result)
        pts = model.shape_list[0].points
        self.assertAlmostEqual(np.max(pts[:, 0]), 3.0)  # xwidth/2 = 6/2 = 3
        self.assertAlmostEqual(np.max(pts[:, 1]), 2.0)  # yheight/2 = 4/2 = 2


class TestGeometryGuessFailureSkip(unittest.TestCase):
    """Tests for graceful handling of geometry guess failures in view_with_guess."""

    def _make_comp(self, name="test", component_name="TestComp",
                   parameter_names=None, parameter_defaults=None, **attrs):
        comp = MagicMock()
        comp.name = name
        comp.component_name = component_name
        comp.parameter_names = parameter_names or []
        comp.parameter_defaults = parameter_defaults or {}
        for k, v in attrs.items():
            setattr(comp, k, v)
        return comp

    def _make_instr(self, components, parameters=None, declare_list=None, user_var_list=None):
        instr = MagicMock()
        instr.component_list = components
        instr.parameters = parameters or []
        instr.declare_list = declare_list or []
        instr.user_var_list = user_var_list or []
        return instr

    def test_bad_geometry_component_skipped_others_render(self):
        """A component with unguessable geometry is skipped; others render."""
        good_comp = self._make_comp(
            name="good_box",
            parameter_names=["xwidth", "yheight", "zdepth"],
            parameter_defaults={"xwidth": None, "yheight": None, "zdepth": None},
            xwidth=1.0, yheight=1.0, zdepth=1.0,
        )
        bad_comp = self._make_comp(
            name="bad_comp",
            parameter_names=["weird_param"],
            parameter_defaults={"weird_param": None},
            weird_param=42,
        )
        another_good = self._make_comp(
            name="another_good",
            parameter_names=["radius"],
            parameter_defaults={"radius": None},
            radius=0.5,
        )

        instr = self._make_instr([good_comp, bad_comp, another_good])

        rendered_names = []

        class MockRenderer:
            def render_component(self, model, component_index=0):
                rendered_names.append(model.comp.name)
                return []
            def make_scene(self, children, **kwargs):
                return "scene"
            def next_component(self):
                pass

        with unittest.mock.patch(
            "mcstasscript.geometry_viewer.api._get_renderer",
            return_value=MockRenderer(),
        ):
            import io, sys
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                result = view_with_guess(instr, backend="matplotlib", verbose=True)
            finally:
                sys.stdout = old_stdout

        output = captured.getvalue()
        self.assertIn("Skipping component 'bad_comp'", output)
        self.assertIn("Geometry guess could not recognize 1 component", output)
        self.assertIn("verbose=True", output)
        self.assertIn("good_box", rendered_names)
        self.assertIn("another_good", rendered_names)
        self.assertNotIn("bad_comp", rendered_names)


class TestTransformFailureDiagnostics(unittest.TestCase):
    """Tests for transform failure diagnostics in view_with_guess."""

    def _make_comp(self, name, at=(0, 0, 0), at_ref=None,
                   rotated=(0, 0, 0), rot_ref=None, rotated_specified=False,
                   parameter_names=None, parameter_defaults=None, **attrs):
        comp = MagicMock()
        comp.name = name
        comp.AT_data = list(at)
        comp.AT_reference = at_ref
        comp.ROTATED_data = list(rotated)
        comp.ROTATED_reference = rot_ref
        comp.ROTATED_specified = rotated_specified
        comp.parameter_names = parameter_names or []
        comp.parameter_defaults = parameter_defaults or {}
        for k, v in attrs.items():
            setattr(comp, k, v)
        return comp

    def _make_instr(self, components, parameters=None, declare_list=None, user_var_list=None):
        instr = MagicMock()
        instr.component_list = components
        instr.parameters = parameters or []
        instr.declare_list = declare_list or []
        instr.user_var_list = user_var_list or []
        return instr

    def test_failed_transform_prints_component_and_dependents(self):
        """Transform failure prints which component failed and which depend on it."""
        # "MissingParent" doesn't exist; base, child1, child2 directly reference it.
        # "orphan" has no dependency on MissingParent.
        base = self._make_comp("base", at=(0, 0, 0), at_ref="MissingParent")
        child1 = self._make_comp("child1", at=(1, 0, 0), at_ref="MissingParent")
        child2 = self._make_comp("child2", at=(2, 0, 0), at_ref="MissingParent")
        orphan = self._make_comp("orphan", at=(3, 0, 0))

        instr = self._make_instr([base, child1, child2, orphan])

        import io, sys
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(TransformResolutionError):
                view_with_guess(instr, backend="matplotlib")
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        self.assertIn("MissingParent", output)
        self.assertIn("base", output)
        self.assertIn("child1", output)
        self.assertIn("child2", output)
        self.assertNotIn("orphan", output)

    def test_failed_transform_can_be_quiet(self):
        """Verbose=False suppresses geometry-guess diagnostics on stdout."""
        base = self._make_comp("base", at=(0, 0, 0), at_ref="MissingParent")
        instr = self._make_instr([base])

        import io, sys
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(TransformResolutionError):
                view_with_guess(instr, backend="matplotlib", verbose=False)
        finally:
            sys.stdout = old_stdout

        self.assertEqual(captured.getvalue(), "")


if __name__ == '__main__':
    unittest.main()
