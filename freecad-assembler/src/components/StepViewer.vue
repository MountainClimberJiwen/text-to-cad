<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { Download, LoaderCircle, Plus, SendHorizontal, Upload } from 'lucide-vue-next';
import occtimportjs from 'occt-import-js';
import occtWasmUrl from 'occt-import-js/dist/occt-import-js.wasm?url';
import occtWorkerUrl from 'occt-import-js/dist/occt-import-js-worker.js?url';

const viewerEl = ref(null);
const models = ref([]);
const currentFileName = ref('');
const statusTone = ref('idle');
const statusMessage = ref('');
const promptInput = ref('');
const chatPending = ref(false);
const chatError = ref('');
const uploadPending = ref(false);
const generatedStepName = ref('');
const messages = ref([]);
const sessionId = ref('');
const wordFileInput = ref(null);
const webglUnavailable = ref(false);
const latestWordText = ref('');
const latestWordFileName = ref('');
const DEFAULT_MODEL_FILE = 'cube_2cm_generator_20260402013428.step';

let messageId = 1;
let occt = null;
let activeModelRoot = null;
let frameHandle = 0;
let resizeObserver = null;
let renderer = null;
let controls = null;

const scene = new THREE.Scene();
scene.background = new THREE.Color('#e7ebe4');

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100000);
camera.position.set(320, 240, 320);

const hemiLight = new THREE.HemisphereLight(0xffffff, 0x748171, 1.35);
scene.add(hemiLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 1.1);
dirLight.position.set(180, 220, 160);
scene.add(dirLight);

const fillLight = new THREE.DirectionalLight(0xfff2df, 0.4);
fillLight.position.set(-120, 80, -90);
scene.add(fillLight);

const grid = new THREE.GridHelper(600, 24, 0xa1aba0, 0xc8cec8);
grid.position.y = -60;
scene.add(grid);

function nextMessageId() {
  messageId += 1;
  return `msg-${messageId}`;
}

function setStatus(message, tone = 'idle') {
  statusMessage.value = message;
  statusTone.value = tone;
}

function pushMessage(message) {
  messages.value.push({
    id: nextMessageId(),
    ...message
  });
}

function resizeRenderer() {
  if (!viewerEl.value) {
    return;
  }
  if (!renderer) {
    return;
  }

  const width = viewerEl.value.clientWidth;
  const height = viewerEl.value.clientHeight;
  if (!width || !height) {
    return;
  }

  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function animate() {
  if (!renderer || !controls) {
    return;
  }
  controls.update();
  renderer.render(scene, camera);
  frameHandle = window.requestAnimationFrame(animate);
}

function colorFromArray(rgb) {
  const [r = 180, g = 180, b = 180] = rgb || [];
  const scale = r <= 1 && g <= 1 && b <= 1 ? 1 : 255;
  return new THREE.Color(r / scale, g / scale, b / scale);
}

function createMaterial(rgb) {
  return new THREE.MeshStandardMaterial({
    color: colorFromArray(rgb),
    metalness: 0.08,
    roughness: 0.62
  });
}

function createMeshFromOcct(meshData) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute(meshData.attributes.position.array, 3)
  );

  if (meshData.attributes.normal?.array?.length) {
    geometry.setAttribute(
      'normal',
      new THREE.Float32BufferAttribute(meshData.attributes.normal.array, 3)
    );
  } else {
    geometry.computeVertexNormals();
  }

  geometry.setIndex(meshData.index.array);

  const material = createMaterial(meshData.color);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = meshData.name || 'STEPMesh';
  return mesh;
}

function buildNode(node, meshes) {
  const group = new THREE.Group();
  group.name = node.name || 'STEPNode';

  for (const meshIndex of node.meshes || []) {
    const meshData = meshes[meshIndex];
    if (meshData) {
      group.add(createMeshFromOcct(meshData));
    }
  }

  for (const child of node.children || []) {
    group.add(buildNode(child, meshes));
  }

  return group;
}

function centerGeometry(object3d) {
  const box = new THREE.Box3().setFromObject(object3d);
  if (box.isEmpty()) {
    return null;
  }

  const center = box.getCenter(new THREE.Vector3());
  // Recenter by moving the model root instead of mutating mesh geometry.
  // This keeps node/local transforms intact for complex STEP hierarchies.
  object3d.position.sub(center);
  object3d.updateMatrixWorld(true);

  return new THREE.Box3().setFromObject(object3d);
}

function frameObject(object3d) {
  const box = centerGeometry(object3d);
  if (!box) {
    return;
  }

  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const radius = Math.max(sphere.radius, 1);
  const fitOffset = 2.2;
  const halfFovY = THREE.MathUtils.degToRad(camera.fov * 0.5);
  const halfFovX = Math.atan(Math.tan(halfFovY) * camera.aspect);
  const distanceY = radius / Math.tan(halfFovY);
  const distanceX = radius / Math.tan(halfFovX);
  const distance = Math.max(distanceX, distanceY) * fitOffset;
  const viewDirection = new THREE.Vector3(1, 0.92, 1.08).normalize();

  if (!controls) {
    return;
  }

  controls.target.set(0, 0, 0);
  camera.near = Math.max(distance / 1000, 0.01);
  camera.far = Math.max(distance * 100, 1000);
  camera.position.copy(viewDirection).multiplyScalar(distance);
  camera.up.set(0, 1, 0);
  camera.lookAt(controls.target);
  camera.updateProjectionMatrix();
  object3d.position.set(0, 0, 0);
  object3d.updateMatrixWorld(true);

  controls.update();
  grid.position.set(0, box.min.y, 0);
  grid.scale.setScalar(Math.max(radius / 80, 1));
}

async function ensureOcct() {
  if (!occt) {
    setStatus('正在初始化 STEP 引擎', 'running');
    occt = await occtimportjs({
      locateFile(fileName) {
        if (fileName.endsWith('.wasm')) {
          return occtWasmUrl;
        }
        if (fileName.endsWith('-worker.js')) {
          return occtWorkerUrl;
        }
        return fileName;
      }
    });
  }
  return occt;
}

async function parseStepModel(url) {
  const importer = await ensureOcct();
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`读取 STEP 文件失败: ${response.status}`);
  }

  const buffer = await response.arrayBuffer();
  const result = importer.ReadStepFile(new Uint8Array(buffer), {
    linearUnit: 'millimeter',
    linearDeflectionType: 'bounding_box_ratio',
    linearDeflection: 0.001,
    angularDeflection: 0.5
  });

  if (!result?.success) {
    throw new Error('STEP 解析失败。');
  }

  return result;
}

function disposeMaterial(material) {
  if (Array.isArray(material)) {
    for (const item of material) {
      item.dispose();
    }
    return;
  }

  material?.dispose?.();
}

function disposeObject(root) {
  root.traverse((child) => {
    if (child.geometry) {
      child.geometry.dispose();
    }
    if (child.material) {
      disposeMaterial(child.material);
    }
  });
}

async function loadModel(model) {
  if (!model?.url) {
    return;
  }
  if (webglUnavailable.value) {
    currentFileName.value = model.fileName;
    return;
  }
  currentFileName.value = model.fileName;
  setStatus('正在解析 STEP', 'running');

  const result = await parseStepModel(model.url);
  const modelRoot = buildNode(result.root, result.meshes);

  if (activeModelRoot) {
    scene.remove(activeModelRoot);
    disposeObject(activeModelRoot);
  }

  activeModelRoot = modelRoot;
  scene.add(activeModelRoot);
  frameObject(activeModelRoot);
  setStatus('');
}

async function fetchJson(url, init) {
  const response = await fetch(url, init);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

async function refreshModelList({ autoSelect = false } = {}) {
  try {
    const data = await fetchJson('/api/models');
    models.value = data.models || [];

    if (autoSelect && !webglUnavailable.value && models.value.length) {
      const selectedModel = currentFileName.value
        ? findModelByFileName(currentFileName.value)
        : null;
      const preferredModel = findModelByFileName(DEFAULT_MODEL_FILE);
      const fallbackModel = selectedModel || preferredModel || models.value[0];
      await loadModel(fallbackModel);
      await focusViewer();
    }
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

function findModelByFileName(fileName) {
  return models.value.find((item) => item.fileName === fileName) || null;
}

function normalizeSteps(steps) {
  return Array.isArray(steps)
    ? steps.map((step, index) => ({
      index: index + 1,
      title: step.title,
      items: step.items || []
    }))
    : [];
}

async function focusViewer() {
  await nextTick();
  resizeRenderer();
  controls.update();
}

async function loadAgentConfig() {
  try {
    const payload = await fetchJson('/api/agent/config');
    // Keep probing backend capability but do not expose skill controls in UI.
    void payload;
  } catch (error) {
    if (/404/.test(error.message)) {
      return;
    }
    throw error;
  }
}

async function submitLegacyChat(message) {
  const payload = await fetchJson('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message })
  });

  return {
    mode: 'legacy',
    payload
  };
}

async function submitChatRequest(message, wordContext = '', wordFileName = '') {
  try {
    const payload = await fetchJson('/api/agent/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        sessionId: sessionId.value,
        message,
        wordContext,
        wordFileName,
        skills: [],
        memoryEnabled: true
      })
    });

    return {
      mode: 'agent',
      payload
    };
  } catch (error) {
    if (/404/.test(error.message)) {
      return submitLegacyChat(message);
    }
    throw error;
  }
}

function handleComposerKeydown(event) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) {
    return;
  }

  event.preventDefault();
  if (!chatPending.value) {
    submitAgentChat();
  }
}

function openWordPicker() {
  wordFileInput.value?.click();
}

function getCurrentModelDownloadUrl() {
  if (!currentFileName.value) {
    return '';
  }
  return `/api/models/${encodeURIComponent(currentFileName.value)}/download`;
}

function downloadCurrentModel() {
  const url = getCurrentModelDownloadUrl();
  if (!url) {
    chatError.value = '当前没有可下载模型。';
    return;
  }

  const link = document.createElement('a');
  link.href = url;
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function startNewSession() {
  sessionId.value = '';
  messages.value = [];
  promptInput.value = '';
  chatError.value = '';
  latestWordText.value = '';
  latestWordFileName.value = '';
  setStatus('');
}

async function handleWordUpload(event) {
  const file = event?.target?.files?.[0];
  event.target.value = '';
  if (!file) {
    return;
  }

  uploadPending.value = true;
  chatError.value = '';
  setStatus('正在解析文档', 'running');

  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('/api/word/parse', {
      method: 'POST',
      body: formData
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `Request failed: ${response.status}`);
    }

    pushMessage({
      role: 'assistant',
      kind: 'word',
      text: `已解析文档：${payload.fileName}（${payload.charCount} 字符）`,
      docText: payload.text || ''
    });
    latestWordText.value = payload.text || '';
    latestWordFileName.value = payload.fileName || '';
    setStatus('');
  } catch (error) {
    chatError.value = '文档解析失败，请上传 .docx 文件。';
    setStatus(chatError.value, 'error');
  } finally {
    uploadPending.value = false;
  }
}

async function submitAgentChat() {
  const message = promptInput.value.trim();
  if (!message) {
    chatError.value = '请先输入需求。';
    return;
  }

  pushMessage({ role: 'user', kind: 'text', text: message });
  promptInput.value = '';
  chatPending.value = true;
  chatError.value = '';
  setStatus('正在思考', 'running');

  try {
    const { mode, payload } = await submitChatRequest(
      message,
      latestWordText.value,
      latestWordFileName.value
    );

    if (mode === 'agent') {
      sessionId.value = payload.sessionId || sessionId.value;
    }

    if (mode === 'agent' && (payload.modelEntry?.fileName || payload.artifact?.model_entry?.fileName)) {
      generatedStepName.value = payload.modelEntry?.fileName || payload.artifact?.model_entry?.fileName || '';
      await refreshModelList();

      const generatedModel = generatedStepName.value ? findModelByFileName(generatedStepName.value) : null;
      if (generatedModel) {
        await loadModel(generatedModel);
        await focusViewer();
      }
    }

    pushMessage({
      role: 'assistant',
      kind: mode === 'agent'
        ? (payload.artifact ? 'codegen' : 'analysis')
        : 'analysis',
      text: mode === 'agent'
        ? (payload.reply || '已处理。')
        : (payload.analysis?.summary || '已处理。'),
      steps: mode === 'agent'
        ? normalizeSteps(payload.steps)
        : normalizeSteps([
          { title: '需求拆解', items: payload.analysis?.requirement_analysis || [] },
          { title: '方案框架', items: payload.analysis?.solution_framework || [] },
          { title: '结构细化', items: payload.analysis?.module_design || [] },
          { title: '验证交付', items: payload.analysis?.validation_delivery || [] }
        ]),
      assumptions: mode === 'agent' ? (payload.artifact?.assumptions || []) : [],
      code: mode === 'agent' ? (payload.artifact?.code || '') : ''
    });
    setStatus('');
  } catch (error) {
    chatError.value = error.message;
    setStatus(error.message, 'error');
  } finally {
    chatPending.value = false;
  }
}

onMounted(async () => {
  await nextTick();
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.set(0, 0, 0);
    viewerEl.value.appendChild(renderer.domElement);
    resizeRenderer();
    animate();
  } catch (error) {
    webglUnavailable.value = true;
    setStatus('当前环境不支持 3D 预览。', 'error');
  }

  resizeObserver = new ResizeObserver(() => {
    resizeRenderer();
  });
  resizeObserver.observe(viewerEl.value);

  await loadAgentConfig();
  await refreshModelList({ autoSelect: true });
  if (!statusMessage.value) {
    setStatus('');
  }
});

onBeforeUnmount(() => {
  window.cancelAnimationFrame(frameHandle);
  resizeObserver?.disconnect();
  controls?.dispose();
  if (activeModelRoot) {
    scene.remove(activeModelRoot);
    disposeObject(activeModelRoot);
  }
  renderer?.dispose();
});
</script>

<template>
  <main class="app-shell">
    <section class="chat-shell">
      <section class="message-list">
        <article
          v-for="message in messages"
          :key="message.id"
          class="message"
          :class="[`role-${message.role}`, `kind-${message.kind || 'text'}`]"
        >
          <div class="message-bubble">
            <p class="message-text">{{ message.text }}</p>

            <section v-if="message.steps?.length" class="step-list">
              <article v-for="step in message.steps" :key="step.title" class="step-card">
                <div class="step-index">{{ step.index }}</div>
                <div class="step-body">
                  <h3>{{ step.title }}</h3>
                  <ul v-if="step.items?.length">
                    <li v-for="item in step.items" :key="`${step.title}-${item}`">{{ item }}</li>
                  </ul>
                  <p v-else>待补充</p>
                </div>
              </article>
            </section>

            <section v-if="message.kind === 'codegen'" class="result-block">
              <div v-if="message.assumptions?.length" class="result-section">
                <h3>待确认</h3>
                <ul>
                  <li v-for="item in message.assumptions" :key="item">{{ item }}</li>
                </ul>
              </div>

              <details v-if="message.code" class="code-details">
                <summary>查看脚本</summary>
                <pre class="code-block"><code>{{ message.code }}</code></pre>
              </details>
            </section>
            <section v-if="message.kind === 'word' && message.docText" class="result-block">
              <details class="code-details" open>
                <summary>文档内容</summary>
                <pre class="code-block"><code>{{ message.docText }}</code></pre>
              </details>
            </section>
          </div>
        </article>
      </section>

      <form class="composer" @submit.prevent="submitAgentChat">
        <textarea
          v-model="promptInput"
          class="composer-input"
          placeholder="输入需求"
          @keydown="handleComposerKeydown"
        ></textarea>

        <div class="composer-actions">
          <input
            ref="wordFileInput"
            class="file-hidden"
            type="file"
            accept=".docx"
            @change="handleWordUpload"
          />
          <button
            class="ghost icon-button"
            type="button"
            :disabled="chatPending || uploadPending"
            title="新会话"
            aria-label="新会话"
            @click="startNewSession"
          >
            <Plus class="icon" :size="18" aria-hidden="true" />
          </button>
          <button
            class="ghost icon-button"
            type="button"
            :disabled="uploadPending || chatPending"
            :title="uploadPending ? '解析中' : '上传Word'"
            :aria-label="uploadPending ? '解析中' : '上传Word'"
            @click="openWordPicker"
          >
            <LoaderCircle v-if="uploadPending" class="icon spinning" :size="18" aria-hidden="true" />
            <Upload v-else class="icon" :size="18" aria-hidden="true" />
          </button>
          <button class="primary" type="submit" :disabled="chatPending">
            <LoaderCircle v-if="chatPending" class="icon spinning" :size="16" aria-hidden="true" />
            <SendHorizontal v-else class="icon" :size="16" aria-hidden="true" />
            <span>{{ chatPending ? '处理中...' : '发送' }}</span>
          </button>
        </div>

        <p v-if="statusMessage" class="chat-status" :class="statusTone">{{ statusMessage }}</p>
        <p v-if="chatError" class="chat-error">{{ chatError }}</p>
      </form>
    </section>

    <section class="viewer-shell">
      <div class="viewer-actions">
        <button
          class="ghost icon-button"
          type="button"
          :disabled="!currentFileName"
          title="下载模型"
          aria-label="下载模型"
          @click="downloadCurrentModel"
        >
          <Download class="icon" :size="18" aria-hidden="true" />
        </button>
      </div>
      <div ref="viewerEl" class="viewer-surface">
        <div v-if="webglUnavailable" class="viewer-fallback">当前环境不支持 3D 预览</div>
      </div>
    </section>
  </main>
</template>
