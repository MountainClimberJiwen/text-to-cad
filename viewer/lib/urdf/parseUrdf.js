import { multiplyTransforms } from "./kinematics.js";

const IDENTITY_TRANSFORM = Object.freeze([
  1, 0, 0, 0,
  0, 1, 0, 0,
  0, 0, 1, 0,
  0, 0, 0, 1
]);
export const TEXTTOCAD_URDF_NAMESPACE = "https://tom-cad.dev/ns/texttocad-urdf/1";
const LEGACY_VIEWER_URDF_NAMESPACE = "https://tom-cad.dev/ns/viewer-urdf/1";

function childElementsByTag(parent, tagName) {
  return Array.from(parent?.childNodes || []).filter((node) => node?.nodeType === 1 && node.tagName === tagName);
}

function childElementsByTextToCadTag(parent, localName) {
  return Array.from(parent?.childNodes || []).filter((node) => {
    if (node?.nodeType !== 1) {
      return false;
    }
    if (node.tagName === `texttocad:${localName}` || node.tagName === `viewer:${localName}`) {
      return true;
    }
    return node.localName === localName && (
      node.namespaceURI === TEXTTOCAD_URDF_NAMESPACE ||
      node.namespaceURI === LEGACY_VIEWER_URDF_NAMESPACE
    );
  });
}

function parseNumberList(value, count, fallback) {
  if (typeof value !== "string" || !value.trim()) {
    return [...fallback];
  }
  const parsed = value.trim().split(/\s+/).map((entry) => Number(entry));
  if (parsed.length !== count || parsed.some((entry) => !Number.isFinite(entry))) {
    throw new Error(`Expected ${count} numeric values, received ${JSON.stringify(value)}`);
  }
  return parsed;
}

function translationTransform(x, y, z) {
  return [
    1, 0, 0, x,
    0, 1, 0, y,
    0, 0, 1, z,
    0, 0, 0, 1
  ];
}

function scaleTransform(x, y, z) {
  return [
    x, 0, 0, 0,
    0, y, 0, 0,
    0, 0, z, 0,
    0, 0, 0, 1
  ];
}

function rotationTransformFromRpy(roll, pitch, yaw) {
  const sr = Math.sin(roll);
  const cr = Math.cos(roll);
  const sp = Math.sin(pitch);
  const cp = Math.cos(pitch);
  const sy = Math.sin(yaw);
  const cy = Math.cos(yaw);
  return [
    cy * cp, (cy * sp * sr) - (sy * cr), (cy * sp * cr) + (sy * sr), 0,
    sy * cp, (sy * sp * sr) + (cy * cr), (sy * sp * cr) - (cy * sr), 0,
    -sp, cp * sr, cp * cr, 0,
    0, 0, 0, 1
  ];
}

function parseOriginTransform(originElement) {
  if (!originElement) {
    return [...IDENTITY_TRANSFORM];
  }
  const [x, y, z] = parseNumberList(originElement.getAttribute("xyz"), 3, [0, 0, 0]);
  const [roll, pitch, yaw] = parseNumberList(originElement.getAttribute("rpy"), 3, [0, 0, 0]);
  return multiplyTransforms(
    translationTransform(x, y, z),
    rotationTransformFromRpy(roll, pitch, yaw)
  );
}

function parseScaleTransform(meshElement) {
  const [x, y, z] = parseNumberList(meshElement?.getAttribute("scale"), 3, [1, 1, 1]);
  return scaleTransform(x, y, z);
}

function normalizeAbsoluteUrl(url) {
  if (url instanceof URL) {
    return url.toString();
  }
  return new URL(url, globalThis.window?.location?.href || "http://localhost/").toString();
}

function resolveMeshUrl(filename, sourceUrl) {
  const normalizedSourceUrl = normalizeAbsoluteUrl(sourceUrl);
  let resolvedUrl;
  if (filename.startsWith("package://")) {
    resolvedUrl = new URL(filename.slice("package://".length).replace(/^\/+/, ""), new URL("/", normalizedSourceUrl));
  } else {
    resolvedUrl = new URL(filename, normalizedSourceUrl);
  }
  return `${resolvedUrl.pathname}${resolvedUrl.search}`;
}

function labelForMeshFilename(filename) {
  const parts = String(filename || "").split("/");
  return parts[parts.length - 1] || "mesh";
}

function parseRgbaColor(rgbaText, context) {
  const values = parseNumberList(rgbaText, 4, [0, 0, 0, 1]);
  if (values.some((value) => value < 0 || value > 1)) {
    throw new Error(`${context} must use rgba values between 0 and 1`);
  }
  return `#${values.slice(0, 3).map((value) => {
    const component = Math.round(value * 255);
    return component.toString(16).padStart(2, "0");
  }).join("")}`;
}

function materialColorFromElement(materialElement, context) {
  const colorElement = childElementsByTag(materialElement, "color")[0];
  const rgbaText = String(colorElement?.getAttribute("rgba") || "").trim();
  if (!rgbaText) {
    return "";
  }
  return parseRgbaColor(rgbaText, context);
}

function parseNamedMaterialColors(robotElement) {
  const namedMaterials = new Map();
  for (const materialElement of childElementsByTag(robotElement, "material")) {
    const name = String(materialElement.getAttribute("name") || "").trim();
    if (!name) {
      continue;
    }
    const color = materialColorFromElement(materialElement, `URDF material ${name}`);
    if (!color) {
      continue;
    }
    namedMaterials.set(name, color);
  }
  return namedMaterials;
}

function resolveVisualColor(visualElement, namedMaterialColors, { linkName, visualIndex }) {
  const materialElement = childElementsByTag(visualElement, "material")[0];
  if (!materialElement) {
    return "";
  }
  const inlineColor = materialColorFromElement(materialElement, `URDF link ${linkName} visual ${visualIndex} material`);
  if (inlineColor) {
    return inlineColor;
  }
  const materialName = String(materialElement.getAttribute("name") || "").trim();
  return materialName ? String(namedMaterialColors.get(materialName) || "") : "";
}

function parseJointDefaultValueDeg(jointElement, jointName) {
  const rawValue = String(jointElement.getAttribute("default_deg") || "").trim();
  if (!rawValue) {
    return 0;
  }
  const parsedValue = Number(rawValue);
  if (!Number.isFinite(parsedValue)) {
    throw new Error(`URDF joint ${jointName} has invalid default_deg ${JSON.stringify(rawValue)}`);
  }
  return parsedValue;
}

function parseJointMimic(jointElement, jointName) {
  const mimicElement = childElementsByTag(jointElement, "mimic")[0];
  if (!mimicElement) {
    return null;
  }
  const joint = String(mimicElement.getAttribute("joint") || "").trim();
  if (!joint) {
    throw new Error(`URDF mimic joint ${jointName} must reference another joint`);
  }
  const multiplierText = String(mimicElement.getAttribute("multiplier") ?? "1").trim() || "1";
  const offsetText = String(mimicElement.getAttribute("offset") ?? "0").trim() || "0";
  const multiplier = Number(multiplierText);
  const offset = Number(offsetText);
  if (!Number.isFinite(multiplier) || !Number.isFinite(offset)) {
    throw new Error(`URDF mimic joint ${jointName} has invalid multiplier or offset`);
  }
  return {
    joint,
    multiplier,
    offset
  };
}

function parseJoint(jointElement, linkNames) {
  const name = String(jointElement.getAttribute("name") || "").trim();
  if (!name) {
    throw new Error("URDF joint name is required");
  }
  const type = String(jointElement.getAttribute("type") || "").trim().toLowerCase();
  if (!["fixed", "continuous", "revolute", "prismatic"].includes(type)) {
    throw new Error(`Unsupported URDF joint type: ${type || "(missing)"}`);
  }
  const parentElement = childElementsByTag(jointElement, "parent")[0];
  const childElement = childElementsByTag(jointElement, "child")[0];
  const parentLink = String(parentElement?.getAttribute("link") || "").trim();
  const childLink = String(childElement?.getAttribute("link") || "").trim();
  if (!parentLink || !childLink) {
    throw new Error(`URDF joint ${name} must declare parent and child links`);
  }
  if (!linkNames.has(parentLink) || !linkNames.has(childLink)) {
    throw new Error(`URDF joint ${name} references missing links`);
  }
  const axis = type === "fixed"
    ? [1, 0, 0]
    : parseNumberList(childElementsByTag(jointElement, "axis")[0]?.getAttribute("xyz"), 3, [1, 0, 0]);
  let minValueDeg = 0;
  let maxValueDeg = 0;
  if (type === "continuous") {
    minValueDeg = -180;
    maxValueDeg = 180;
  } else if (type === "revolute" || type === "prismatic") {
    const limitElement = childElementsByTag(jointElement, "limit")[0];
    if (!limitElement) {
      throw new Error(`URDF ${type} joint ${name} requires <limit>`);
    }
    const lower = Number(limitElement.getAttribute("lower"));
    const upper = Number(limitElement.getAttribute("upper"));
    if (!Number.isFinite(lower) || !Number.isFinite(upper)) {
      throw new Error(`URDF ${type} joint ${name} has invalid limits`);
    }
    if (type === "revolute") {
      minValueDeg = (lower * 180) / Math.PI;
      maxValueDeg = (upper * 180) / Math.PI;
    } else {
      minValueDeg = lower;
      maxValueDeg = upper;
    }
  }
  return {
    name,
    type,
    parentLink,
    childLink,
    originTransform: parseOriginTransform(childElementsByTag(jointElement, "origin")[0]),
    axis,
    defaultValueDeg: type === "fixed" ? 0 : parseJointDefaultValueDeg(jointElement, name),
    minValueDeg,
    maxValueDeg,
    mimic: parseJointMimic(jointElement, name)
  };
}

function parseViewerJointPoseValue(jointElement, { poseName, jointName, joint }) {
  const rawValue = String(jointElement.getAttribute("value") || "").trim();
  if (!rawValue) {
    throw new Error(`Viewer pose ${poseName} joint ${jointName} is missing value`);
  }
  const parsedValue = Number(rawValue);
  if (!Number.isFinite(parsedValue)) {
    throw new Error(`Viewer pose ${poseName} joint ${jointName} has invalid value ${JSON.stringify(rawValue)}`);
  }
  const jointType = String(joint?.type || "fixed");
  if (jointType === "fixed") {
    throw new Error(`Viewer pose ${poseName} joint ${jointName} must target a movable joint`);
  }
  if (joint?.mimic) {
    throw new Error(`Viewer pose ${poseName} joint ${jointName} must target a non-mimic joint`);
  }
  if (jointType !== "continuous") {
    const minValue = Number(joint?.minValueDeg);
    const maxValue = Number(joint?.maxValueDeg);
    if (
      Number.isFinite(minValue) &&
      Number.isFinite(maxValue) &&
      (parsedValue < Math.min(minValue, maxValue) || parsedValue > Math.max(minValue, maxValue))
    ) {
      throw new Error(`Viewer pose ${poseName} joint ${jointName} must stay within joint limits`);
    }
  }
  return parsedValue;
}

function parseViewerPoses(robotElement, joints) {
  const posesElement = childElementsByTextToCadTag(robotElement, "poses")[0];
  if (!posesElement) {
    return [];
  }
  const jointByName = new Map(joints.map((joint) => [String(joint?.name || ""), joint]).filter(([name]) => name));
  const poseNames = new Set();
  return childElementsByTextToCadTag(posesElement, "pose").map((poseElement) => {
    const poseName = String(poseElement.getAttribute("name") || "").trim();
    if (!poseName) {
      throw new Error("Viewer pose name is required");
    }
    if (poseNames.has(poseName)) {
      throw new Error(`Duplicate viewer pose name: ${poseName}`);
    }
    poseNames.add(poseName);

    const jointValuesByName = {};
    for (const jointElement of childElementsByTextToCadTag(poseElement, "joint")) {
      const jointName = String(jointElement.getAttribute("name") || "").trim();
      if (!jointName) {
        throw new Error(`Viewer pose ${poseName} joint name is required`);
      }
      if (Object.hasOwn(jointValuesByName, jointName)) {
        throw new Error(`Viewer pose ${poseName} references joint ${jointName} multiple times`);
      }
      const joint = jointByName.get(jointName);
      if (!joint) {
        throw new Error(`Viewer pose ${poseName} references missing joint ${jointName}`);
      }
      jointValuesByName[jointName] = parseViewerJointPoseValue(
        jointElement,
        {
          poseName,
          jointName,
          joint
        }
      );
    }

    if (!Object.keys(jointValuesByName).length) {
      throw new Error(`Viewer pose ${poseName} must define at least one joint value`);
    }

    return {
      name: poseName,
      jointValuesByName
    };
  });
}

function validateMimicJoints(joints) {
  const jointNames = new Set(joints.map((joint) => joint.name));
  for (const joint of joints) {
    if (!joint.mimic) {
      continue;
    }
    if (!jointNames.has(joint.mimic.joint)) {
      throw new Error(`URDF mimic joint ${joint.name} references missing joint ${joint.mimic.joint}`);
    }
  }
}

function validateTree(links, joints) {
  const linkNames = new Set(links.map((link) => link.name));
  const children = new Set();
  const jointsByParent = new Map();
  const jointNames = new Set();
  for (const joint of joints) {
    if (jointNames.has(joint.name)) {
      throw new Error(`Duplicate URDF joint name: ${joint.name}`);
    }
    jointNames.add(joint.name);
    if (children.has(joint.childLink)) {
      throw new Error(`URDF link ${joint.childLink} has multiple parents`);
    }
    children.add(joint.childLink);
    const current = jointsByParent.get(joint.parentLink) || [];
    current.push(joint.childLink);
    jointsByParent.set(joint.parentLink, current);
  }
  const rootCandidates = [...linkNames].filter((linkName) => !children.has(linkName));
  if (rootCandidates.length !== 1) {
    throw new Error(`URDF must form a single rooted tree; found roots ${JSON.stringify(rootCandidates)}`);
  }
  const rootLink = rootCandidates[0];
  const visited = new Set();
  const visiting = new Set();
  const visit = (linkName) => {
    if (visited.has(linkName)) {
      return;
    }
    if (visiting.has(linkName)) {
      throw new Error("URDF joint graph contains a cycle");
    }
    visiting.add(linkName);
    for (const childLink of jointsByParent.get(linkName) || []) {
      visit(childLink);
    }
    visiting.delete(linkName);
    visited.add(linkName);
  };
  visit(rootLink);
  if (visited.size !== links.length) {
    const missing = links.map((link) => link.name).filter((linkName) => !visited.has(linkName));
    throw new Error(`URDF leaves links disconnected from the root: ${JSON.stringify(missing)}`);
  }
  return rootLink;
}

export function parseUrdf(xmlText, { sourceUrl } = {}) {
  if (typeof DOMParser === "undefined") {
    throw new Error("DOMParser is unavailable in this environment");
  }
  const document = new DOMParser().parseFromString(String(xmlText || ""), "application/xml");
  const parseError = document.querySelector("parsererror");
  if (parseError) {
    throw new Error("Failed to parse URDF XML");
  }
  const robot = document.documentElement;
  if (!robot || robot.tagName !== "robot") {
    throw new Error("URDF root element must be <robot>");
  }
  const robotName = String(robot.getAttribute("name") || "").trim();
  if (!robotName) {
    throw new Error("URDF robot name is required");
  }
  const namedMaterialColors = parseNamedMaterialColors(robot);

  const links = childElementsByTag(robot, "link").map((linkElement) => {
    const name = String(linkElement.getAttribute("name") || "").trim();
    if (!name) {
      throw new Error("URDF link name is required");
    }
    const visuals = childElementsByTag(linkElement, "visual").map((visualElement, index) => {
      const geometryElement = childElementsByTag(visualElement, "geometry")[0];
      const meshElement = geometryElement ? childElementsByTag(geometryElement, "mesh")[0] : null;
      if (!meshElement) {
        throw new Error(`URDF link ${name} uses unsupported visual geometry`);
      }
      const filename = String(meshElement.getAttribute("filename") || "").trim();
      if (!filename) {
        throw new Error(`URDF link ${name} visual ${index + 1} is missing a mesh filename`);
      }
      return {
        id: `${name}:v${index + 1}`,
        label: labelForMeshFilename(filename),
        meshUrl: resolveMeshUrl(filename, sourceUrl || "/"),
        color: resolveVisualColor(visualElement, namedMaterialColors, {
          linkName: name,
          visualIndex: index + 1
        }),
        localTransform: multiplyTransforms(
          parseOriginTransform(childElementsByTag(visualElement, "origin")[0]),
          parseScaleTransform(meshElement)
        )
      };
    });
    return {
      name,
      visuals
    };
  });

  const linkNames = new Set();
  for (const link of links) {
    if (linkNames.has(link.name)) {
      throw new Error(`Duplicate URDF link name: ${link.name}`);
    }
    linkNames.add(link.name);
  }

  const joints = childElementsByTag(robot, "joint").map((jointElement) => parseJoint(jointElement, linkNames));
  validateMimicJoints(joints);
  const rootLink = validateTree(links, joints);
  const poses = parseViewerPoses(robot, joints);

  return {
    robotName,
    rootLink,
    rootWorldTransform: [...IDENTITY_TRANSFORM],
    links,
    joints,
    poses
  };
}
