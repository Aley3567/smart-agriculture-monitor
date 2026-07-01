const HAS_TIMEZONE = /(?:Z|[+-]\d{2}:?\d{2})$/i
const DATE_TIME_FORMAT = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
})

const DATE_TIME_MINUTE_FORMAT = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const SHORT_FORMAT = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  month: 'numeric',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const TIME_FORMAT = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
})

function normalizeFormatted(value) {
  return value.replace(/\//g, '-').replace(/,\s*/, ' ')
}

export function parseTimestamp(ts) {
  if (!ts) return null
  if (ts instanceof Date) return ts
  if (typeof ts !== 'string') return new Date(ts)

  const normalized = ts.includes('T') && !HAS_TIMEZONE.test(ts)
    ? `${ts}Z`
    : ts
  return new Date(normalized)
}

export function formatDateTime(ts) {
  if (!ts) return ''
  return normalizeFormatted(DATE_TIME_FORMAT.format(parseTimestamp(ts)))
}

export function formatDateTimeMinute(ts) {
  if (!ts) return ''
  return normalizeFormatted(DATE_TIME_MINUTE_FORMAT.format(parseTimestamp(ts)))
}

export function formatShortDate(ts) {
  if (!ts) return ''
  return SHORT_FORMAT.format(parseTimestamp(ts)).replace(/\//g, '/').replace(/,\s*/, ' ')
}

export function formatTimeOnly(ts) {
  if (!ts) return ''
  return TIME_FORMAT.format(parseTimestamp(ts))
}
