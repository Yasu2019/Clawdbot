const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const { promisify } = require('util');
const execFileAsync = promisify(execFile);
const {
  fetchEmailContext,
  fetchEmailCount,
  fetchTaskContext,
  fetchComplaintContext,
  fetchReportContext,
  buildEmailAwarePrompt,
} = require(path.join(__dirname, '..', 'data', 'state', 'email_context_helper'));
const {
  buildModelRankingText,
  fetchInstalledOllamaModels,
  isModelRankingIntent,
} = require(path.join(__dirname, '..', 'data', 'state', 'model_ranking_helper'));

const repoRoot = path.resolve(__dirname, '..');
const stateDir = path.join(repoRoot, 'data', 'state', 'telegram_fast');
const statusFile = path.join(stateDir, 'harness_status.json');
const eventsFile = path.join(stateDir, 'events.log');
const offsetFile = path.join(stateDir, 'offset.json');
const pidFile = path.join(stateDir, 'bridge.pid');
const dbContextFile = path.join(stateDir, 'last_db_context.json');
const configFile = path.join(repoRoot, 'data', 'state', 'openclaw.json');

const ollamaUrl = (process.env.OLLAMA_URL || 'http://127.0.0.1:11434').replace(/\/$/, '');
const replyModel = process.env.TELEGRAM_FAST_MODEL || 'google/gemini-2.5-flash';
const replyApiBase = (process.env.TELEGRAM_FAST_API_BASE || 'http://127.0.0.1:4000/v1').replace(/\/$/, '');
const replyApiKey = process.env.TELEGRAM_FAST_API_KEY || process.env.OPENAI_API_KEY || 'none';
const MODEL_TIMEOUT_MS = Number(process.env.TELEGRAM_FAST_TIMEOUT_MS || 45000);
const ALLOWED_TELEGRAM_CHAT_ID = '8173025084';
// Escalation settings
const localModel = process.env.TELEGRAM_LOCAL_MODEL || 'qwen3:8b';
const AGENT_TIMEOUT_MS = Number(process.env.TELEGRAM_AGENT_TIMEOUT_MS || 120000);
const GATEWAY_CONTAINER = process.env.CLAWDBOT_GATEWAY_CONTAINER || 'clawstack-unified-clawdbot-gateway-1';

function usesOpenAiCompatibleRoute(modelName) {
  return /^(google|gemini|openai|anthropic|claude)\//i.test(modelName || '');
}

fs.mkdirSync(stateDir, { recursive: true });

function nowIso() {
  return new Date().toISOString();
}

function readJson(file, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

function writeStatus(state, extra = {}) {
  const current = fs.existsSync(statusFile) ? readJson(statusFile, {}) : {};
  if (!Object.prototype.hasOwnProperty.call(extra, 'lastError') && !/error|conflict/i.test(state)) {
    delete current.lastError;
  }
  if (!Object.prototype.hasOwnProperty.call(extra, 'progressStage')) {
    delete current.progressStage;
  }
  if (!Object.prototype.hasOwnProperty.call(extra, 'progressElapsedSec')) {
    delete current.progressElapsedSec;
  }
  if (!Object.prototype.hasOwnProperty.call(extra, 'existingPid')) {
    delete current.existingPid;
  }
  const payload = {
    ...current,
    service: 'telegram_fast_bridge',
    updatedAt: nowIso(),
    pid: process.pid,
    state,
    model: replyModel,
    ...extra,
  };
  fs.writeFileSync(statusFile, JSON.stringify(payload, null, 2));
}

function writeEvent(kind, data = {}) {
  const payload = {
    at: nowIso(),
    pid: process.pid,
    kind,
    ...data,
  };
  fs.appendFileSync(eventsFile, `${JSON.stringify(payload)}\n`);
}

function saveDbContext(payload) {
  fs.writeFileSync(dbContextFile, JSON.stringify({
    updatedAt: nowIso(),
    ...payload,
  }, null, 2));
}

function loadDbContext() {
  return readJson(dbContextFile, null);
}

function assertAllowedTelegramChatId(chatId, source) {
  const normalized = String(chatId || '').trim();
  if (normalized !== ALLOWED_TELEGRAM_CHAT_ID) {
    writeEvent('telegram_send_blocked', {
      source,
      requestedChatId: normalized,
      allowedChatId: ALLOWED_TELEGRAM_CHAT_ID,
    });
    throw new Error(`[SECURITY POLICY] blocked Telegram chat_id for ${source}: ${normalized}`);
  }
  return ALLOWED_TELEGRAM_CHAT_ID;
}

function loadOffset() {
  if (!fs.existsSync(offsetFile)) return null;
  const parsed = readJson(offsetFile, {});
  return Number.isFinite(Number(parsed.lastUpdateId)) ? Number(parsed.lastUpdateId) : null;
}

function saveOffset(updateId) {
  fs.writeFileSync(offsetFile, JSON.stringify({
    version: 1,
    lastUpdateId: updateId,
    updatedAt: nowIso(),
  }, null, 2));
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function processExists(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function acquireLock() {
  if (fs.existsSync(pidFile)) {
    const existingPid = Number(fs.readFileSync(pidFile, 'utf8').trim() || '0');
    if (existingPid > 0 && processExists(existingPid)) {
      writeStatus('already_running', { existingPid });
      process.exit(0);
    }
  }
  fs.writeFileSync(pidFile, String(process.pid), 'ascii');
}

function releaseLock() {
  if (!fs.existsSync(pidFile)) return;
  try {
    const existingPid = Number(fs.readFileSync(pidFile, 'utf8').trim() || '0');
    if (existingPid === process.pid) {
      fs.rmSync(pidFile, { force: true });
    }
  } catch {
  }
}


function loadHistory(chatId) {
  const file = path.join(stateDir, `history_${chatId}.json`);
  if (!fs.existsSync(file)) return [];
  return readJson(file, []);
}

function saveHistory(chatId, history) {
  const file = path.join(stateDir, `history_${chatId}.json`);
  fs.writeFileSync(file, JSON.stringify(history.slice(-12), null, 2));
}

function formatHistoryBlock(history) {
  if (!history || history.length === 0) return [];
  return [
    '=== 会話履歴 (Conversation Context) ===',
    ...history.map(m => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`),
    '========================',
    ''
  ];
}

function buildStackStatusText() {
  return [
    'telegram_fast_bridge status',
    `reply_model=${replyModel}`,
    `reply_backend=${usesOpenAiCompatibleRoute(replyModel) ? 'litellm-openai' : 'ollama-generate'}`,
    'router=commands-local_context-aware',
    'task_search=sqlite tasks-context',
    'email_search=sqlite email context',
    'telegram_path=general-direct-model',
  ].join('\n');
}

async function getFastReply(text) {
  const trimmed = (text || '').trim();
  if (!trimmed) return 'メッセージを送ってください。';
  if (/^ping$/i.test(trimmed)) return 'pong';
  if (/^\/status$/i.test(trimmed)) return buildStackStatusText();
  if (/^(おはよう|おはようございます|こんにちは|こんばんは|ありがとう|ありがと)$/i.test(trimmed)) {
    if (/ありがとう/.test(trimmed)) return 'どういたしまして。必要なことがあればそのまま送ってください。';
    return 'おはようございます。今日も確認できます。';
  }
  if (/天気|weather/i.test(trimmed)) {
    return '天気の外部取得はこのTelegram bridgeでは未接続です。地域名つきで送ってもらえれば、確認経路を切り替えて調べます。';
  }
  if (/^\/models$/i.test(trimmed) || /^\/rankings$/i.test(trimmed) || isModelRankingIntent(trimmed)) {
    const installedModels = await fetchInstalledOllamaModels(ollamaUrl);
    return `${buildStackStatusText()}\n\n${buildModelRankingText(installedModels)}`;
  }
  return null;
}

function getAckReply() {
  return '確認します。少し待ってください。';
}

function getProgressMessage(stage, elapsedSeconds) {
  const seconds = Math.max(0, Math.floor(elapsedSeconds));
  return `${stage}\n経過: ${seconds}秒\nモデル: ${replyModel}`;
}

function normalizeCompareText(text) {
  return (text || '').trim().toLowerCase().replace(/\s+/g, '');
}

function sanitizeModelReply(inputText, replyText) {
  const inputNorm = normalizeCompareText(inputText);
  const reply = (replyText || '').trim();
  const replyNorm = normalizeCompareText(reply);

  if (!reply) {
    return 'うまく応答を生成できませんでした。少し言い換えてもう一度送ってください。';
  }
  if (replyNorm === 'received' || replyNorm === 'received.') {
    return '受け取りました。内容をもう少し具体的に送ってください。';
  }
  if (inputNorm && replyNorm === inputNorm) {
    return '内容をそのまま繰り返さず、要点で答えてください。もう一度送るなら少し具体化してください。';
  }
  return reply;
}

function normalizeUserText(text) {
  return String(text || '')
    .normalize('NFKC')
    .replace(/\u3000/g, ' ')
    .trim();
}

function compactUserText(text) {
  return normalizeUserText(text).toLowerCase().replace(/\s+/g, '');
}

function hasAnyPattern(text, patterns) {
  return patterns.some((pattern) => pattern.test(text));
}

function extractContextTitles(context) {
  const rows = Array.isArray(context?.results) ? context.results : [];
  return rows
    .map((item) => String(item?.subject || item?.title || item?.name || '').trim())
    .filter(Boolean);
}

function uniqueStrings(values) {
  const seen = new Set();
  const result = [];
  for (const value of values) {
    const text = String(value || '').trim();
    if (!text) continue;
    const key = text.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(text);
  }
  return result;
}

function hasDbDomainHint(normalized, compact) {
  return hasAnyPattern(normalized, [
    /IATF/i,
    /ISO\s*9001/i,
    /ISO\s*16949/i,
    /QMS/i,
    /品質/,
    /監査/,
    /資料/,
    /文書/,
    /書類/,
    /帳票/,
    /記録/,
    /データベース/,
    /DB/,
  ]) || hasAnyPattern(compact, [
    /iatf/,
    /iso9001/,
    /iso16949/,
    /qms/,
    /db/,
  ]);
}

function hasDbSearchVerb(normalized, compact) {
  return hasAnyPattern(normalized, [
    /検索/,
    /探して/,
    /調べて/,
    /見つけて/,
    /教えて/,
    /見せて/,
    /出して/,
    /一覧/,
    /リスト/,
    /数えて/,
    /件数/,
    /何件/,
    /何個/,
    /どんな/,
    /何がある/,
    /あるか/,
    /ありますか/,
    /登録/,
    /保存/,
  ]) || hasAnyPattern(compact, [
    /search/,
    /find/,
    /count/,
    /list/,
    /howmany/,
    /whatisthere/,
  ]);
}

function looksLikeDbCountRequest(normalized, compact) {
  return hasAnyPattern(normalized, [
    /何件/,
    /件数/,
    /総数/,
    /何個/,
    /いくつ/,
    /数えて/,
    /数を数えて/,
    /資料数/,
    /文書数/,
    /書類数/,
    /件ありますか/,
    /件ある/,
  ]) || hasAnyPattern(compact, [
    /count/,
    /howmany/,
  ]);
}

function looksLikeDbListRequest(normalized, compact) {
  return hasAnyPattern(normalized, [
    /資料名/,
    /文書名/,
    /タイトル/,
    /一覧/,
    /リスト/,
    /内訳/,
    /どんな資料/,
    /どの資料/,
    /何がある/,
    /何が登録/,
    /代表資料/,
    /例を見せて/,
    /具体例/,
  ]) || hasAnyPattern(compact, [
    /titles/,
    /list/,
    /documents/,
  ]);
}

function looksLikeDbFollowupRequest(normalized, compact, hasDbContext) {
  if (!hasDbContext) return false;
  return hasAnyPattern(normalized, [
    /^それ$/,
    /^それは$/,
    /^これ$/,
    /^これで$/,
    /^その資料名は$/,
    /^資料名は$/,
    /^文書名は$/,
    /^タイトルは$/,
    /^一覧は$/,
    /^もっと$/,
    /^他には$/,
    /^ほかには$/,
    /^前の$/,
    /^さっきの$/,
    /^直前の$/,
    /^その$/,
    /^この$/,
  ]) || hasAnyPattern(compact, [
    /それは/,
    /これ/,
    /そのしりょうめいは/,
    /そのもんしょめいは/,
    /いちらんは/,
    /もっと/,
    /ほかには/,
    /さっきの/,
    /ちょくぜんの/,
  ]);
}

function normalizeUserIntent(text) {
  const normalized = normalizeUserText(text);
  const compact = compactUserText(text);
  const existingDbContext = loadDbContext();
  const hasDbContext = Boolean(
    existingDbContext &&
    Array.isArray(existingDbContext.titles) &&
    existingDbContext.titles.length > 0,
  );

  const countQuery = looksLikeDbCountRequest(normalized, compact);
  const listQuery = looksLikeDbListRequest(normalized, compact);
  const followupQuery = looksLikeDbFollowupRequest(normalized, compact, hasDbContext);
  const dbDomainHint = hasDbDomainHint(normalized, compact);
  const searchVerb = hasDbSearchVerb(normalized, compact);
  const taskIntent = /(?:タスク|依頼|やること|todo|task|deadline|締切|期限|未回答|約束|remind|follow up|納期|来週|今週|明日|今日まで|何まで|いつまで)/i.test(normalized)
    || /(?:deadline|due|task|todo|followup)/i.test(compact);
  const reportIntent = /(?:日報|レポート|AI Scout|trend ranking|promises|health check|ヘルスチェック|定期報告|scheduled report|週次報告|月次報告)/i.test(normalized)
    || /(?:aiscout|healthcheck|scheduledreport|dailyreport|trendranking)/i.test(compact);
  const complaintIntent = /(?:クレーム|complaint|不具合|密着不良|溶解異常|再発防止|市場不良|品質問題|顧客不良|不適合事例)/i.test(normalized);
  const emailIntent = /(?:メール|mail|gmail|eml|inbox|from:|to:|送信者|受信|返信|未読)/i.test(normalized)
    || /(?:mail|gmail|inbox|from:|to:)/i.test(compact);

  if ((countQuery || listQuery || followupQuery || (dbDomainHint && searchVerb)) && (dbDomainHint || hasDbContext || countQuery || listQuery || followupQuery)) {
    return {
      route: 'db',
      mode: countQuery ? 'count' : followupQuery ? 'followup' : 'list',
      normalized,
      compact,
      hasDbContext,
    };
  }

  if (taskIntent) {
    return {
      route: 'task',
      mode: /(?:納期|期限|締切|来週|今週|明日|今日まで|何まで|いつまで)/i.test(normalized) ? 'due' : 'search',
      normalized,
      compact,
    };
  }

  if (reportIntent) {
    return { route: 'report', mode: 'search', normalized, compact };
  }

  if (complaintIntent) {
    return { route: 'complaint', mode: 'search', normalized, compact };
  }

  if (emailIntent) {
    return { route: 'email', mode: 'search', normalized, compact };
  }

  return { route: 'general', mode: 'general', normalized, compact };
}

function isTaskIntent(text) {
  return normalizeUserIntent(text).route === 'task';
}

function isDatabaseIntent(text) {
  return normalizeUserIntent(text).route === 'db';
}

function isEmailIntent(text) {
  return normalizeUserIntent(text).route === 'email';
}

function isReportIntent(text) {
  return normalizeUserIntent(text).route === 'report';
}

function isComplaintIntent(text) {
  return normalizeUserIntent(text).route === 'complaint';
}

function classifyRoute(text) {
  return normalizeUserIntent(text).route;
}

function normalizeComplaintQuery(text) {
  let normalized = (text || '').trim();
  normalized = normalized.replace(/\d{4}[/-]\d{1,2}[/-]\d{1,2}/g, ' ');
  normalized = normalized.replace(/(今日|昨日|明日|本日|先月|今月|今年|去年)/g, ' ');
  normalized = normalized.replace(/\b\d+\b/g, ' ');
  normalized = normalized.replace(/\s+/g, ' ').trim();
  return normalized || 'クレーム';
}

async function telegramRequest(botToken, method, endpoint, body = null) {
  const url = `https://api.telegram.org/bot${botToken}/${endpoint}`;
  const init = { method };
  if (body) {
    init.headers = { 'content-type': 'application/x-www-form-urlencoded' };
    init.body = new URLSearchParams(body);
  }
  const res = await fetch(url, init);
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`Telegram API ${res.status}: ${text.slice(0, 200)}`);
  }
  return JSON.parse(text);
}

async function sendTelegramMessage(botToken, chatId, text, replyToMessageId = 0) {
  const allowedChatId = assertAllowedTelegramChatId(chatId, 'telegram_fast_bridge.sendTelegramMessage');
  const body = { chat_id: allowedChatId, text };
  if (replyToMessageId > 0) {
    body.reply_to_message_id = String(replyToMessageId);
  }
  return telegramRequest(botToken, 'POST', 'sendMessage', body);
}

async function editTelegramMessage(botToken, chatId, messageId, text) {
  const allowedChatId = assertAllowedTelegramChatId(chatId, 'telegram_fast_bridge.editTelegramMessage');
  const body = {
    chat_id: allowedChatId,
    message_id: String(messageId),
    text,
  };
  return telegramRequest(botToken, 'POST', 'editMessageText', body);
}

async function getTelegramUpdates(botToken, offset) {
  const params = new URLSearchParams({
    timeout: '20',
    allowed_updates: '["message"]',
  });
  if (offset !== null && offset !== undefined) {
    params.set('offset', String(offset + 1));
  }
  return telegramRequest(botToken, 'GET', `getUpdates?${params.toString()}`);
}

// ── Think mode utilities ──────────────────────────────────────────────────────

/**
 * Parse /no_think or /think prefix from user message.
 * Returns { text: stripped_text, thinkOverride: true|false|null }
 *   null = use auto-detection
 */
function parseThinkPrefix(rawText) {
  let t = (rawText || '').trim();
  let thinkOverride = null;
  let fastMode = false;

  // Multi-command support: /fast /think ...
  let matched = true;
  while (matched) {
    matched = false;
    if (/^\/no_think\s*/i.test(t)) {
      t = t.replace(/^\/no_think\s*/i, '').trim();
      thinkOverride = false;
      matched = true;
    }
    if (/^\/think\s*/i.test(t)) {
      t = t.replace(/^\/think\s*/i, '').trim();
      thinkOverride = true;
      matched = true;
    }
    if (/^\/fast\s*/i.test(t)) {
      t = t.replace(/^\/fast\s*/i, '').trim();
      fastMode = true;
      matched = true;
    }
  }
  return { text: t, thinkOverride, fastMode };
}

/**
 * Auto-detect whether thinking mode is beneficial.
 * Long analytical/reasoning questions → think: true (slower but smarter)
 * Short/factual → think: false (fast)
 */
function shouldAutoThink(text) {
  const t = (text || '').trim();
  if (t.length < 20) return false;
  return /(分析|解析|比較|評価|考察|推論|なぜ|理由|原因|対策|計画|設計|最適化|どうすれば|どうしたら|どちらが|pros|cons|メリット|デメリット|利点|欠点|問題点|改善|提案|説明して|教えて.*詳しく|深く|根本|仮説|検討)/i.test(t);
}

/**
 * Resolve final think flag for a qwen3 call.
 *   thinkOverride=true/false → use that directly
 *   thinkOverride=null       → auto-detect via shouldAutoThink
 */
function resolveThink(text, thinkOverride) {
  if (thinkOverride !== null && thinkOverride !== undefined) return thinkOverride;
  return shouldAutoThink(text);
}

// ─────────────────────────────────────────────────────────────────────────────

async function callOllamaGenerate(prompt, onProgress = null, think = false, onStream = null) {
  let progressTimer = null;
  const startedAt = Date.now();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), MODEL_TIMEOUT_MS);
  const emitProgress = async (stage) => {
    if (!onProgress) return;
    try {
      await onProgress(stage, startedAt);
    } catch {
    }
  };

  try {
    if (!onStream) {
      await emitProgress(think ? '思考中...' : '応答を準備しています。');
      const stages = think
        ? ['考えています...', '分析しています...', '回答をまとめています。']
        : ['質問を整理しています。', '応答を生成しています。', '文面を整えています。'];
      let index = 0;
      progressTimer = setInterval(() => {
        const stage = stages[Math.min(index, stages.length - 1)];
        index += 1;
        void emitProgress(stage);
      }, 5000);
    }

    const res = await fetch(`${ollamaUrl}/api/generate`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        model: localModel,
        prompt,
        stream: !!onStream,
        ...(localModel.includes('qwen3') || localModel.includes('qwen') ? { think } : {}),
        options: {
          temperature: 0.3,
          num_predict: think ? 600 : 220,
          num_ctx: think ? 8192 : 4096,
        },
      }),
    });
    if (!res.ok) {
      throw new Error(`Ollama API ${res.status}`);
    }

    if (onStream) {
      const reader = res.body.getReader();
      let fullText = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = new TextDecoder().decode(value);
        const lines = chunk.split('\n').filter(l => l.trim());
        for (const line of lines) {
          try {
            const json = JSON.parse(line);
            if (json.response) {
              fullText += json.response;
              onStream(fullText);
            }
          } catch (e) {}
        }
      }
      return fullText;
    } else {
      const json = await res.json();
      await emitProgress('応答の生成が完了しました。');
      return json.response || '';
    }
  } finally {
    clearTimeout(timeoutId);
    if (progressTimer) clearInterval(progressTimer);
  }
}

async function callModelGenerate(prompt, onProgress = null, onStream = null) {
  let progressTimer = null;
  const startedAt = Date.now();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), MODEL_TIMEOUT_MS);
  const emitProgress = async (stage) => {
    if (!onProgress) return;
    try {
      await onProgress(stage, startedAt);
    } catch {
    }
  };

  try {
    if (!onStream) {
      await emitProgress('応答を準備しています。');
      const stages = [
        '質問を整理しています。',
        '応答を生成しています。',
        '文面を整えています。',
      ];
      let index = 0;
      progressTimer = setInterval(() => {
        const stage = stages[Math.min(index, stages.length - 1)];
        index += 1;
        void emitProgress(stage);
      }, 5000);
    }

    if (usesOpenAiCompatibleRoute(replyModel)) {
      const res = await fetch(`${replyApiBase}/chat/completions`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          authorization: `Bearer ${replyApiKey}`,
        },
        signal: controller.signal,
        body: JSON.stringify({
          model: replyModel,
          temperature: 0.35,
          max_tokens: 300,
          stream: !!onStream,
          messages: [{ role: 'user', content: prompt }],
        }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`OpenAI-compatible API ${res.status}: ${text.slice(0, 200)}`);
      }

      if (onStream) {
        const reader = res.body.getReader();
        let fullText = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = new TextDecoder().decode(value);
          const lines = chunk.split('\n').filter(l => l.trim());
          for (const line of lines) {
            let jsonString = line;
            if (line.startsWith('data: ')) {
              jsonString = line.substring(6);
            }
            if (jsonString === '[DONE]') continue;
            try {
              const json = JSON.parse(jsonString);
              const delta = json.choices?.[0]?.delta?.content;
              if (delta) {
                fullText += delta;
                onStream(fullText);
              }
            } catch (e) {}
          }
        }
        return fullText;
      } else {
        const json = await res.json();
        await emitProgress('応答の生成が完了しました。');
        return json.choices?.[0]?.message?.content || '';
      }
    }

    return callOllamaGenerate(prompt, onProgress, false, onStream);
  } finally {
    clearTimeout(timeoutId);
    if (progressTimer) clearInterval(progressTimer);
  }
}

// ── RAG: embedding + Qdrant search (direct HTTP, no docker exec) ──────────────

const INFINITY_URL  = process.env.INFINITY_URL  || 'http://127.0.0.1:7997';
const QDRANT_URL    = process.env.QDRANT_URL    || 'http://127.0.0.1:6333';
const RAG_SCORE_MIN = parseFloat(process.env.RAG_SCORE_MIN || '0.50');

async function embedMxbai(text) {
  const res = await fetch(`${INFINITY_URL}/embeddings`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ model: 'mixedbread-ai/mxbai-embed-large-v1', input: [text] }),
  });
  if (!res.ok) throw new Error(`Infinity embed ${res.status}`);
  const json = await res.json();
  return json.data[0].embedding;
}

async function embedNomic(text) {
  const res = await fetch(`${ollamaUrl}/api/embeddings`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ model: 'nomic-embed-text', prompt: text }),
  });
  if (!res.ok) throw new Error(`Ollama embed ${res.status}`);
  const json = await res.json();
  return json.embedding;
}

async function qdrantSearch(collection, vector, topK = 4) {
  const res = await fetch(`${QDRANT_URL}/collections/${collection}/points/search`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ vector, top: topK, with_payload: true, score_threshold: RAG_SCORE_MIN }),
  });
  if (!res.ok) throw new Error(`Qdrant search ${res.status}`);
  const json = await res.json();
  return json.result || [];
}

function detectRagCollection(text) {
  const t = text || '';
  if (/(IATF|ISO.?9001|ISO.?16949|QMS|品質マニュアル|品質管理システム|内部監査|顧客要求|マネジメントレビュー|是正処置|不適合管理)/i.test(t)) {
    return { collection: 'iatf_knowledge', embedFn: embedNomic };
  }
  if (/(FMEA|5Why|故障モード|工程能力|公差解析|CETOL|FEM|有限要素|強度解析|射出成形|金型設計|プレス加工|溶接|材料特性|SPC|MSA|測定システム|検査基準|図面公差|幾何公差|GD&T|不良原因|品質異常|改善提案|設備保全|予防保全)/i.test(t)) {
    return { collection: 'universal_knowledge', embedFn: embedMxbai };
  }
  return null;
}

async function ragSearch(text) {
  const target = detectRagCollection(text);
  if (!target) return [];
  try {
    const vector  = await target.embedFn(text);
    const results = await qdrantSearch(target.collection, vector, 4);
    return results.map(r => ({
      score:  r.score,
      source: r.payload?.source || r.payload?.file || 'unknown',
      text:   (r.payload?.text || r.payload?.content || '').slice(0, 600),
    }));
  } catch {
    return [];
  }
}

// ── LLM Classifier (qwen3:8b, think:false, ~5-10s) ───────────────────────────

const CLASSIFIER_MODEL   = process.env.TELEGRAM_CLASSIFIER_MODEL || 'qwen3:8b';
const CLASSIFIER_TIMEOUT = Number(process.env.TELEGRAM_CLASSIFIER_TIMEOUT_MS || 20000);

async function classifyWithLLM(text) {
  const prompt = `以下の質問を1語で分類してください。選択肢のみ出力。

simple: 挨拶・雑談・簡単な一般知識
rag: 品質管理・IATF・製造技術・図面・材料・工程・FMEA・公差・設備の専門知識
agent: ブラウザ操作・ファイル操作・複数ステップの自動化タスク・システム操作
gemini: 最新情報・時事・複雑な推論・広範な一般知識・創作・翻訳

質問: "${text.slice(0, 200)}"
分類(simple/rag/agent/gemini):`;

  const controller = new AbortController();
  const tid = setTimeout(() => controller.abort(), CLASSIFIER_TIMEOUT);
  try {
    const res = await fetch(`${ollamaUrl}/api/generate`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, signal: controller.signal,
      body: JSON.stringify({
        model: CLASSIFIER_MODEL, prompt, stream: false, think: false,
        options: { temperature: 0.1, num_predict: 8, num_ctx: 1024 },
      }),
    });
    if (!res.ok) return null;
    const reply = ((await res.json()).response || '').toLowerCase().trim();
    if (reply.includes('simple')) return 'simple';
    if (reply.includes('rag'))    return 'rag';
    if (reply.includes('agent'))  return 'agent';
    if (reply.includes('gemini')) return 'gemini';
    return null;
  } catch { return null; } finally { clearTimeout(tid); }
}

/**
 * Expanded keyword classifier — no LLM call (CPU推論は遅すぎるため).
 * Coverage priority: simple > agent > rag > local-general > gemini
 */
function classifyMessageFast(text) {
  const t = (text || '').trim();

  // ── simple: greetings, short factual, status ───────────────────────
  if (needsLocalOnly(t)) return 'simple';
  if (/^(今日|今週|今月|今年|明日|昨日)の(天気|予定|タスク|売上|生産|進捗|状況|報告|スケジュール)/.test(t)) return 'simple';
  if (/^(ステータス|状態|進捗|状況)(は|を|教えて|どう|確認)/.test(t)) return 'simple';
  if (/(何時|何日|何曜日|いつ|どこ|誰が)[？?]?\s*$/.test(t)) return 'simple';

  // ── agent: multi-step system ops ──────────────────────────────────
  if (needsAgentEscalation(t)) return 'agent';

  // ── rag: manufacturing / quality / engineering domain ─────────────
  if (detectRagCollection(t)) return 'rag';
  // Extended rag keywords (manufacturing/quality ops not in detectRagCollection)
  if (/(工程\s*(管理|改善|フロー|能力)|設備\s*(保全|故障|異常|点検)|品質\s*(コスト|指標|目標|改善|記録)|作業標準|手順書|WI|QC工程図|初物検査|最終検査|出荷検査|受入検査|サンプリング|抜取り|ロット|トレーサビリティ|4M変更|変更管理)/i.test(t)) return 'rag';

  // ── local-general: Japanese conversational / factual (qwen3:8b) ───
  if (t.length <= 60 && /^[ぁ-んァ-ン一-龥々〆〇ー！？。、\s]+$/.test(t)) return 'simple';
  if (/(どうすれば|どうやって|方法|手順|ポイント|コツ|注意点|違い|比較|メリット|デメリット|おすすめ|アドバイス)/.test(t) && t.length < 80) return 'simple';

  // ── gemini: current events, broad knowledge, translation, creative
  if (/(最新|ニュース|今年.*リリース|新機能|アップデート|翻訳して|英語で|英訳|日本語訳|要約して.*記事|ウェブで|インターネット)/.test(t)) return 'gemini';

  // Default: short → simple (local), longer → gemini (cloud)
  return t.length <= 50 ? 'simple' : 'gemini';
}

async function classifyMessage(text) {
  return classifyMessageFast(text);
  // NOTE: LLM classifier (classifyWithLLM) disabled — qwen3:8b takes 120s on CPU
  // Re-enable when GPU is added: return (await classifyWithLLM(text)) || 'gemini';
}

// ── Escalation tier detection ─────────────────────────────────────────────────

/**
 * Tier 1: Simple/short messages → local qwen3:8b (free, ~95s on CPU)
 * Greetings, single-word queries, very short acknowledgments.
 */
function needsLocalOnly(text) {
  const t = (text || '').trim();
  if (t.length === 0) return false;
  // Greetings / acknowledgments
  if (/^(こんにちは|おはよう|こんばんは|お疲れ様|ありがとう|thanks|thank you|hello|hi|hey|ok|okay|はい|いいえ|わかりました|了解|なるほど|そうか|すごい|やった|確認しました)[\!\?。！？\s]*$/i.test(t)) return true;
  // Very short with no complex intent
  if (t.length <= 12 && !/[調査|検索|分析|作成|生成|修正|コード|スクリプト|設定|一覧|送信|削除]/.test(t)) return true;
  return false;
}

/**
 * Tier 3: Agent-requiring messages → OpenClaw (browser, file ops, system ops)
 * User can also explicitly prefix with /agent or エージェント:
 */
function needsAgentEscalation(text) {
  const t = (text || '').trim();
  if (/^\/agent\b/i.test(t) || /^エージェント[：:]/i.test(t)) return true;
  return /(ブラウザで|サイトを開|URLを|ファイルを(作成|削除|移動|編集)|スクリプトを(書|実行|作成)|n8nの(ワークフロー|設定)|コンテナを再起動|ログを(取得|確認|解析)して|自動(化|実行|スクレイピング)|PDFを(作成|生成|変換)|メールを(送信|作成|書いて)|全件(取得|一覧|検索)|データベース(を|に|から)(操作|更新|クエリ))/i.test(t);
}

// ── Escalation call functions ─────────────────────────────────────────────────

/**
 * Call local Ollama directly (qwen3:8b) — bypasses LiteLLM for speed.
 * Used for Tier 1 (simple) and Tier 2 local analytical questions.
 * @param {string} text
 * @param {function|null} onProgress
 * @param {boolean|null} thinkOverride  null=auto-detect, true/false=force
 */
async function callLocalModelDirect(text, onProgress = null, thinkOverride = null, history = []) {
  const think = resolveThink(text, thinkOverride);
  const prompt = think
    ? [
        'あなたは日本語で深く考えて答える分析的なアシスタントです。',
        '段階的に考え、根拠を示しながら丁寧に答えてください。',
        '',
        ...formatHistoryBlock(history),
        `User: ${text}`,
      ].join('\n')
    : [
        'あなたは日本語で答える実用的で親切なアシスタントです。',
        '簡潔に、1〜3文で答えてください。',
        '',
        ...formatHistoryBlock(history),
        `User: ${text}`,
      ].join('\n');
  try {
    const savedModel = replyModel;
    // Temporarily override replyModel so callOllamaGenerate uses qwen3:8b
    // We call the Ollama endpoint directly instead to avoid model confusion
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), MODEL_TIMEOUT_MS + (think ? 90000 : 0));
    try {
      const res = await fetch(`${ollamaUrl}/api/generate`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          model: localModel,
          prompt,
          stream: false,
          think,
          options: {
            temperature: think ? 0.5 : 0.3,
            num_predict: think ? 800 : 220,
            num_ctx: think ? 8192 : 4096,
          },
        }),
      });
      if (!res.ok) throw new Error(`Ollama ${res.status}`);
      const json = await res.json();
      return sanitizeModelReply(text, json.response || '');
    } finally {
      clearTimeout(timeoutId);
    }
  } catch {
    return null; // fallback to cloud
  }
}

/**
 * Escalate to OpenClaw agent via docker exec.
 * Used for Tier 3 (agent-requiring) questions.
 */
async function callAgentEscalation(text, onProgress = null) {
  if (onProgress) {
    await onProgress('エージェントに転送中...', Date.now()).catch(() => {});
  }
  try {
    const { stdout } = await execFileAsync(
      'docker',
      [
        'exec', GATEWAY_CONTAINER,
        'openclaw', 'agent',
        '--message', text,
        '--json',
        '--timeout', '110',
      ],
      { timeout: AGENT_TIMEOUT_MS }
    );
    // openclaw --json may output multiple lines; find the JSON object
    const lines = stdout.trim().split('\n').reverse();
    for (const line of lines) {
      try {
        const obj = JSON.parse(line.trim());
        const reply = obj.reply || obj.response || obj.content || obj.output || obj.text;
        if (reply && typeof reply === 'string' && reply.length > 0) return reply;
      } catch { /* skip non-JSON lines */ }
    }
    const plain = stdout.trim();
    if (plain.length > 0) return plain;
    return null;
  } catch (e) {
    return null; // fallback to cloud on timeout or error
  }
}

// ── General reply (tiered) ────────────────────────────────────────────────────

// ── RAG-enhanced reply ────────────────────────────────────────────────────────

async function generateRagReply(text, onProgress = null, thinkOverride = null, history = []) {
  if (onProgress) await onProgress('知識ベースを検索しています...', Date.now()).catch(() => {});

  const hits = await ragSearch(text);

  if (hits.length === 0) {
    // RAG found nothing → fall back to qwen3:8b without context
    return callLocalModelDirect(text, onProgress, thinkOverride, history);
  }

  const context = hits
    .map((h, i) => `[${i + 1}] (score=${h.score.toFixed(2)}, source: ${h.source})\n${h.text}`)
    .join('\n\n');

  const think = resolveThink(text, thinkOverride);
  const prompt = [
    'あなたは製造業の専門知識を持つ日本語アシスタントです。',
    '以下の参照資料を使って、質問に対して正確かつ簡潔に答えてください。',
    '資料に答えがない場合は「資料には記載がありません」と明示してください。',
    '',
    '=== 参照資料 ===',
    context,
    '=== ここまで ===',
    '',
    ...formatHistoryBlock(history),
    `質問: ${text}`,
  ].join('\n');

  const controller = new AbortController();
  const tid = setTimeout(() => controller.abort(), MODEL_TIMEOUT_MS + (think ? 90000 : 0));
  try {
    const res = await fetch(`${ollamaUrl}/api/generate`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        model: localModel,
        prompt,
        stream: false,
        think,
        options: {
          temperature: think ? 0.4 : 0.3,
          num_predict: think ? 1000 : 400,
          num_ctx: think ? 8192 : 6144,
        },
      }),
    });
    if (!res.ok) throw new Error(`Ollama RAG ${res.status}`);
    const json = await res.json();
    const reply = sanitizeModelReply(text, json.response || '');
    if (reply) {
      const srcList = [...new Set(hits.map(h => h.source))].slice(0, 2).join(', ');
      return `${reply}\n\n📚 参照: ${srcList}`;
    }
    return null;
  } catch { return null; } finally { clearTimeout(tid); }
}

// ── Main general reply — full 4-tier loop ─────────────────────────────────────

async function generateGeneralReply(text, onProgress = null, thinkOverride = null, history = [], onStream = null, fastMode = false) {
  const tier = await classifyMessage(text);
  writeEvent('classify', { lastMessage: text, tier, think: thinkOverride, fast: fastMode });

  // Speed optimization: for fastMode or specific keywords, prefer Cloud (Gemini)
  const isUrgent = /(緊急|至急|トラブル|故障|停止|火災|事故|怪我|危険)/.test(text);
  const useFastCloud = fastMode || isUrgent;

  if (!useFastCloud) {
    switch (tier) {
      case 'simple': {
        const r = await callLocalModelDirect(text, onProgress, false);
        if (r) return r;
        break;
      }
      case 'rag': {
        const r = await generateRagReply(text, onProgress, thinkOverride);
        if (r) return r;
        break;
      }
      case 'agent': {
        const r = await callAgentEscalation(text, onProgress);
        if (r) return r;
        break;
      }
    }
  }

  // Final tier: Cloud model (Gemini 2.5 Flash)
  // Also handles thinkOverride=true by first trying local with thinking
  if (thinkOverride === true && tier !== 'agent' && !fastMode) {
    const r = await callLocalModelDirect(text, onProgress, true, history);
    if (r) return r;
  }

  const prompt = [
    'You are a warm and natural Japanese assistant on Telegram.',
    'Reply in Japanese.',
    isUrgent ? 'IMPORTANT: This is an URGENT inquiry. Provide a brief, safe, and helpful initial response immediately.' : '',
    'For greetings or casual conversation, respond warmly and naturally in 1 to 3 short sentences.',
    'Do not list capabilities unless the user asks for them.',
    'If you cannot verify something from local context, say that clearly and offer the next helpful step.',
    '',
    ...formatHistoryBlock(history),
    `User: ${text}`,
  ].join('\n');
  try {
    const raw = await callModelGenerate(prompt, onProgress, onStream);
    return sanitizeModelReply(text, raw);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    writeEvent('model_fallback_reply', { lastMessage: text, lastError: message });
    return '応答生成がタイムアウトしました。短めに聞き直すか、/fast を付けて送ってください。';
  }
}

async function generateEmailReply(text, onProgress = null, history = [], onStream = null) {
  const emailContext = await fetchEmailContext(repoRoot, text, { limit: 5, force: true });
  if (emailContext.summary && emailContext.resultCount > 0 && /(summary|要約|今日|昨日|最新)/i.test(text)) {
    return emailContext.summary;
  }
  const prompt = buildEmailAwarePrompt([
    'You are a practical Japanese assistant on Telegram.',
    'Reply in Japanese.',
    'Use the local email context if it is relevant.',
    'If the local context is insufficient, say that clearly.',
    '',
    ...formatHistoryBlock(history),
    `User: ${text}`,
  ], emailContext, null);
  const raw = await callModelGenerate(prompt, onProgress, onStream);
  return sanitizeModelReply(text, raw);
}

async function generateTaskReply(text) {
  const taskContext = await fetchTaskContext(repoRoot, text, { limit: 5, force: true });
  if (taskContext.summary) return taskContext.summary;
  return 'タスクに関する一致はまだ見つかりませんでした。対象や期限があればもう少し具体的に送ってください。';
}

async function generateComplaintReply(text) {
  const complaintContext = await fetchComplaintContext(repoRoot, text, { limit: 5, force: true });
  if (complaintContext.summary) {
    return complaintContext.summary;
  }

  const normalizedQuery = normalizeComplaintQuery(text);
  return `クレーム関連の一致はまだ見つかりませんでした。確認対象: ${normalizedQuery}`;
}

async function generateDatabaseReply(text) {
  const existingContext = loadDbContext();
  const intent = normalizeUserIntent(text);

  if (intent.mode === 'followup' && existingContext && Array.isArray(existingContext.titles) && existingContext.titles.length > 0) {
    return `直前のDB検索で見つかった資料名です。\n${existingContext.titles.slice(0, 10).map((title, index) => `${index + 1}. ${title}`).join('\n')}`;
  }

  if (intent.mode === 'count') {
    const emailCount = await fetchEmailCount(repoRoot, text);
    const emailContext = await fetchEmailContext(repoRoot, text, { limit: 10, force: true });
    const titles = uniqueStrings(extractContextTitles(emailContext));
    saveDbContext({
      query: text,
      route: 'db',
      mode: 'count',
      resultCount: emailCount.resultCount,
      titles,
    });
    const preview = titles.length > 0
      ? `\n代表資料名:\n${titles.slice(0, 5).map((title, index) => `${index + 1}. ${title}`).join('\n')}`
      : '';
    return `ローカルDB検索結果\n該当件数: ${emailCount.resultCount} 件${preview}`;
  }

  const taskContext = await fetchTaskContext(repoRoot, text, { limit: 5, force: true });
  const reportContext = await fetchReportContext(repoRoot, text, { limit: 5, force: true });
  const emailContext = await fetchEmailContext(repoRoot, text, { limit: 5, force: true });
  const sections = [];

  if (taskContext.summary && taskContext.resultCount > 0) {
    sections.push(`タスクDB:\n${taskContext.summary}`);
  }
  if (reportContext.summary && reportContext.resultCount > 0) {
    sections.push(`レポートDB:\n${reportContext.summary}`);
  }
  if (emailContext.summary && emailContext.resultCount > 0) {
    sections.push(`メールDB:\n${emailContext.summary}`);
  }

  if (sections.length > 0) {
    const titles = uniqueStrings([
      ...extractContextTitles(taskContext),
      ...extractContextTitles(reportContext),
      ...extractContextTitles(emailContext),
    ]);
    saveDbContext({
      query: text,
      route: 'db',
      mode: intent.mode || 'search',
      resultCount: Math.max(
        Number(taskContext.resultCount || 0),
        Number(reportContext.resultCount || 0),
        Number(emailContext.resultCount || 0),
      ),
      titles,
    });
    return `ローカルDBを検索しました。\n\n${sections.join('\n\n')}`;
  }

  if (intent.mode === 'list' && existingContext && Array.isArray(existingContext.titles) && existingContext.titles.length > 0) {
    return `直前のDB検索で見つかった資料名です。\n${existingContext.titles.slice(0, 10).map((title, index) => `${index + 1}. ${title}`).join('\n')}`;
  }

  return 'ローカルDB検索では該当データを見つけられませんでした。キーワードを少し変えるか、資料名・期間・対象をもう少し具体的に教えてください。';
}

async function routeReply(text, onProgress = null, routeName = null, thinkOverride = null, history = [], onStream = null, fastMode = false) {
  const route = routeName || classifyRoute(text);
  writeEvent('route', { lastMessage: text, route, think: thinkOverride, fast: fastMode });

  if (route === 'db' && !fastMode) {
    return generateDatabaseReply(text);
  }

  if (route === 'report' && !fastMode) {
    const reportContext = await fetchReportContext(repoRoot, text, { limit: 5, force: true });
    if (reportContext.summary && reportContext.resultCount > 0) return reportContext.summary;
    const prompt = buildEmailAwarePrompt([
      'You are a practical Japanese assistant on Telegram.',
      'Reply in Japanese.',
      'Use the scheduled report context if it is relevant.',
      'If the local context is insufficient, say that clearly.',
      '',
      ...formatHistoryBlock(history),
      `User: ${text}`,
    ], null, null, reportContext);
    const raw = await callModelGenerate(prompt, onProgress, onStream);
    return sanitizeModelReply(text, raw);
  }

  if (route === 'task' && !fastMode) {
    return generateTaskReply(text);
  }

  if (route === 'complaint' && !fastMode) {
    return generateComplaintReply(text);
  }

  if (route === 'email' && !fastMode) {
    return generateEmailReply(text, onProgress, history, onStream);
  }

  return generateGeneralReply(text, onProgress, thinkOverride, history, onStream, fastMode);
}

// ── Buffered Stream Updater ──────────────────────────────────────────────────
class BufferedStreamUpdater {
  constructor(botToken, chatId, messageId, initialText = '') {
    this.botToken = botToken;
    this.chatId = chatId;
    this.messageId = messageId;
    this.currentText = initialText;
    this.pendingText = '';
    this.lastUpdateTime = 0;
    this.updateInterval = 1200; // Telegram rate limit safe
    this.timer = null;
    this.isFinished = false;
  }

  async update(newText) {
    if (this.isFinished) return;
    this.pendingText = newText;
    if (Date.now() - this.lastUpdateTime > this.updateInterval) {
      await this.flush();
    } else if (!this.timer) {
      this.timer = setTimeout(() => this.flush(), this.updateInterval);
    }
  }

  async flush() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.pendingText === this.currentText || !this.pendingText) return;

    try {
      await editTelegramMessage(this.botToken, this.chatId, this.messageId, this.pendingText);
      this.currentText = this.pendingText;
      this.lastUpdateTime = Date.now();
    } catch (e) {
      // Ignore "message is not modified" or "too many requests" errors during stream
    }
  }

  async finish(finalText) {
    this.isFinished = true;
    if (this.timer) clearTimeout(this.timer);
    if (finalText && finalText !== this.currentText) {
      try {
        await editTelegramMessage(this.botToken, this.chatId, this.messageId, finalText);
      } catch (e) {}
    }
  }
}

async function main() {
  acquireLock();

  const cfg = readJson(configFile, {});
  const botToken = cfg.channels?.telegram?.botToken;
  const allowedChatIds = (cfg.channels?.telegram?.allowFrom || []).map(String);
  if (!botToken || allowedChatIds.length === 0) {
    writeStatus('config_error');
    process.exit(1);
  }

  let offset = loadOffset();
  writeStatus('starting', { lastUpdateId: offset });

  while (true) {
    let response;
    try {
      response = await getTelegramUpdates(botToken, offset);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const state = message.includes('409') ? 'poll_conflict' : 'poll_error';
      writeEvent('poll_error', { lastUpdateId: offset, lastError: message });
      writeStatus(state, { lastUpdateId: offset, lastError: message });
      await sleep(5000);
      continue;
    }

    const updates = Array.isArray(response.result) ? response.result : [];
    if (updates.length === 0) {
      writeStatus('idle', { lastUpdateId: offset });
      continue;
    }

    for (const update of updates) {
      try {
        const updateId = Number(update.update_id);
        const message = update.message || {};
        const chatId = String(message.chat?.id || '');
        const text = String(message.text || '');
        const messageId = Number(message.message_id || 0);

        if (!allowedChatIds.includes(chatId)) {
          offset = updateId;
          saveOffset(offset);
          writeEvent('ignored', { lastUpdateId: offset, lastChatId: chatId });
          writeStatus('ignored', { lastUpdateId: offset, lastChatId: chatId });
          continue;
        }

        // Parse /no_think, /think, or /fast prefix BEFORE routing
        const { text: cleanText, thinkOverride, fastMode } = parseThinkPrefix(text);
        const history = loadHistory(chatId);

        let reply = await getFastReply(cleanText);
        if (reply === null) {
          const routeName = classifyRoute(cleanText);

          writeStatus('generating', {
            lastUpdateId: updateId,
            lastChatId: chatId,
            lastMessage: cleanText,
            route: routeName,
            think: thinkOverride,
            fast: fastMode,
          });

          // Initial typing status/ACK
          let progressMessageId = 0;
          let streamUpdater = null;

          if (routeName === 'general' || fastMode) {
            // Instant cloud route or simple general
            const initialText = fastMode ? '🚀 高速モードで確認中...' : '...';
            const progressResult = await sendTelegramMessage(botToken, chatId, initialText, messageId);
            progressMessageId = Number(progressResult?.result?.message_id || 0);
            if (progressMessageId > 0) {
              streamUpdater = new BufferedStreamUpdater(botToken, chatId, progressMessageId, initialText);
            }
          } else {
            // Complex local RAG/DB route with full progress reporting
            const ack = getAckReply();
            await sendTelegramMessage(botToken, chatId, ack, messageId);
            const progressStart = Date.now();
            const progressResult = await sendTelegramMessage(
              botToken,
              chatId,
              getProgressMessage(thinkOverride === true ? '思考中...' : '応答を準備しています。', 0),
              messageId,
            );
            progressMessageId = Number(progressResult?.result?.message_id || 0);
            
            const updateProgress = async (stage, startedAt = progressStart) => {
              if (progressMessageId <= 0) return;
              const elapsedSeconds = (Date.now() - startedAt) / 1000;
              await editTelegramMessage(botToken, chatId, progressMessageId, getProgressMessage(stage, elapsedSeconds));
            };

            reply = await routeReply(cleanText, updateProgress, routeName, thinkOverride, history, null, fastMode);
            if (progressMessageId > 0) {
              await editTelegramMessage(botToken, chatId, progressMessageId, getProgressMessage('生成完了。', (Date.now() - progressStart) / 1000));
            }
          }

          if (streamUpdater) {
            reply = await routeReply(
              cleanText,
              null,
              routeName,
              thinkOverride,
              history,
              (text) => streamUpdater.update(text),
              fastMode
            );
            await streamUpdater.finish(reply);
          }
        }

        // Final reply (if not already handled by stream finishing)
        if (reply) {
          // Note: If we streamed, the reply is already in progressMessageId.
          // But the code below might send it again. We should avoid double-sending.
          // In the current logic, if streamUpdater was used, we don't send separately.
          if (!streamUpdater) {
             await sendTelegramMessage(botToken, chatId, reply, messageId);
          }
        }
        
        history.push({ role: 'user', content: cleanText });
        history.push({ role: 'assistant', content: reply });
        saveHistory(chatId, history);

        offset = updateId;
        saveOffset(offset);
        writeEvent('reply', { lastUpdateId: offset, lastChatId: chatId, lastMessage: text, lastReply: reply });
        writeStatus('replied', { lastUpdateId: offset, lastChatId: chatId, lastMessage: text, lastReply: reply });
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        writeEvent('message_error', { lastUpdateId: offset, lastError: message });
        writeStatus('message_error', { lastUpdateId: offset, lastError: message });
        await sleep(2000);
      }
    }
  }
}

process.on('SIGINT', () => {
  releaseLock();
  process.exit(0);
});

process.on('SIGTERM', () => {
  releaseLock();
  process.exit(0);
});

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  writeStatus('error', { lastError: message });
  releaseLock();
  process.exit(1);
});
