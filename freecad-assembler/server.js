import express from 'express';
import { execFile } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import mammoth from 'mammoth';
import multer from 'multer';
import path from 'node:path';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

function loadDotEnvFile(envPath) {
  if (!fs.existsSync(envPath)) {
    return;
  }

  const content = fs.readFileSync(envPath, 'utf8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }

    const separatorIndex = trimmed.indexOf('=');
    if (separatorIndex <= 0) {
      continue;
    }

    const key = trimmed.slice(0, separatorIndex).trim();
    let value = trimmed.slice(separatorIndex + 1).trim();

    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    if (process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

loadDotEnvFile(path.resolve(process.cwd(), '.env'));

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const app = express();
const execFileAsync = promisify(execFile);

const PORT = Number.parseInt(process.env.PORT || '3000', 10);
const HOST = process.env.HOST || '127.0.0.1';
const MODELS_DIR = path.join(__dirname, 'models', 'step');
const DIST_DIR = path.join(__dirname, 'dist');
const isProduction = process.env.NODE_ENV === 'production';
const LEGACY_OLLAMA_HOST = process.env.OLLAMA_HOST || 'http://127.0.0.1:11434';
const LEGACY_OLLAMA_MODEL = process.env.OLLAMA_MODEL || 'qwen3-vl:8b';
const LEGACY_OLLAMA_TIMEOUT_MS = Number.parseInt(process.env.OLLAMA_TIMEOUT_MS || '300000', 10);
const LLM_PROVIDER = (process.env.LLM_PROVIDER || 'openai-compatible').trim().toLowerCase();
const LLM_BASE_URL = (
  process.env.LLM_BASE_URL ||
  process.env.OPENAI_BASE_URL ||
  (LLM_PROVIDER === 'ollama' ? LEGACY_OLLAMA_HOST : 'http://127.0.0.1:11434/v1')
).replace(/\/+$/, '');
const LLM_MODEL = process.env.LLM_MODEL || process.env.OPENAI_MODEL || LEGACY_OLLAMA_MODEL;
const CHAT_LLM_MODEL = process.env.CHAT_LLM_MODEL || process.env.AGENT_MODEL || process.env.CHAT_MODEL || '';
const CODEGEN_LLM_MODEL = process.env.CODEGEN_LLM_MODEL || process.env.GENERATE_MODEL || LLM_MODEL;
const LLM_API_KEY = process.env.LLM_API_KEY || process.env.OPENAI_API_KEY || '';
const LLM_TIMEOUT_MS = Number.parseInt(
  process.env.LLM_TIMEOUT_MS || process.env.OPENAI_TIMEOUT_MS || String(LEGACY_OLLAMA_TIMEOUT_MS),
  10
);
const FREECAD_CMD = process.env.FREECAD_CMD || '/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd';
const FREECAD_REFERENCE_SCRIPT = path.join(__dirname, 'scripts', 'freecad', 'build_laser_gantry.py');
const DEFAULT_FREECAD_SCRIPT_NAME = 'generated_freecad_assembly.py';
const GENERATED_SCRIPT_DIR = path.join(__dirname, 'scripts', 'freecad');
const GENERATED_FCSTD_DIR = path.join(__dirname, 'models', 'fcstd');
const GENERATED_STEP_DIR = MODELS_DIR;
const GENERATED_FILE_RETENTION_MS = 24 * 60 * 60 * 1000;
const FREECAD_RUNNER_PATH = path.join(GENERATED_SCRIPT_DIR, '_generated_freecad_runner.py');
const DOCX_EXTRACTOR_SCRIPT = path.join(__dirname, 'scripts', 'skills', 'extract_docx_text.py');
const UPLOAD_TMP_DIR = path.join(__dirname, 'data', 'uploads');
const SKILLS_DIR = path.join(__dirname, 'skills');
const URS_MANUAL_DIR = path.join(__dirname, 'URS-MANUAL');
const AGENT_MEMORY_DIR = path.join(__dirname, 'data');
const AGENT_MEMORY_PATH = path.join(AGENT_MEMORY_DIR, 'agent-memory.jsonl');
const sessionStore = new Map();
let preferredChatModelPromise = null;
let pythonUserSitePromise = null;
const upload = multer({
  storage: multer.diskStorage({
    destination: (_req, _file, cb) => {
      fs.mkdirSync(UPLOAD_TMP_DIR, { recursive: true });
      cb(null, UPLOAD_TMP_DIR);
    },
    filename: (_req, file, cb) => {
      const safeName = String(file.originalname || 'upload.docx').replace(/[^\w.-]+/g, '_');
      cb(null, `${Date.now()}-${safeName}`);
    }
  }),
  limits: {
    fileSize: 12 * 1024 * 1024
  }
});

const PROTECTED_FREECAD_SCRIPT_FILES = new Set([
  path.basename(FREECAD_REFERENCE_SCRIPT),
  path.basename(FREECAD_RUNNER_PATH)
]);

const MODEL_ANALYSIS_PROMPT = `你是硬件结构/3D建模方案助手。
基于用户需求，按下面固定框架输出设计方案。

核心工作流程：
1. 需求抽象与拆解：提炼硬件结构核心需求（尺寸、材质等），明确结构边界与约束
2. 方案框架与架构设计：规划设备物理布局，划分硬件功能模块及衔接逻辑
3. 模块级硬件结构细节设计：完成通用硬件模块设计，优化设备特性适配细节，包含布局设计
4. 验证与交付：开展硬件安装、性能等相关验证，明确交付内容与周期

只返回有效 JSON，不要 Markdown，不要代码块。
字段固定为：
summary: 字符串
requirement_analysis: 字符串数组
solution_framework: 字符串数组
module_design: 字符串数组
validation_delivery: 字符串数组

约束：
- 总字数控制在 200 字以内
- 每个数组用多个 bullet point 风格的短句，最多 2 项
- 不要编造未给出的尺寸、材料、公差
- 输出必须适合直接展示给用户`;

const FREECAD_CODEGEN_PROMPT = `你是 FreeCAD 装配脚本生成器。
目标：根据用户对装配物体的自然语言描述，生成可直接保存为 Python 文件的 FreeCAD 脚本。

输出要求：
1. 只返回有效 JSON，不要 Markdown，不要代码块，不要额外解释
2. 字段固定为：
   summary: 字符串
   file_name: 字符串
   assumptions: 字符串数组
   code: 字符串
3. code 必须是完整 Python 脚本，风格参考给定示例，优先使用：
   - import FreeCAD as App
   - Part
   - reset_doc / make_box / make_lcs / import_step_as_feature / align_by_lcs 这类清晰辅助函数
4. 如果用户没给尺寸，不要编造精确数值；可以使用 clearly named DEFAULT_* 常量承载保守占位值，并在 assumptions 说明待确认项
5. 代码应以装配建模为主，优先使用基础几何体、坐标系、Placement、STEP 导入占位能力
6. 输出必须能读，命名清晰，避免无意义缩写
7. 不要调用网络，不要依赖当前对话之外的文件，除非代码里显式写成可选路径`;

const AGENT_SYSTEM_PROMPT = `你是一个本地工程 Agent Runtime，风格接近 openclaw 核心，但只做当前仓库所需的最小能力。

你会收到：
- 用户当前消息
- 最近对话 memory
- 被启用的 skills 文本

你的目标：
1. 先给出简洁直接的答复
2. 如有必要，给出最多 4 个 step，用于前端展示
3. 当用户明确要“生成 FreeCAD / 生成脚本 / 导出 STEP / 建模落地”时，将 action 设为 "generate_freecad"
4. 如果只是分析、规划、解释、追问，则 action 为 "respond"

只返回有效 JSON，不要 Markdown，不要代码块。
字段固定为：
- reply: 字符串
- steps: { title: 字符串, items: 字符串数组 } 数组，最多 4 项
- action: "respond" | "generate_freecad"
- generate_prompt: 字符串，只有 action=generate_freecad 时填写；应是适合传给 FreeCAD 代码生成器的清晰建模需求

约束：
- 只能回答当前 project 领域相关问题：FreeCAD 装配建模、STEP 模型查看、结构设计拆解、装配方案、项目内 skill/memory/workflow 的使用
- 如果用户问题不属于上述领域，直接拒绝，不要扩展回答
- reply 简短，适合直接显示
- 不要编造未提供的精确尺寸
- steps 只保留对当前任务有帮助的信息
- 没必要时 steps 返回空数组`;

const DOMAIN_REJECTION_MESSAGE = '只回答当前项目领域相关问题：FreeCAD 装配建模、STEP 查看、结构设计与本项目 workflow/skill/memory。';
const URS_OUT_OF_SCOPE_MESSAGE = '这个问题我还回答不了';
const DOMAIN_KEYWORDS = [
  'freecad',
  'step',
  'stp',
  '装配',
  '建模',
  '模型',
  '结构',
  '支架',
  '电机',
  '孔位',
  '布局',
  '工程图',
  '导出',
  'viewer',
  'workflow',
  'skill',
  'memory',
  'occt',
  'three.js',
  'threejs',
  'nema',
  'fcstd',
  '项目',
  '本项目',
  'urs',
  'a1',
  'a2',
  'layout',
  '规划',
  '上料'
];

function normalizeStringList(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => (typeof item === 'string' ? item.trim() : ''))
    .filter(Boolean);
}

function isProjectDomainQuestion(message) {
  const text = String(message || '').trim().toLowerCase();
  if (!text) {
    return false;
  }

  return DOMAIN_KEYWORDS.some((keyword) => text.includes(keyword));
}

function buildDomainRejectionPayload() {
  return {
    reply: DOMAIN_REJECTION_MESSAGE,
    steps: [],
    action: 'respond',
    generate_prompt: ''
  };
}

function normalizeClientIp(rawIp) {
  const value = String(rawIp || '').trim();
  if (!value) {
    return 'unknown';
  }
  if (value.includes(',')) {
    return normalizeClientIp(value.split(',')[0]);
  }
  return value.replace(/^::ffff:/i, '') || 'unknown';
}

function getClientIp(req) {
  const forwarded = req.headers['x-forwarded-for'];
  const realIp = req.headers['x-real-ip'];
  const fromSocket = req.socket?.remoteAddress;
  return normalizeClientIp(forwarded || realIp || fromSocket || '');
}

function buildSessionStoreKey(sessionId, clientIp) {
  return `${normalizeClientIp(clientIp)}::${String(sessionId || '').trim()}`;
}

function ensureSession(sessionId, clientIp = 'unknown') {
  const id = typeof sessionId === 'string' && sessionId.trim()
    ? sessionId.trim()
    : crypto.randomUUID();
  const ip = normalizeClientIp(clientIp);
  const storeKey = buildSessionStoreKey(id, ip);

  if (!sessionStore.has(storeKey)) {
    sessionStore.set(storeKey, {
      messages: []
    });
  }

  return {
    sessionId: id,
    clientIp: ip,
    session: sessionStore.get(storeKey)
  };
}

async function listSkills() {
  let entries = [];
  try {
    entries = await fs.promises.readdir(SKILLS_DIR, { withFileTypes: true });
  } catch {
    return [];
  }

  const parseSkillFrontmatter = (content) => {
    const raw = String(content || '');
    if (!raw.startsWith('---\n')) {
      return { metadata: {}, body: raw };
    }
    const end = raw.indexOf('\n---\n', 4);
    if (end < 0) {
      return { metadata: {}, body: raw };
    }

    const metadataText = raw.slice(4, end);
    const body = raw.slice(end + 5);
    const metadata = {};
    let listKey = '';

    for (const line of metadataText.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) {
        continue;
      }
      const listItem = trimmed.match(/^-\s+(.+)$/);
      if (listItem && listKey) {
        if (!Array.isArray(metadata[listKey])) {
          metadata[listKey] = [];
        }
        metadata[listKey].push(listItem[1].trim());
        continue;
      }

      const match = trimmed.match(/^([a-zA-Z0-9_-]+)\s*:\s*(.*)$/);
      if (!match) {
        listKey = '';
        continue;
      }
      const key = match[1];
      const value = match[2].trim();
      if (!value) {
        metadata[key] = [];
        listKey = key;
        continue;
      }
      metadata[key] = value.replace(/^['"]|['"]$/g, '');
      listKey = '';
    }

    return { metadata, body };
  };

  const skillDirs = entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b));

  const skills = [];
  for (const dirName of skillDirs) {
    const skillFile = path.join(SKILLS_DIR, dirName, 'SKILL.md');
    let rawContent = '';
    try {
      rawContent = await fs.promises.readFile(skillFile, 'utf8');
    } catch {
      continue;
    }

    const { metadata, body } = parseSkillFrontmatter(rawContent);
    const firstLine = body
      .split('\n')
      .map((line) => line.trim())
      .find(Boolean) || dirName;

    const id = String(metadata.name || dirName).trim();
    const triggers = Array.isArray(metadata.triggers)
      ? metadata.triggers.map((item) => String(item || '').trim()).filter(Boolean)
      : [];

    skills.push({
      id,
      fileName: path.join(dirName, 'SKILL.md'),
      title: firstLine.replace(/^#+\s*/, ''),
      content: body.trim(),
      description: String(metadata.description || '').trim(),
      triggers
    });
  }

  return skills;
}

function inferSkillIdsFromMessage(message, skills) {
  const text = String(message || '').toLowerCase();
  if (!text) {
    return [];
  }

  return skills
    .filter((skill) => {
      const triggerTokens = Array.isArray(skill.triggers) ? skill.triggers : [];
      const tokens = Array.from(
        new Set([
          ...triggerTokens.map((item) => String(item).toLowerCase()),
          String(skill.id || '').toLowerCase()
        ])
      );
      return tokens.some((token) => token && text.includes(token));
    })
    .map((skill) => skill.id);
}

function isUrsQuery(message = '', effectiveSkillIds = []) {
  const text = String(message || '').toLowerCase();
  const ursKeywords = [
    'urs',
    'manual',
    'workflow',
    'planner',
    '模块',
    '工艺',
    '布局',
    '选型',
    '验证',
    '交货期',
    'a1',
    'a2',
    '注射笔'
  ];
  if (ursKeywords.some((token) => text.includes(token))) {
    return true;
  }
  return effectiveSkillIds.includes('planner') || effectiveSkillIds.includes('workflow') || effectiveSkillIds.includes('urs-manual');
}

function scoreTextByTokens(haystack, tokens) {
  const text = String(haystack || '').toLowerCase();
  if (!text || !tokens.length) {
    return 0;
  }
  let score = 0;
  for (const token of tokens) {
    if (token && text.includes(token)) {
      score += 1;
    }
  }
  return score;
}

function buildQueryTokens(message) {
  return String(message || '')
    .toLowerCase()
    .split(/[\s,，。；;:：/()（）\[\]【】]+/)
    .map((token) => token.trim())
    .filter((token) => token.length >= 2)
    .slice(0, 24);
}

function chunkMarkdownBySection(content) {
  const lines = String(content || '').split('\n');
  const chunks = [];
  let currentHeader = 'Overview';
  let buffer = [];

  const flush = () => {
    const text = buffer.join('\n').trim();
    if (text) {
      chunks.push({
        header: currentHeader,
        text
      });
    }
    buffer = [];
  };

  for (const line of lines) {
    if (/^#{1,4}\s+/.test(line.trim())) {
      flush();
      currentHeader = line.trim();
      buffer.push(line);
      continue;
    }
    buffer.push(line);
  }
  flush();
  return chunks;
}

async function collectMarkdownFiles(rootDir) {
  const files = [];

  async function walk(currentDir) {
    let entries = [];
    try {
      entries = await fs.promises.readdir(currentDir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      const absPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        await walk(absPath);
        continue;
      }
      if (entry.isFile() && /\.md$/i.test(entry.name)) {
        files.push(absPath);
      }
    }
  }

  await walk(rootDir);
  return files;
}

async function searchUrsManual(message, maxSnippets = 5) {
  const tokens = buildQueryTokens(message);
  if (!tokens.length) {
    return [];
  }

  const mdFiles = await collectMarkdownFiles(URS_MANUAL_DIR);
  const ranked = [];

  for (const filePath of mdFiles) {
    let content = '';
    try {
      content = await fs.promises.readFile(filePath, 'utf8');
    } catch {
      continue;
    }

    const sections = chunkMarkdownBySection(content);
    for (const section of sections) {
      const score = scoreTextByTokens(section.text, tokens);
      if (score <= 0) {
        continue;
      }
      ranked.push({
        filePath: path.relative(__dirname, filePath),
        header: section.header,
        score,
        snippet: section.text.slice(0, 700).trim()
      });
    }
  }

  return ranked
    .sort((a, b) => b.score - a.score || a.filePath.localeCompare(b.filePath))
    .slice(0, maxSnippets);
}

async function appendMemory(entry) {
  await fs.promises.mkdir(AGENT_MEMORY_DIR, { recursive: true });
  await fs.promises.appendFile(AGENT_MEMORY_PATH, `${JSON.stringify(entry)}\n`, 'utf8');
}

async function loadMemoryEntries() {
  try {
    const raw = await fs.promises.readFile(AGENT_MEMORY_PATH, 'utf8');
    return raw
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch {
          return null;
        }
      })
      .filter(Boolean);
  } catch {
    return [];
  }
}

function scoreMemory(entry, tokens) {
  const haystack = `${entry.message || ''} ${entry.reply || ''}`.toLowerCase();
  if (!haystack) {
    return 0;
  }

  let score = 0;
  for (const token of tokens) {
    if (token && haystack.includes(token)) {
      score += 1;
    }
  }
  return score;
}

async function searchMemory(query, sessionId, clientIp, limit = 4) {
  const entries = await loadMemoryEntries();
  const ip = normalizeClientIp(clientIp);
  const tokens = String(query || '')
    .toLowerCase()
    .split(/[\s,，。；;:：/]+/)
    .map((token) => token.trim())
    .filter((token) => token.length >= 2)
    .slice(0, 12);

  const ranked = entries
    .filter((entry) => normalizeClientIp(entry.clientIp) === ip)
    .map((entry) => ({
      entry,
      score: scoreMemory(entry, tokens) + (entry.sessionId === sessionId ? 0.5 : 0)
    }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || String(b.entry.timestamp).localeCompare(String(a.entry.timestamp)))
    .slice(0, limit)
    .map((item) => item.entry);

  return ranked;
}

function stripUnsupportedMeasurements(items, sourceMessage) {
  const source = String(sourceMessage || '');
  const hasExplicitMeasurements = /(mm|cm|毫米|厘米|公差|±|°|度)/i.test(source);
  if (hasExplicitMeasurements) {
    return items;
  }

  return items.filter(
    (item) => !/(\d+\s*(mm|cm|毫米|厘米|°|度))|±|\b公差\b/i.test(item)
  );
}

function normalizeAnalysis(payload, fallbackText = '', sourceMessage = '') {
  const summary = typeof payload?.summary === 'string' && payload.summary.trim()
    ? payload.summary.trim()
    : fallbackText || '未生成结构化总结。';

  const requirementAnalysis = stripUnsupportedMeasurements(
    normalizeStringList(payload?.requirement_analysis),
    sourceMessage
  );
  const solutionFramework = stripUnsupportedMeasurements(
    normalizeStringList(payload?.solution_framework),
    sourceMessage
  );
  const moduleDesign = stripUnsupportedMeasurements(
    normalizeStringList(payload?.module_design),
    sourceMessage
  );
  const validationDelivery = stripUnsupportedMeasurements(
    normalizeStringList(payload?.validation_delivery),
    sourceMessage
  );

  return {
    summary,
    requirement_analysis: requirementAnalysis.length
      ? requirementAnalysis.slice(0, 2)
      : ['补齐尺寸与边界条件'],
    solution_framework: solutionFramework.length
      ? solutionFramework.slice(0, 2)
      : ['先确定整体布局与模块关系'],
    module_design: moduleDesign.length
      ? moduleDesign.slice(0, 2)
      : ['细化支架、孔位与布局结构'],
    validation_delivery: validationDelivery.length
      ? validationDelivery.slice(0, 2)
      : ['打印验证并确认交付物']
  };
}

function parseJsonResponse(text) {
  const trimmed = String(text || '').trim();
  if (!trimmed) {
    return null;
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
    if (fenced?.[1]) {
      try {
        return JSON.parse(fenced[1].trim());
      } catch {
        return null;
      }
    }
  }

  return null;
}

function extractCodeBlock(text) {
  const raw = String(text || '').trim();
  if (!raw) {
    return '';
  }

  const fenced = raw.match(/```(?:python|py)?\s*([\s\S]*?)```/i);
  return fenced?.[1]?.trim() || raw;
}

function looksLikeFreecadPython(code) {
  const text = String(code || '');
  return /import\s+FreeCAD\s+as\s+App/.test(text) && /\bPart\b/.test(text);
}

function parseRequestedCubeSizeMm(message) {
  const text = String(message || '').toLowerCase();
  const cmMatch = text.match(/(\d+(?:\.\d+)?)\s*(cm|厘米)/i);
  if (cmMatch) {
    return Number.parseFloat(cmMatch[1]) * 10;
  }
  const mmMatch = text.match(/(\d+(?:\.\d+)?)\s*(mm|毫米)/i);
  if (mmMatch) {
    return Number.parseFloat(mmMatch[1]);
  }
  return null;
}

function buildFallbackCubeScript(message) {
  const sizeMm = parseRequestedCubeSizeMm(message);
  const edge = Number.isFinite(sizeMm) && sizeMm > 0 ? sizeMm : 20;
  return `import FreeCAD as App
import Part

doc = App.newDocument("GeneratedCube")
cube = doc.addObject("Part::Feature", "Cube")
cube.Shape = Part.makeBox(${edge}, ${edge}, ${edge})
doc.recompute()
`;
}

function canFallbackToCube(message) {
  const text = String(message || '').toLowerCase();
  return /立方体|cube/.test(text);
}

function makeSlug(value, fallback = 'generated_freecad_assembly') {
  const base = String(value || '')
    .replace(/\.[^.]+$/, '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
  return base || fallback;
}

function buildPublicModelEntry(stepPath) {
  const fileName = path.basename(stepPath);
  return {
    fileName,
    url: `/models/step/${encodeURIComponent(fileName)}`
  };
}

function resolveModelFilePath(fileName) {
  const rawName = String(fileName || '');
  const decodedName = decodeURIComponent(rawName);
  const safeName = path.basename(decodedName);
  if (!safeName || safeName !== decodedName) {
    return null;
  }
  if (!/\.(step|stp)$/i.test(safeName)) {
    return null;
  }
  const filePath = path.join(MODELS_DIR, safeName);
  if (!fs.existsSync(filePath)) {
    return null;
  }
  return {
    fileName: safeName,
    filePath
  };
}

function buildModelHeaders() {
  const headers = {
    'Content-Type': 'application/json'
  };

  if (LLM_API_KEY && LLM_PROVIDER !== 'ollama') {
    headers.Authorization = `Bearer ${LLM_API_KEY}`;
  }

  return headers;
}

async function fetchModelCatalog() {
  if (LLM_PROVIDER === 'ollama') {
    const response = await fetch(`${LLM_BASE_URL}/api/tags`, {
      headers: buildModelHeaders(),
      signal: AbortSignal.timeout(Math.min(LLM_TIMEOUT_MS, 15000))
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.error || `Model catalog request failed: ${response.status}`);
    }

    return Array.isArray(payload?.models)
      ? payload.models.map((item) => item?.name || item?.model).filter(Boolean)
      : [];
  }

  const response = await fetch(`${LLM_BASE_URL}/models`, {
    headers: buildModelHeaders(),
    signal: AbortSignal.timeout(Math.min(LLM_TIMEOUT_MS, 15000))
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.error?.message || payload?.error || `Model catalog request failed: ${response.status}`);
  }

  return Array.isArray(payload?.data)
    ? payload.data.map((item) => item?.id || item?.model).filter(Boolean)
    : [];
}

async function resolvePreferredChatModel() {
  if (CHAT_LLM_MODEL) {
    return CHAT_LLM_MODEL;
  }

  if (!preferredChatModelPromise) {
    preferredChatModelPromise = (async () => {
      try {
        const models = await fetchModelCatalog();
        const doubaoModel = models.find((model) => /doubao/i.test(String(model)));
        return doubaoModel || LLM_MODEL;
      } catch {
        return LLM_MODEL;
      }
    })();
  }

  return preferredChatModelPromise;
}

async function resolveModelForPurpose(purpose = 'default') {
  if (purpose === 'chat') {
    return resolvePreferredChatModel();
  }

  if (purpose === 'codegen') {
    return CODEGEN_LLM_MODEL;
  }

  return LLM_MODEL;
}

async function callLlm(messages, options = {}) {
  const {
    purpose = 'default',
    responseFormat = null,
    temperature = 0.2
  } = options;
  const model = await resolveModelForPurpose(purpose);

  if (LLM_PROVIDER === 'ollama') {
    const response = await fetch(`${LLM_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: buildModelHeaders(),
      body: JSON.stringify({
        model,
        stream: false,
        think: false,
        messages
      }),
      signal: AbortSignal.timeout(LLM_TIMEOUT_MS)
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.error || `LLM request failed: ${response.status}`);
    }

    return {
      model,
      content: payload?.message?.content || ''
    };
  }

  const body = {
    model,
    messages,
    temperature
  };

  if (responseFormat) {
    body.response_format = responseFormat;
  }

  const sendChatCompletion = async (requestBody) => {
    const response = await fetch(`${LLM_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: buildModelHeaders(),
      body: JSON.stringify(requestBody),
      signal: AbortSignal.timeout(LLM_TIMEOUT_MS)
    });
    const payload = await response.json().catch(() => ({}));
    return { response, payload };
  };

  let { response, payload } = await sendChatCompletion(body);
  if (!response.ok && responseFormat) {
    const errorMessage = String(payload?.error?.message || payload?.error || '').toLowerCase();
    const unsupportedResponseFormat =
      errorMessage.includes('response_format') && errorMessage.includes('not supported');
    if (unsupportedResponseFormat) {
      const fallbackBody = { ...body };
      delete fallbackBody.response_format;
      ({ response, payload } = await sendChatCompletion(fallbackBody));
    }
  }

  if (!response.ok) {
    throw new Error(payload?.error?.message || payload?.error || `LLM request failed: ${response.status}`);
  }

  return {
    model,
    content: payload?.choices?.[0]?.message?.content || ''
  };
}

async function analyzeModelRequest(message) {
  if (!isProjectDomainQuestion(message)) {
    return {
      summary: DOMAIN_REJECTION_MESSAGE,
      requirement_analysis: [],
      solution_framework: [],
      module_design: [],
      validation_delivery: []
    };
  }

  const { model, content } = await callLlm([
    {
      role: 'system',
      content: MODEL_ANALYSIS_PROMPT
    },
    {
      role: 'user',
      content: message
    }
  ], {
    purpose: 'chat',
    responseFormat: { type: 'json_object' },
    temperature: 0.1
  });
  const parsed = parseJsonResponse(content);
  return {
    model,
    analysis: normalizeAnalysis(parsed, content.trim(), message)
  };
}

function normalizeFreecadCodegen(payload, fallbackText = '') {
  const summary = typeof payload?.summary === 'string' && payload.summary.trim()
    ? payload.summary.trim()
    : '已生成 FreeCAD 装配脚本草案。';
  const fileName = typeof payload?.file_name === 'string' && payload.file_name.trim()
    ? payload.file_name.trim().replace(/[^\w.-]+/g, '_')
    : DEFAULT_FREECAD_SCRIPT_NAME;
  const assumptions = normalizeStringList(payload?.assumptions).slice(0, 8);
  const payloadCode = typeof payload?.code === 'string' ? payload.code : '';
  const extractedPayloadCode = extractCodeBlock(payloadCode);
  let code = extractedPayloadCode;

  if (!code && looksLikeFreecadPython(fallbackText)) {
    code = extractCodeBlock(fallbackText);
  }

  if (!code) {
    throw new Error('模型未返回可用的 FreeCAD 代码。');
  }

  return {
    summary,
    file_name: fileName.endsWith('.py') ? fileName : `${fileName}.py`,
    assumptions,
    code
  };
}

function normalizeAgentResponse(payload, fallbackText = '', message = '') {
  const reply = typeof payload?.reply === 'string' && payload.reply.trim()
    ? payload.reply.trim()
    : fallbackText || '已处理你的请求。';

  const steps = Array.isArray(payload?.steps)
    ? payload.steps
      .map((step) => ({
        title: typeof step?.title === 'string' ? step.title.trim() : '',
        items: normalizeStringList(step?.items).slice(0, 4)
      }))
      .filter((step) => step.title)
      .slice(0, 4)
    : [];

  let action = payload?.action === 'generate_freecad' ? 'generate_freecad' : 'respond';
  const generatePrompt = typeof payload?.generate_prompt === 'string' && payload.generate_prompt.trim()
    ? payload.generate_prompt.trim()
    : message;

  if (!generatePrompt && action === 'generate_freecad') {
    action = 'respond';
  }

  return {
    reply,
    steps,
    action,
    generate_prompt: generatePrompt
  };
}

async function runAgentTurn({
  sessionId,
  message,
  selectedSkillIds = [],
  memoryEnabled = true,
  clientIp = 'unknown',
  wordContext = '',
  wordFileName = ''
}) {
  const { session, clientIp: normalizedIp } = ensureSession(sessionId, clientIp);
  const normalizedWordContext = typeof wordContext === 'string' ? wordContext.trim() : '';
  const wordContextForSearch = normalizedWordContext.slice(0, 4000);
  const ursQuery = [message, wordContextForSearch].filter(Boolean).join('\n');
  const ursSnippets = await searchUrsManual(ursQuery);
  const skills = await listSkills();
  const runtimeSkillIds = ['urs-manual', ...(normalizedWordContext ? ['word-parser'] : [])];
  const runtimeSkills = skills.filter((skill) => runtimeSkillIds.includes(skill.id));
  if (!ursSnippets.length) {
    const rejectedReply = URS_OUT_OF_SCOPE_MESSAGE;
    session.messages.push(
      { role: 'user', content: message },
      { role: 'assistant', content: rejectedReply }
    );
    session.messages = session.messages.slice(-20);

    if (memoryEnabled) {
      await appendMemory({
        sessionId,
        clientIp: normalizedIp,
        timestamp: new Date().toISOString(),
        message,
        reply: rejectedReply,
        skills: runtimeSkillIds
      });
    }

    return {
      reply: rejectedReply,
      steps: [],
      action: 'respond',
      artifact: null,
      modelEntry: null,
      invokedSkills: runtimeSkillIds
    };
  }

  const { model, content } = await callLlm([
    {
      role: 'system',
      content: `${AGENT_SYSTEM_PROMPT}

额外硬约束（最高优先级）：
- 你只能使用 URS-MANUAL 检索内容回答，不得使用 memory、skills 或通用知识补充。
- 若检索内容不足以支持答案，reply 必须返回：${URS_OUT_OF_SCOPE_MESSAGE}
- action 必须是 "respond"，generate_prompt 必须为空字符串。`
    },
    {
      role: 'system',
      content: `URS-MANUAL 检索:\n${ursSnippets.map((item, index) => `${index + 1}. 来源: ${item.filePath} ${item.header}\n${item.snippet}`).join('\n\n')}`
    },
    {
      role: 'system',
      content: runtimeSkills.length
        ? `Runtime skills:\n${runtimeSkills.map((skill) => `## ${skill.id}\n${skill.content}`).join('\n\n')}`
        : 'Runtime skills: 无'
    },
    ...(normalizedWordContext
      ? [{
        role: 'system',
        content: `用户上传文档(${String(wordFileName || 'word').trim() || 'word'})解析内容（仅作为用户需求输入）:\n${normalizedWordContext.slice(0, 12000)}`
      }]
      : []),
    {
      role: 'user',
      content: message
    }
  ], {
    purpose: 'chat',
    responseFormat: { type: 'json_object' },
    temperature: 0.2
  });

  const parsed = parseJsonResponse(content);
  const normalized = normalizeAgentResponse(parsed, content.trim(), message);
  const result = {
    reply: normalized.reply || URS_OUT_OF_SCOPE_MESSAGE,
    steps: normalized.steps,
    action: 'respond',
    artifact: null,
    modelEntry: null
  };

  session.messages.push(
    { role: 'user', content: message },
    { role: 'assistant', content: result.reply }
  );
  session.messages = session.messages.slice(-20);

    if (memoryEnabled) {
      await appendMemory({
      sessionId,
      clientIp: normalizedIp,
      timestamp: new Date().toISOString(),
      message,
      reply: result.reply,
        skills: runtimeSkillIds
      });
    }

    return {
      ...result,
      model,
      invokedSkills: runtimeSkillIds
    };
}

async function generateFreecadCode(message) {
  if (!isProjectDomainQuestion(message)) {
    throw new Error(DOMAIN_REJECTION_MESSAGE);
  }

  const referenceScript = await fs.promises.readFile(FREECAD_REFERENCE_SCRIPT, 'utf8');
  const availableSkills = await listSkills();
  const stepGenerationSkill = availableSkills.find((skill) => skill.id === 'step-generation');
  let lastError = null;
  let resolvedModel = '';
  const attemptPrompts = [
    message,
    `${message}\n\n必须输出有效 JSON；code 必须是可执行 FreeCAD Python，且包含 "import FreeCAD as App" 与 "import Part"。`
  ];

  for (const prompt of attemptPrompts) {
    try {
      const { model, content } = await callLlm([
        {
          role: 'system',
          content: FREECAD_CODEGEN_PROMPT
        },
        ...(stepGenerationSkill?.content
          ? [{
            role: 'system',
            content: `STEP generation skill guidance:\n${stepGenerationSkill.content}`
          }]
          : []),
        {
          role: 'user',
          content: [
            '用户需求：',
            prompt,
            '',
            '参考脚本（风格参考，不要逐字照抄）：',
            referenceScript
          ].join('\n')
        }
      ], {
        purpose: 'codegen',
        responseFormat: { type: 'json_object' },
        temperature: 0.2
      });
      resolvedModel = model;
      const parsed = parseJsonResponse(content);
      const artifact = normalizeFreecadCodegen(parsed, content.trim());
      if (!looksLikeFreecadPython(artifact.code)) {
        throw new Error('Generated code is not valid FreeCAD script.');
      }
      return {
        model,
        artifact
      };
    } catch (error) {
      lastError = error;
    }
  }

  if (canFallbackToCube(message)) {
    return {
      model: resolvedModel || CODEGEN_LLM_MODEL,
      artifact: {
        summary: '模型生成不稳定，已使用立方体兜底脚本完成建模。',
        file_name: 'fallback_cube.py',
        assumptions: ['使用兜底脚本生成基础立方体。'],
        code: buildFallbackCubeScript(message)
      }
    };
  }

  throw lastError || new Error('Model did not return valid FreeCAD python code.');
}

function buildFreecadRunnerScript() {
  return `# -*- coding: utf-8 -*-
import os
import sys
import traceback

import FreeCAD as App
import Import


GENERATED_SCRIPT_PATH = os.environ["GENERATED_SCRIPT_PATH"]
OUTPUT_STEP_PATH = os.environ["OUTPUT_STEP_PATH"]
OUTPUT_FCSTD_PATH = os.environ["OUTPUT_FCSTD_PATH"]


def close_all_documents():
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)


def get_exportable_objects(document):
    exportable = []
    for obj in document.Objects:
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        try:
            if shape.isNull():
                continue
        except Exception:
            continue
        exportable.append(obj)
    return exportable


def main():
    close_all_documents()
    script_dir = os.path.dirname(GENERATED_SCRIPT_PATH)
    if script_dir and script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    os.chdir(script_dir or os.getcwd())

    namespace = {
        "__name__": "__main__",
        "__file__": GENERATED_SCRIPT_PATH,
    }
    with open(GENERATED_SCRIPT_PATH, "r", encoding="utf-8") as handle:
        source = handle.read()
    exec(compile(source, GENERATED_SCRIPT_PATH, "exec"), namespace, namespace)

    document = App.ActiveDocument
    if document is None:
        docs = App.listDocuments()
        if docs:
            document = docs[list(docs.keys())[-1]]
    if document is None:
        raise RuntimeError("Generated script did not create a FreeCAD document.")

    document.recompute()
    os.makedirs(os.path.dirname(OUTPUT_FCSTD_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_STEP_PATH), exist_ok=True)
    document.saveAs(OUTPUT_FCSTD_PATH)

    exportable = get_exportable_objects(document)
    if not exportable:
        raise RuntimeError("Generated document has no exportable shapes.")
    Import.export(exportable, OUTPUT_STEP_PATH)

    print("RUNNER_OK")
    print("ACTIVE_DOC", document.Name)
    print("FCSTD_PATH", OUTPUT_FCSTD_PATH)
    print("STEP_PATH", OUTPUT_STEP_PATH)
    print("EXPORTED_COUNT", len(exportable))


try:
    main()
except Exception as error:
    print("RUNNER_ERROR", str(error))
    traceback.print_exc()
    raise
`;
}

async function ensureFreecadRunner() {
  const runnerScript = buildFreecadRunnerScript();
  if (typeof runnerScript !== 'string' || !runnerScript.trim()) {
    throw new Error('FreeCAD runner script is empty.');
  }
  await fs.promises.writeFile(FREECAD_RUNNER_PATH, runnerScript, 'utf8');
}

async function cleanupGeneratedFilesOlderThanOneDay() {
  const now = Date.now();
  const cutoff = now - GENERATED_FILE_RETENTION_MS;
  const deleted = {
    step: 0,
    script: 0
  };

  async function cleanupDirectory(dirPath, isTargetFile, counterKey) {
    let entries = [];
    try {
      entries = await fs.promises.readdir(dirPath, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      if (!entry.isFile()) {
        continue;
      }
      if (!isTargetFile(entry.name)) {
        continue;
      }

      const fullPath = path.join(dirPath, entry.name);
      let stat = null;
      try {
        stat = await fs.promises.stat(fullPath);
      } catch {
        continue;
      }
      if (stat.mtimeMs > cutoff) {
        continue;
      }

      try {
        await fs.promises.unlink(fullPath);
        deleted[counterKey] += 1;
      } catch {
        // ignore cleanup failures to avoid blocking main workflow
      }
    }
  }

  await cleanupDirectory(
    GENERATED_STEP_DIR,
    (name) => /\.(step|stp)$/i.test(name) && /_\d{14}\.(step|stp)$/i.test(name),
    'step'
  );
  await cleanupDirectory(
    GENERATED_SCRIPT_DIR,
    (name) => /\.py$/i.test(name) && /_\d{14}\.py$/i.test(name) && !PROTECTED_FREECAD_SCRIPT_FILES.has(name),
    'script'
  );

  return deleted;
}

async function runGeneratedFreecadArtifact(artifact) {
  await cleanupGeneratedFilesOlderThanOneDay();
  await fs.promises.mkdir(GENERATED_SCRIPT_DIR, { recursive: true });
  await fs.promises.mkdir(GENERATED_FCSTD_DIR, { recursive: true });
  await fs.promises.mkdir(GENERATED_STEP_DIR, { recursive: true });
  await ensureFreecadRunner();

  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14);
  const slug = makeSlug(artifact.file_name);
  const baseName = `${slug}_${stamp}`;
  const scriptPath = path.join(GENERATED_SCRIPT_DIR, `${baseName}.py`);
  const fcstdPath = path.join(GENERATED_FCSTD_DIR, `${baseName}.FCStd`);
  const stepPath = path.join(GENERATED_STEP_DIR, `${baseName}.step`);

  const generatedCode = typeof artifact?.code === 'string' ? artifact.code : '';
  if (!generatedCode.trim()) {
    const summary = typeof artifact?.summary === 'string' ? artifact.summary : '';
    throw new Error(`Generated FreeCAD code is empty. summary=${summary || 'n/a'}`);
  }
  await fs.promises.writeFile(scriptPath, generatedCode, 'utf8');

  let stdout = '';
  let stderr = '';
  const startedAt = Date.now();
  try {
    const result = await execFileAsync(FREECAD_CMD, [FREECAD_RUNNER_PATH], {
      cwd: __dirname,
      env: {
        ...process.env,
        PYTHONIOENCODING: process.env.PYTHONIOENCODING || 'utf-8',
        LANG: process.env.LANG || 'en_US.UTF-8',
        LC_ALL: process.env.LC_ALL || 'en_US.UTF-8',
        GENERATED_SCRIPT_PATH: scriptPath,
        OUTPUT_FCSTD_PATH: fcstdPath,
        OUTPUT_STEP_PATH: stepPath
      },
      timeout: Math.max(LLM_TIMEOUT_MS, 120000),
      maxBuffer: 8 * 1024 * 1024
    });
    stdout = result.stdout;
    stderr = result.stderr;
  } catch (error) {
    const details = [error.stdout, error.stderr]
      .filter(Boolean)
      .join('\n')
      .trim();
    throw new Error(details || error.message || 'FreeCAD export failed.');
  }

  async function pickLatestGeneratedFile(dirPath, extension, minMtimeMs) {
    try {
      const entries = await fs.promises.readdir(dirPath, { withFileTypes: true });
      const candidates = [];
      for (const entry of entries) {
        if (!entry.isFile() || !entry.name.toLowerCase().endsWith(extension)) {
          continue;
        }
        const fullPath = path.join(dirPath, entry.name);
        const stat = await fs.promises.stat(fullPath);
        if (stat.mtimeMs >= minMtimeMs - 2000) {
          candidates.push({ fullPath, mtimeMs: stat.mtimeMs });
        }
      }
      candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
      return candidates[0]?.fullPath || '';
    } catch {
      return '';
    }
  }

  async function ensureArtifactFile(targetPath, extension, { required = true } = {}) {
    try {
      await fs.promises.access(targetPath, fs.constants.F_OK);
      return;
    } catch {
      // continue to fallback path
    }

    const fallbackDirs = [path.join(GENERATED_SCRIPT_DIR, 'output'), GENERATED_SCRIPT_DIR];
    let fallbackSource = '';
    for (const dirPath of fallbackDirs) {
      fallbackSource = await pickLatestGeneratedFile(dirPath, extension, startedAt);
      if (fallbackSource) {
        break;
      }
      if (extension === '.step') {
        fallbackSource = await pickLatestGeneratedFile(dirPath, '.stp', startedAt);
        if (fallbackSource) {
          break;
        }
      }
    }
    if (fallbackSource) {
      await fs.promises.copyFile(fallbackSource, targetPath);
      return;
    }

    if (required) {
      throw new Error(
        `Generated artifact missing: ${targetPath}. stdout=${stdout.trim() || 'n/a'} stderr=${stderr.trim() || 'n/a'}`
      );
    }
  }

  await ensureArtifactFile(stepPath, '.step', { required: true });
  await ensureArtifactFile(fcstdPath, '.fcstd', { required: false });

  return {
    ...artifact,
    script_path: scriptPath,
    fcstd_path: fcstdPath,
    step_path: stepPath,
    model_entry: buildPublicModelEntry(stepPath),
    freecad_stdout: stdout.trim(),
    freecad_stderr: stderr.trim()
  };
}

async function extractWordText(filePath) {
  let skillError = null;
  try {
    if (!pythonUserSitePromise) {
      pythonUserSitePromise = execFileAsync(
        'python3',
        ['-c', 'import site; print(site.getusersitepackages())'],
        {
          cwd: __dirname,
          timeout: 15000,
          maxBuffer: 1024 * 1024
        }
      )
        .then(({ stdout }) => String(stdout || '').trim())
        .catch(() => '');
    }
    const pythonUserSite = await pythonUserSitePromise;
    const envPythonPath = process.env.PYTHONPATH || '';
    const pythonPath = [pythonUserSite, envPythonPath].filter(Boolean).join(':');
    const { stdout, stderr } = await execFileAsync('python3', [DOCX_EXTRACTOR_SCRIPT, filePath], {
      cwd: __dirname,
      env: {
        ...process.env,
        ...(pythonPath ? { PYTHONPATH: pythonPath } : {})
      },
      timeout: 120000,
      maxBuffer: 8 * 1024 * 1024
    });
    if (stderr?.trim()) {
      console.warn(stderr.trim());
    }
    const text = String(stdout || '').trim();
    if (text) {
      return text;
    }
    skillError = new Error('Word skill returned empty output.');
  } catch (error) {
    const details = [error.stdout, error.stderr]
      .filter(Boolean)
      .join('\n')
      .trim();
    skillError = new Error(details || error.message || 'Word skill parse failed.');
  }

  try {
    const { value } = await mammoth.extractRawText({ path: filePath });
    const text = String(value || '').trim();
    if (text) {
      return text;
    }
    throw new Error('Fallback parser returned empty output.');
  } catch (fallbackError) {
    throw new Error(
      `Word document parse failed. skill_error=${skillError?.message || 'unknown'}; fallback_error=${fallbackError.message}`
    );
  }
}

app.use(express.json());
app.use('/models/step', express.static(MODELS_DIR));

app.get('/api/health', (_req, res) => {
  res.json({
    ok: true,
    renderer: 'three.js/vue',
    importer: 'occt-import-js/vite',
    modelsDir: MODELS_DIR,
    freecadCmd: FREECAD_CMD,
    chatModel: CHAT_LLM_MODEL || 'auto:doubao-or-default',
    codegenModel: CODEGEN_LLM_MODEL,
    llmProvider: LLM_PROVIDER,
    llmBaseUrl: LLM_BASE_URL
  });
});

app.get('/api/agent/config', async (_req, res, next) => {
  try {
    const skills = await listSkills();
    const chatModel = await resolveModelForPurpose('chat');
    res.json({
      ok: true,
      provider: LLM_PROVIDER,
      model: chatModel,
      memoryEnabledByDefault: true,
      skills: skills.map((skill) => ({
        id: skill.id,
        title: skill.title
      }))
    });
  } catch (error) {
    next(error);
  }
});

app.get('/api/models', async (_req, res, next) => {
  try {
    const { readdir } = await import('node:fs/promises');
    const entries = await readdir(MODELS_DIR, { withFileTypes: true });
    const models = entries
      .filter((entry) => entry.isFile() && /\.(step|stp)$/i.test(entry.name))
      .map((entry) => ({
        fileName: entry.name,
        url: `/models/step/${encodeURIComponent(entry.name)}`
      }))
      .sort((a, b) => a.fileName.localeCompare(b.fileName));

    res.json({ models });
  } catch (error) {
    next(error);
  }
});

app.get('/api/models/:fileName/download', (req, res) => {
  const resolved = resolveModelFilePath(req.params.fileName);
  if (!resolved) {
    res.status(404).json({ error: '模型文件不存在。' });
    return;
  }

  res.download(resolved.filePath, resolved.fileName);
});

app.post('/chat', async (req, res, next) => {
  try {
    const message = typeof req.body?.message === 'string' ? req.body.message.trim() : '';
    if (!message) {
      res.status(400).json({
        error: 'message is required'
      });
      return;
    }

    const { model, analysis } = await analyzeModelRequest(message);
    res.json({
      ok: true,
      model,
      analysis
    });
  } catch (error) {
    next(error);
  }
});

app.post('/api/freecad/generate', async (req, res, next) => {
  try {
    const message = typeof req.body?.message === 'string' ? req.body.message.trim() : '';
    if (!message) {
      res.status(400).json({
        error: 'message is required'
      });
      return;
    }

    const { model, artifact: generated } = await generateFreecadCode(message);
    const artifact = await runGeneratedFreecadArtifact(generated);
    res.json({
      ok: true,
      model,
      artifact,
      modelEntry: artifact.model_entry
    });
  } catch (error) {
    next(error);
  }
});

app.post('/api/agent/chat', async (req, res, next) => {
  try {
    const message = typeof req.body?.message === 'string' ? req.body.message.trim() : '';
    if (!message) {
      res.status(400).json({
        error: 'message is required'
      });
      return;
    }

    const sessionId = typeof req.body?.sessionId === 'string' ? req.body.sessionId.trim() : '';
    const wordContext = typeof req.body?.wordContext === 'string' ? req.body.wordContext : '';
    const wordFileName = typeof req.body?.wordFileName === 'string' ? req.body.wordFileName : '';
    const clientIp = getClientIp(req);
    const selectedSkills = Array.isArray(req.body?.skills)
      ? req.body.skills.filter((item) => typeof item === 'string' && item.trim()).map((item) => item.trim())
      : [];
    const memoryEnabled = req.body?.memoryEnabled !== false;

    const { sessionId: resolvedSessionId } = ensureSession(sessionId, clientIp);
    const result = await runAgentTurn({
      sessionId: resolvedSessionId,
      clientIp,
      message,
      wordContext,
      wordFileName,
      selectedSkillIds: selectedSkills,
      memoryEnabled
    });

    res.json({
      ok: true,
      sessionId: resolvedSessionId,
      model: result.model,
      provider: LLM_PROVIDER,
      ...result
    });
  } catch (error) {
    next(error);
  }
});

app.post('/api/word/parse', upload.single('file'), async (req, res, next) => {
  const uploadedPath = req.file?.path;
  try {
    if (!req.file) {
      res.status(400).json({ error: 'file is required' });
      return;
    }

    const originalName = req.file.originalname || 'upload.docx';
    if (!/\.docx$/i.test(originalName)) {
      res.status(400).json({ error: 'Only .docx files are supported.' });
      return;
    }

    const text = await extractWordText(uploadedPath);
    res.json({
      ok: true,
      fileName: originalName,
      charCount: text.length,
      text
    });
  } catch (error) {
    next(error);
  } finally {
    if (uploadedPath) {
      fs.promises.unlink(uploadedPath).catch(() => {});
    }
  }
});

async function start() {
  await cleanupGeneratedFilesOlderThanOneDay();

  if (isProduction) {
    if (!fs.existsSync(path.join(DIST_DIR, 'index.html'))) {
      throw new Error('Missing dist/index.html. Run "npm run build" before starting production mode.');
    }

    app.use(express.static(DIST_DIR));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(DIST_DIR, 'index.html'));
    });
  } else {
    const { createServer } = await import('vite');
    const vite = await createServer({
      root: __dirname,
      appType: 'custom',
      server: {
        middlewareMode: true,
        host: HOST
      }
    });

    app.use(vite.middlewares);
    app.get('*', async (req, res, next) => {
      try {
        const template = await vite.transformIndexHtml(
          req.originalUrl,
          await fs.promises.readFile(path.join(__dirname, 'index.html'), 'utf8')
        );
        res.status(200).set({ 'Content-Type': 'text/html' }).end(template);
      } catch (error) {
        vite.ssrFixStacktrace(error);
        next(error);
      }
    });
  }

  app.use((error, _req, res, _next) => {
    const statusCode = error.statusCode || 500;
    res.status(statusCode).json({
      error: error.message || 'Unexpected server error.'
    });
  });

  app.listen(PORT, HOST, () => {
    console.log(`Viewer app listening on http://${HOST}:${PORT}`);
  });
}

start().catch((error) => {
  console.error(error);
  process.exit(1);
});
