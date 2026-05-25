import assert from "node:assert/strict";
import test from "node:test";

import { parseUrdf, TEXTTOCAD_URDF_NAMESPACE } from "./parseUrdf.js";

class FakeElement {
  constructor(tagName, attributes = {}, children = []) {
    this.nodeType = 1;
    this.tagName = tagName;
    this.localName = String(tagName || "").split(":").pop();
    this.namespaceURI = tagName.startsWith("texttocad:") ? TEXTTOCAD_URDF_NAMESPACE : null;
    this._attributes = { ...attributes };
    this.childNodes = children;
  }

  getAttribute(name) {
    return Object.hasOwn(this._attributes, name) ? this._attributes[name] : null;
  }
}

class FakeDocument {
  constructor(documentElement) {
    this.documentElement = documentElement;
  }

  querySelector(selector) {
    return selector === "parsererror" ? null : null;
  }
}

function withFakeDomParser(document, callback) {
  const previous = globalThis.DOMParser;
  globalThis.DOMParser = class FakeDomParser {
    parseFromString() {
      return document;
    }
  };
  try {
    return callback();
  } finally {
    globalThis.DOMParser = previous;
  }
}

test("parseUrdf resolves referenced robot material colors from rgba", () => {
  const robot = new FakeElement("robot", { name: "sample_robot" }, [
    new FakeElement("material", { name: "black_aluminum" }, [
      new FakeElement("color", { rgba: "0.168627 0.184314 0.2 1" })
    ]),
    new FakeElement("link", { name: "base_link" }, [
      new FakeElement("visual", {}, [
        new FakeElement("geometry", {}, [
          new FakeElement("mesh", { filename: "meshes/sample_part.stl", scale: "0.001 0.001 0.001" })
        ]),
        new FakeElement("material", { name: "black_aluminum" })
      ])
    ])
  ]);

  const urdfData = withFakeDomParser(new FakeDocument(robot), () => parseUrdf("<robot />", { sourceUrl: "/models/sample_robot.urdf" }));

  assert.equal(urdfData.links[0].visuals[0].color, "#2b2f33");
  assert.equal(
    urdfData.links[0].visuals[0].meshUrl,
    "/models/meshes/sample_part.stl"
  );
});

test("parseUrdf preserves non-zero default joint angles from default_deg", () => {
  const robot = new FakeElement("robot", { name: "sample_robot" }, [
    new FakeElement("link", { name: "base_link" }),
    new FakeElement("link", { name: "arm_link" }),
    new FakeElement("joint", { name: "base_to_arm", type: "continuous", default_deg: "90" }, [
      new FakeElement("parent", { link: "base_link" }),
      new FakeElement("child", { link: "arm_link" }),
      new FakeElement("origin", { xyz: "0 0 0", rpy: "0 0 0" }),
      new FakeElement("axis", { xyz: "0 1 0" })
    ])
  ]);

  const urdfData = withFakeDomParser(new FakeDocument(robot), () => parseUrdf("<robot />", { sourceUrl: "/models/sample_robot.urdf" }));

  assert.equal(urdfData.joints[0].defaultValueDeg, 90);
});

test("parseUrdf accepts prismatic mimic joints", () => {
  const robot = new FakeElement("robot", { name: "sample_robot" }, [
    new FakeElement("link", { name: "base_link" }),
    new FakeElement("link", { name: "servo_link" }),
    new FakeElement("link", { name: "claw_link" }),
    new FakeElement("joint", { name: "gripper_servo", type: "revolute" }, [
      new FakeElement("parent", { link: "base_link" }),
      new FakeElement("child", { link: "servo_link" }),
      new FakeElement("limit", { lower: "0", upper: "1", effort: "1", velocity: "1" })
    ]),
    new FakeElement("joint", { name: "claw_slide", type: "prismatic" }, [
      new FakeElement("parent", { link: "base_link" }),
      new FakeElement("child", { link: "claw_link" }),
      new FakeElement("axis", { xyz: "1 0 0" }),
      new FakeElement("limit", { lower: "0", upper: "0.05", effort: "1", velocity: "1" }),
      new FakeElement("mimic", { joint: "gripper_servo", multiplier: "0.0065", offset: "0" })
    ])
  ]);

  const urdfData = withFakeDomParser(new FakeDocument(robot), () => parseUrdf("<robot />", { sourceUrl: "/models/sample_robot.urdf" }));

  assert.equal(urdfData.joints[1].type, "prismatic");
  assert.equal(urdfData.joints[1].maxValueDeg, 0.05);
  assert.deepEqual(urdfData.joints[1].mimic, {
    joint: "gripper_servo",
    multiplier: 0.0065,
    offset: 0
  });
});

test("parseUrdf captures viewer pose presets", () => {
  const robot = new FakeElement("robot", { name: "sample_robot" }, [
    new FakeElement("link", { name: "base_link" }),
    new FakeElement("link", { name: "arm_link" }),
    new FakeElement("joint", { name: "base_to_arm", type: "continuous", default_deg: "15" }, [
      new FakeElement("parent", { link: "base_link" }),
      new FakeElement("child", { link: "arm_link" }),
      new FakeElement("origin", { xyz: "0 0 0", rpy: "0 0 0" }),
      new FakeElement("axis", { xyz: "0 1 0" })
    ]),
    new FakeElement("texttocad:poses", {}, [
      new FakeElement("texttocad:pose", { name: "home" }, [
        new FakeElement("texttocad:joint", { name: "base_to_arm", value: "45" })
      ])
    ])
  ]);

  const urdfData = withFakeDomParser(new FakeDocument(robot), () => parseUrdf("<robot />", { sourceUrl: "/models/sample_robot.urdf" }));

  assert.deepEqual(urdfData.poses, [
    {
      name: "home",
      jointValuesByName: {
        base_to_arm: 45
      }
    }
  ]);
});

test("parseUrdf rejects viewer poses that reference missing joints", () => {
  const robot = new FakeElement("robot", { name: "sample_robot" }, [
    new FakeElement("link", { name: "base_link" }),
    new FakeElement("link", { name: "arm_link" }),
    new FakeElement("joint", { name: "base_to_arm", type: "continuous" }, [
      new FakeElement("parent", { link: "base_link" }),
      new FakeElement("child", { link: "arm_link" }),
      new FakeElement("axis", { xyz: "0 1 0" })
    ]),
    new FakeElement("texttocad:poses", {}, [
      new FakeElement("texttocad:pose", { name: "home" }, [
        new FakeElement("texttocad:joint", { name: "missing_joint", value: "45" })
      ])
    ])
  ]);

  assert.throws(
    () => withFakeDomParser(new FakeDocument(robot), () => parseUrdf("<robot />", { sourceUrl: "/models/sample_robot.urdf" })),
    /Viewer pose home references missing joint missing_joint/
  );
});
