// Which columns of a result name a desk document, and of which doctype, as the
// server traced it: keyed by result column name. Nothing here guesses a doctype
// from a column name — a miss renders no link rather than a link that lands on
// the wrong document.
export type RecordLinks = Record<string, string>
