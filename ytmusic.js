// Helper functions for formatting time, numbers, and parsing responses

function formatSeconds(seconds) {
  if (isNaN(seconds) || seconds === null || seconds < 0) return "0:00";
  var sec = Math.floor(seconds);
  var m = Math.floor(sec / 60);
  var s = sec % 60;
  return m + ":" + (s < 10 ? "0" : "") + s;
}

function truncateString(str, maxLen) {
  if (!str) return "";
  var s = String(str).trim();
  if (s.length <= maxLen) return s;
  return s.substring(0, maxLen - 1) + "…";
}

function parseJsonSafe(text, fallback) {
  if (!text) return fallback;
  try {
    var trimmed = String(text).trim();
    var firstObj = trimmed.indexOf('{');
    var firstArr = trimmed.indexOf('[');
    
    if (firstObj !== -1 && (firstArr === -1 || firstObj < firstArr)) {
      var lastObj = trimmed.lastIndexOf('}');
      if (lastObj > firstObj) {
        trimmed = trimmed.substring(firstObj, lastObj + 1);
      }
    } else if (firstArr !== -1) {
      var lastArr = trimmed.lastIndexOf(']');
      if (lastArr > firstArr) {
        trimmed = trimmed.substring(firstArr, lastArr + 1);
      }
    }
    return JSON.parse(trimmed);
  } catch (e) {
    console.warn("JSON Parse Error:", e, "Input was:", text);
    return fallback;
  }
}
