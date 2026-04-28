from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from build123d import Box, Color, Cylinder, Pos, Rot, Shape


DISPLAY_NAME = "L-Shaped Mounting Bracket"


@dataclass(frozen=True)
class BracketParameters:
    base_length: float = 80.0
    base_width: float = 45.0
    base_thickness: float = 8.0
    support_thickness: float = 8.0
    support_height: float = 55.0
    base_hole_diameter: float = 7.0
    base_hole_center_xs: tuple[float, float] = (28.0, 56.0)
    support_hole_diameter: float = 10.0
    support_hole_offset_above_base: float = 32.0


PARAMETERS = BracketParameters()


def _assert_vector_close(actual: object, expected: tuple[float, float, float]) -> None:
    actual_values = (actual.X, actual.Y, actual.Z)
    for actual_value, expected_value in zip(actual_values, expected, strict=True):
        assert isclose(actual_value, expected_value, abs_tol=1e-6)


def _validate_parameters(parameters: BracketParameters) -> None:
    assert parameters.support_thickness <= parameters.base_length
    assert parameters.base_hole_diameter < parameters.base_width
    assert parameters.support_hole_diameter < parameters.base_width
    for hole_center_x in parameters.base_hole_center_xs:
        assert parameters.base_hole_diameter / 2.0 < hole_center_x < (
            parameters.base_length - parameters.base_hole_diameter / 2.0
        )
        assert hole_center_x > parameters.support_thickness + parameters.base_hole_diameter / 2.0
    assert parameters.support_hole_diameter / 2.0 < parameters.support_hole_offset_above_base < (
        parameters.support_height - parameters.support_hole_diameter / 2.0
    )


def _validate_shape(shape: Shape, parameters: BracketParameters) -> None:
    bounds = shape.bounding_box()
    _assert_vector_close(bounds.min, (0.0, -parameters.base_width / 2.0, 0.0))
    _assert_vector_close(
        bounds.max,
        (
            parameters.base_length,
            parameters.base_width / 2.0,
            parameters.base_thickness + parameters.support_height,
        ),
    )
    assert len(shape.solids()) == 1


def build_bracket(parameters: BracketParameters = PARAMETERS) -> Shape:
    _validate_parameters(parameters)

    base_plate = Pos(parameters.base_length / 2.0, 0.0, parameters.base_thickness / 2.0) * Box(
        parameters.base_length,
        parameters.base_width,
        parameters.base_thickness,
    )
    vertical_support = Pos(
        parameters.support_thickness / 2.0,
        0.0,
        parameters.base_thickness + parameters.support_height / 2.0,
    ) * Box(
        parameters.support_thickness,
        parameters.base_width,
        parameters.support_height,
    )

    bracket = base_plate + vertical_support

    for hole_center_x in parameters.base_hole_center_xs:
        base_hole = Pos(hole_center_x, 0.0, parameters.base_thickness / 2.0) * Cylinder(
            parameters.base_hole_diameter / 2.0,
            parameters.base_thickness + 4.0,
        )
        bracket = bracket - base_hole

    support_hole_center_z = parameters.base_thickness + parameters.support_hole_offset_above_base
    support_hole = Pos(parameters.support_thickness / 2.0, 0.0, support_hole_center_z) * Rot(0, 90, 0) * Cylinder(
        parameters.support_hole_diameter / 2.0,
        parameters.support_thickness + 4.0,
    )
    bracket = bracket - support_hole

    bracket.color = Color(0.36, 0.42, 0.50, 1.0)
    _validate_shape(bracket, parameters)
    return bracket


def gen_step() -> dict[str, object]:
    return {
        "shape": build_bracket(),
        "step_output": "bracket.step",
    }
