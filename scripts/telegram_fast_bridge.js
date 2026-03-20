const fs = require('fs');
const path = require('path');
const {
  fetchEmailContext,
  fetchTaskContext,
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
const configFile = path.join(repoRoot, 'data', 'state', 'openclaw.json');

const ollamaUrl = (process.env.OLLAMA_URL || 'http://127.0.0.1:11434').replace(/\/$/, '');
const ollamaModel = process.env.TELEGRAM_FAST_MODEL || 'qwen3:8b';

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
    model: ollamaModel,
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

function buildStackStatusText() {
  return [
    'telegram_fast_bridge status',
    `reply_model=${ollamaModel}`,
    'router=explicit local rules',
    'task_search=sqlite tasks-context',
    'email_search=sqlite email context',
    'telegram_path=no_dify_no_classifier',
  ].join('\n');
}

async function getFastReply(text) {
  const trimmed = (text || '').trim();
  if (/^ping$/i.test(trimmed)) return 'pong';
  if (/^\/status$/i.test(trimmed)) return buildStackStatusText();
  if (/^\/models$/i.test(trimmed) || /^\/rankings$/i.test(trimmed) || isModelRankingIntent(trimmed)) {
    const installedModels = await fetchInstalledOllamaModels(ollamaUrl);
    return `${buildStackStatusText()}\n\n${buildModelRankingText(installedModels)}`;
  }
  if (!trimmed) return 'メッセージを送ってください。';
  if (/^(こんばんは|こんにちは|おはよう|やあ|hello|hi)$/i.test(trimmed)) {
    return 'こんにちは。メール要約、依頼事項確認、未回答確認、返信文案の下書きができます。';
  }
  if (/(何ができる|なにができる|使い方|ヘルプ|help|モデル構成|使っているモデル|使用モデル|今のモデル)/i.test(trimmed)) {
    return `${buildStackStatusText()}\n例: 昨日のメールを要約してください / 今月期限の未回答のみ / 依頼者 福田 の未回答のみ`;
  }
  if (/(天気|気温|降水|雨|晴れ|weather|forecast)/i.test(trimmed)) {
    return '天気データには未接続です。地域名と情報源を指定してもらえれば、別途接続できます。';
  }
  if (/(会話になってない|通じない|反応おかしい|変だ|おかしい)/.test(trimmed)) {
    return '失礼しました。今は業務向けです。メール、依頼事項、期限、未回答、回答内容の形式で送ってください。';
  }
  return null;
}

function getAckReply() {
  return '受け付けました。進捗をお知らせします。';
}

function getProgressMessage(stage, elapsedSeconds) {
  const seconds = Math.max(0, Math.floor(elapsedSeconds));
  return `${stage}\n経過: ${seconds}秒\nモデル: ${ollamaModel}`;
}

function normalizeCompareText(text) {
  return (text || '').trim().toLowerCase().replace(/\s+/g, '');
}

function sanitizeOllamaReply(inputText, replyText) {
  const trimmed = (inputText || '').trim();
  const reply = (replyText || '').trim();
  if (!reply) return '回答を生成できませんでした。メール、依頼事項、期限など具体的に送ってください。';
  const inputNorm = normalizeCompareText(trimmed);
  const replyNorm = normalizeCompareText(reply);
  if (replyNorm === 'received.' || replyNorm === 'received') {
    return '受信はできています。内容をもう少し具体的に送ってください。';
  }
  if (replyNorm === inputNorm) {
    return '入力をそのまま返してしまいました。目的を具体的に書いてください。';
  }
  return reply;
}

function isTaskIntent(text) {
  const trimmed = (text || '').trim();
  return /(依頼事項|依頼|期限|締切|締め切り|納期|提出|未回答|未返信|回答済|回答者|回答内容|担当者|期限切れ|今週|今月|明日|本日|タスク|todo|task|deadline|due)/i.test(trimmed);
}

function isEmailIntent(text) {
  const trimmed = (text || '').trim();
  return /(メール|mail|gmail|eml|受信|受診|inbox|件名|送信者|from:|to:|要約)/i.test(trimmed);
}

function isReportIntent(text) {
  const trimmed = (text || '').trim();
  return /(日報|レポート|AI Scout|トレンド|ランキング|約束事項|promises|health check|ヘルスチェック|P016|定刻|scheduled report)/i.test(trimmed);
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
  const body = { chat_id: String(chatId), text };
  if (replyToMessageId > 0) {
    body.reply_to_message_id = String(replyToMessageId);
  }
  return telegramRequest(botToken, 'POST', 'sendMessage', body);
}

async function editTelegramMessage(botToken, chatId, messageId, text) {
  const body = {
    chat_id: String(chatId),
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

async function callOllamaGenerate(prompt, onProgress = null) {
  let progressTimer = null;
  const startedAt = Date.now();
  const emitProgress = async (stage) => {
    if (!onProgress) return;
    try {
      await onProgress(stage, startedAt);
    } catch {
    }
  };

  try {
    await emitProgress('回答を準備しています。');
    const stages = [
      '質問内容を確認しています。',
      '回答案を生成しています。',
      '文章を整えています。',
    ];
    let index = 0;
    progressTimer = setInterval(() => {
      const stage = stages[Math.min(index, stages.length - 1)];
      index += 1;
      void emitProgress(stage);
    }, 5000);

    const res = await fetch(`${ollamaUrl}/api/generate`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        model: ollamaModel,
        prompt,
        stream: false,
        options: {
          temperature: 0.2,
          num_predict: 160,
          num_ctx: 2048,
        },
      }),
    });
    if (!res.ok) {
      throw new Error(`Ollama API ${res.status}`);
    }
    const json = await res.json();
    await emitProgress('回答の生成が完了しました。');
    return json.response || '';
  } finally {
    if (progressTimer) clearInterval(progressTimer);
  }
}

async function generateGeneralReply(text, onProgress = null) {
  const prompt = [
    'You are a practical Japanese work assistant on Telegram.',
    'Reply in Japanese.',
    'Keep the answer short and natural.',
    'If you do not know, say so directly.',
    '',
    `User: ${text}`,
  ].join('\n');
  const raw = await callOllamaGenerate(prompt, onProgress);
  return sanitizeOllamaReply(text, raw);
}

async function generateEmailReply(text, onProgress = null) {
  const emailContext = await fetchEmailContext(repoRoot, text, { limit: 5, force: true });
  if (emailContext.summary && emailContext.resultCount > 0 && /(要約|summary|昨日|今日|先週|先月)/i.test(text)) {
    return emailContext.summary;
  }
  const prompt = buildEmailAwarePrompt([
    'You are a practical Japanese work assistant on Telegram.',
    'Reply in Japanese.',
    'Use the local email context if relevant.',
    'If the local context is insufficient, say so directly.',
    '',
    `User: ${text}`,
  ], emailContext, null);
  const raw = await callOllamaGenerate(prompt, onProgress);
  return sanitizeOllamaReply(text, raw);
}

async function generateTaskReply(text) {
  const taskContext = await fetchTaskContext(repoRoot, text, { limit: 5, force: true });
  if (taskContext.summary) return taskContext.summary;
  return '依頼事項は見つかりませんでした。';
}

async function routeReply(text, onProgress = null) {
  if (isReportIntent(text)) {
    writeEvent('route', { lastMessage: text, route: 'report' });
    const reportContext = await fetchReportContext(repoRoot, text, { limit: 5, force: true });
    if (reportContext.summary && reportContext.resultCount > 0) return reportContext.summary;
    const prompt = buildEmailAwarePrompt([
      'You are a practical Japanese work assistant on Telegram.',
      'Reply in Japanese.',
      'Use the scheduled report context if relevant.',
      'If the local context is insufficient, say so directly.',
      '',
      `User: ${text}`,
    ], null, null, reportContext);
    const raw = await callOllamaGenerate(prompt, onProgress);
    return sanitizeOllamaReply(text, raw);
  }
  if (isTaskIntent(text)) {
    writeEvent('route', { lastMessage: text, route: 'task' });
    return generateTaskReply(text);
  }
  if (isEmailIntent(text)) {
    writeEvent('route', { lastMessage: text, route: 'email' });
    return generateEmailReply(text, onProgress);
  }
  writeEvent('route', { lastMessage: text, route: 'general' });
  return generateGeneralReply(text, onProgress);
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

        let reply = await getFastReply(text);
        if (reply === null) {
          const ack = getAckReply();
          await sendTelegramMessage(botToken, chatId, ack, messageId);
          writeEvent('ack', { lastUpdateId: updateId, lastChatId: chatId, lastMessage: text, lastReply: ack });
          writeStatus('generating', { lastUpdateId: updateId, lastChatId: chatId, lastMessage: text });

          const progressStart = Date.now();
          const progressResult = await sendTelegramMessage(
            botToken,
            chatId,
            getProgressMessage('処理を開始しました。', 0),
            messageId,
          );
          const progressMessageId = Number(progressResult?.result?.message_id || 0);
          const updateProgress = async (stage, startedAt = progressStart) => {
            if (progressMessageId <= 0) return;
            const elapsedSeconds = (Date.now() - startedAt) / 1000;
            await editTelegramMessage(botToken, chatId, progressMessageId, getProgressMessage(stage, elapsedSeconds));
            writeStatus('generating', {
              lastUpdateId: updateId,
              lastChatId: chatId,
              lastMessage: text,
              progressStage: stage,
              progressElapsedSec: Math.floor(elapsedSeconds),
            });
          };

          reply = await routeReply(text, updateProgress);
          if (progressMessageId > 0) {
            const doneSeconds = (Date.now() - progressStart) / 1000;
            await editTelegramMessage(botToken, chatId, progressMessageId, getProgressMessage('処理が完了しました。', doneSeconds));
          }
        }

        await sendTelegramMessage(botToken, chatId, reply, messageId);
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
