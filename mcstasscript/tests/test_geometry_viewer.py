import json
import os
import unittest
from unittest.mock import MagicMock

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
)
from mcstasscript.geometry_viewer.model.shapes import (
    Style,
    BoxShape,
    LineSegmentsShape,
    CircleShape,
    ConeShape,
    CylinderShape,
    PolyhedronShape,
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
    intensity_to_color,
)
from mcstasscript.geometry_viewer.api import _get_renderer


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
        self.assertEqual(DEFAULT_NAVIGATOR_DISTANCE, 2.0)


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

    def test_colormode_selector_no_intensity(self):
        """Without intensity_map, selector should not include 'Intensity'."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer()
        selector = renderer.create_colormode_selector()
        self.assertNotIn("Intensity", selector.options)

    def test_no_intensity_map_falls_through(self):
        """Without intensity_map, default colormode should work as before."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(colormode="default")
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.render_component(comp_model, component_index=0)
        self.assertIsNone(renderer._temp_color)


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


class TestColorbarImage(unittest.TestCase):
    """Tests for create_colorbar_image: generates a PNG colorbar."""

    def test_returns_png_bytes(self):
        """Should return valid PNG bytes."""
        from mcstasscript.geometry_viewer.config import create_colorbar_image
        result = create_colorbar_image("inferno", 0.1, 10.0, "Test", log_scale=True)
        self.assertIsInstance(result, bytes)
        self.assertTrue(result.startswith(b'\x89PNG'))

    def test_linear_scale(self):
        """Linear scale should produce valid PNG."""
        from mcstasscript.geometry_viewer.config import create_colorbar_image
        result = create_colorbar_image("viridis", 0, 100, "Index", log_scale=False)
        self.assertIsInstance(result, bytes)
        self.assertTrue(result.startswith(b'\x89PNG'))

    def test_different_colormaps(self):
        """Different colormaps should produce different images."""
        from mcstasscript.geometry_viewer.config import create_colorbar_image
        img1 = create_colorbar_image("inferno", 1.0, 100.0, "Test", log_scale=True)
        img2 = create_colorbar_image("viridis", 1.0, 100.0, "Test", log_scale=True)
        self.assertNotEqual(img1, img2)

    def test_zero_min(self):
        """Zero min with log scale should fall back to linear."""
        from mcstasscript.geometry_viewer.config import create_colorbar_image
        result = create_colorbar_image("inferno", 0.0, 10.0, "Test", log_scale=True)
        self.assertIsInstance(result, bytes)


class TestPyThreejsColorbar(unittest.TestCase):
    """Tests for PyThreejsRenderer colorbar widget."""

    def test_colorbar_intensity_mode(self):
        """In intensity mode, create_colorbar should return an Image widget."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.Image)

    def test_colorbar_default_mode(self):
        """In default mode, create_colorbar should return a Label (hidden)."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(colormode="default")
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.Label)

    def test_colorbar_component_mode(self):
        """In component mode, create_colorbar should return an Image widget."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(colormode="component", num_components=10)
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.Image)

    def test_colorbar_label_stored(self):
        """colorbar_label should be stored on the renderer."""
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        renderer = PyThreejsRenderer(colorbar_label="Wavelength [Å]")
        self.assertEqual(renderer.colorbar_label, "Wavelength [Å]")


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


if __name__ == '__main__':
    unittest.main()
