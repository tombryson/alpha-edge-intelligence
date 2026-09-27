  const LOOKBACK_THREADS = 20;
  const MAX_MESSAGES_PER_POLL = 8;
  const POLL_BUDGET_MS = 4.5 * 60 * 1000;
  const HOTCOPPER_LOOKBACK_MS = 2 * 24 * 60 * 60 * 1000;
  const HOTCOPPER_QUERY =
    'from:no-reply@hotcopper.com.au subject:announcement newer_than:2d is:unread';

  /**
   * Poll the automation mailbox and send each unread HotCopper announcement once.
   *
   * The Council service owns durable idempotency by gmail_message_id. Gmail's unread
   * state is the producer queue: terminal responses are marked read, while transient
   * failures remain unread for a later retry. Do not add per-message Script Properties.
   */
  function pollScenarioRouterAnnouncements() {
    const startedAt = Date.now();
    let delivered = 0;
    const threads = GmailApp.search(HOTCOPPER_QUERY, 0, LOOKBACK_THREADS);

    for (const thread of threads) {
      for (const message of thread.getMessages()) {
        // Gmail search returns whole threads, including already-read messages.
        if (!message.isUnread()) continue;
        if (!isRecentScenarioRouterMessage(message)) continue;
        if (delivered >= MAX_MESSAGES_PER_POLL || Date.now() - startedAt >= POLL_BUDGET_MS) {
          console.log(JSON.stringify({
            status: 'poll_budget_reached',
            delivered,
            elapsed_ms: Date.now() - startedAt,
          }));
          return;
        }

        const payload = buildScenarioRouterPayload(message);
        if (!shouldSendScenarioRouterPayload(payload)) continue;
        delivered += 1;
        console.log(JSON.stringify({
          status: 'delivery_start',
          gmail_message_id: payload.gmail_message_id,
          subject: payload.subject,
          received_at_utc: payload.received_at_utc,
        }));

        let result;
        try {
          result = sendScenarioRouterPayload(payload);
        } catch (error) {
          if ([401, 403].includes(getScenarioRouterHttpStatus(error))) {
            console.error(
              `Scenario router authentication failed for ${message.getId()}; ` +
              'messages remain unread and this will retry on the next scheduled poll. ' +
              `Verify SCENARIO_ROUTER_WEBHOOK_SECRET: ${String(error)}`
            );
            return;
          }
          console.error(
            `Scenario router delivery failed for ${message.getId()}: ${String(error)}`
          );
          continue;
        }

        logScenarioRouterResult(result);
        if (isScenarioRouterTerminalResult(result)) {
          message.markRead();
        }
      }
    }
  }

  function getScenarioRouterConfig() {
    const props = PropertiesService.getScriptProperties();
    return {
      webhookUrl: toScenarioRouterEnqueueUrl(
        props.getProperty('SCENARIO_ROUTER_WEBHOOK_URL')
      ),
      webhookSecret: props.getProperty('SCENARIO_ROUTER_WEBHOOK_SECRET'),
    };
  }

  function toScenarioRouterEnqueueUrl(value) {
    const url = String(value || '').trim();
    if (!url) return '';
    return url.replace(
      /\/api\/(?:scenario-router|announcement-router|freshness)\/process-announcement\/?$/,
      '/api/scenario-router/enqueue-announcement'
    );
  }

  function isRecentScenarioRouterMessage(message) {
    const receivedAt = message.getDate();
    return receivedAt instanceof Date &&
      receivedAt.getTime() >= Date.now() - HOTCOPPER_LOOKBACK_MS;
  }

  function buildScenarioRouterPayload(message) {
    const plainBody = message.getPlainBody() || '';
    return {
      gmail_message_id: message.getId(),
      subject: message.getSubject() || '',
      sender: message.getFrom() || '',
      body_text: plainBody,
      source_channel: 'gmail_hotcopper',
      received_at_utc: message.getDate().toISOString(),
      urls: extractUrls(plainBody),
      attachments: [],
    };
  }

  function shouldSendScenarioRouterPayload(payload) {
    const subject = String(payload.subject || '');
    const sender = String(payload.sender || '').toLowerCase();

    if (!sender.includes('hotcopper.com.au')) return false;
    if (!subject.toLowerCase().includes('announcement')) return false;
    return (
      /\b[A-Z0-9]{2,8}\s*\(ASX\)/i.test(subject) ||
      /\bASX[: ][A-Z0-9]{2,8}\b/i.test(subject)
    );
  }

  function sendScenarioRouterPayload(payload) {
    const config = getScenarioRouterConfig();
    if (!config.webhookUrl || !config.webhookSecret) {
      throw new Error(
        'Missing SCENARIO_ROUTER_WEBHOOK_URL or SCENARIO_ROUTER_WEBHOOK_SECRET'
      );
    }

    const response = UrlFetchApp.fetch(config.webhookUrl, {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'X-Scenario-Router-Secret': config.webhookSecret,
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
    });

    const code = response.getResponseCode();
    const text = response.getContentText();
    if (code < 200 || code >= 300) {
      const error = new Error(`Scenario router webhook failed: ${code} ${text}`);
      error.httpStatus = code;
      throw error;
    }

    return JSON.parse(text);
  }

  function isScenarioRouterTerminalResult(result) {
    return ['accepted', 'ok', 'duplicate', 'skipped_no_baseline_run'].includes(
      String(result && result.status || '')
    );
  }

  function getScenarioRouterHttpStatus(error) {
    const status = Number(error && error.httpStatus);
    if (Number.isFinite(status)) return status;

    const match = String(error || '').match(/\b(401|403)\b/);
    return match ? Number(match[1]) : 0;
  }

  function logScenarioRouterResult(result) {
    const compact = {
      status: String(result && result.status || ''),
      ticker: String(result && result.ticker || ''),
      action: String(result && result.action || ''),
      baseline_run_id: String(result && result.baseline_run_id || ''),
      current_path: String(result && result.current_path || ''),
      path_transition: String(result && result.path_transition || ''),
      detail: String(result && result.detail || ''),
    };
    console.log(JSON.stringify(compact));
  }

  function extractUrls(text) {
    const matches = String(text || '').match(/https?:\/\/[^\s)>\]]+/g) || [];
    return matches.map((url) => url.trim());
  }

  /** Run once after installing this version to remove the old unbounded markers. */
  function clearLegacyScenarioRouterProcessedProperties() {
    const props = PropertiesService.getScriptProperties();
    const legacyKeys = Object.keys(props.getProperties()).filter((key) =>
      key.startsWith('scenario_router_processed_')
    );

    legacyKeys.forEach((key) => props.deleteProperty(key));
    console.log(`Removed ${legacyKeys.length} legacy scenario-router markers.`);
  }

  function testScenarioRouterWebhook() {
    const payload = {
      gmail_message_id: `manual-test-${new Date().toISOString()}`,
      subject: 'PEN (ASX) announcement on HotCopper',
      sender: 'HotCopper Team <no-reply@hotcopper.com.au>',
      body_text:
        'PEN: Central Processing Plant Recommences Production\nPeninsula Energy Limited released an announcement.',
      source_channel: 'gmail_hotcopper',
      received_at_utc: new Date().toISOString(),
      urls: [],
      attachments: [],
    };

    const result = sendScenarioRouterPayload(payload);
    logScenarioRouterResult(result);
  }
