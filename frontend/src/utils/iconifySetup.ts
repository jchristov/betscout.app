import { addCollection } from "@iconify/vue";

const LUCIDE_SUBSET = {
  "prefix": "lucide",
  "width": 24,
  "height": 24,
  "icons": {
    "arrow-right": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M5 12h14m-7-7l7 7l-7 7\"/>"
    },
    "award": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"m15.477 12.89l1.515 8.526a.5.5 0 0 1-.81.47l-3.58-2.687a1 1 0 0 0-1.197 0l-3.586 2.686a.5.5 0 0 1-.81-.469l1.514-8.526\"/><circle cx=\"12\" cy=\"8\" r=\"6\"/></g>"
    },
    "bar-chart-3": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M3 3v18h18m-3-4V9m-5 8V5M8 17v-3\"/>",
      "hidden": true
    },
    "book-open": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 5v16m8.001-2A2 2 0 0 0 22 17V5a2 2 0 0 0-1.999-2L16 3.002A5 5 0 0 0 12 5a5 5 0 0 0-4-2H4a2 2 0 0 0-2 2v12a2 2 0 0 0 1.999 2H8a5 5 0 0 1 4 2a5 5 0 0 1 4-2z\"/>"
    },
    "calculator": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><rect width=\"16\" height=\"20\" x=\"4\" y=\"2\" rx=\"2\"/><path d=\"M8 6h8m0 8v4m0-8h.01M12 10h.01M8 10h.01M12 14h.01M8 14h.01M12 18h.01M8 18h.01\"/></g>"
    },
    "check": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M20 6L9 17l-5-5\"/>"
    },
    "check-circle-2": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><circle cx=\"12\" cy=\"12\" r=\"10\"/><path d=\"m16 9l-5.5 5.5L8 12\"/></g>"
    },
    "check-square": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M21 10.656V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12.344\"/><path d=\"m9 11l3 3L22 4\"/></g>"
    },
    "chevron-down": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"m6 9l6 6l6-6\"/>"
    },
    "chevron-right": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"m9 18l6-6l-6-6\"/>"
    },
    "clock": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><circle cx=\"12\" cy=\"12\" r=\"10\"/><path d=\"M12 6v6l4 2\"/></g>"
    },
    "copy": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><rect width=\"14\" height=\"14\" x=\"8\" y=\"8\" rx=\"2\" ry=\"2\"/><path d=\"M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2\"/></g>"
    },
    "database": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><ellipse cx=\"12\" cy=\"5\" rx=\"9\" ry=\"3\"/><path d=\"M3 5v14a9 3 0 0 0 18 0V5\"/><path d=\"M3 12a9 3 0 0 0 18 0\"/></g>"
    },
    "dices": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><rect width=\"12\" height=\"12\" x=\"2\" y=\"10\" rx=\"2\" ry=\"2\"/><path d=\"m17.92 14l3.5-3.5a2.24 2.24 0 0 0 0-3l-5-4.92a2.24 2.24 0 0 0-3 0L10 6M6 18h.01M10 14h.01M15 6h.01M18 9h.01\"/></g>"
    },
    "download": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M12 15V3m9 12v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\"/><path d=\"m7 10l5 5l5-5\"/></g>"
    },
    "download-cloud": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M12 13v8l-4-4m4 4l4-4\"/><path d=\"M4.393 15.269A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.436 8.284\"/></g>"
    },
    "flame": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 3q1 4 4 6.5t3 5.5a1 1 0 0 1-14 0a5 5 0 0 1 1-3a1 1 0 0 0 5 0c0-2-1.5-3-1.5-5q0-2 2.5-4\"/>"
    },
    "globe": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><circle cx=\"12\" cy=\"12\" r=\"10\"/><path d=\"M12 2a14.5 14.5 0 0 0 0 20a14.5 14.5 0 0 0 0-20M2 12h20\"/></g>"
    },
    "home": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8\"/><path d=\"M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z\"/></g>"
    },
    "layers": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z\"/><path d=\"M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12\"/><path d=\"M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17\"/></g>"
    },
    "link-2": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M9 17H7A5 5 0 0 1 7 7h2m6 0h2a5 5 0 1 1 0 10h-2m-7-5h8\"/>"
    },
    "lock": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><rect width=\"18\" height=\"11\" x=\"3\" y=\"11\" rx=\"2\" ry=\"2\"/><path d=\"M7 11V7a5 5 0 0 1 10 0v4\"/></g>"
    },
    "megaphone": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M11 6a13 13 0 0 0 8.4-2.8A1 1 0 0 1 21 4v12a1 1 0 0 1-1.6.8A13 13 0 0 0 11 14H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z\"/><path d=\"M6 14a12 12 0 0 0 2.4 7.2a2 2 0 0 0 3.2-2.4A8 8 0 0 1 10 14M8 6v8\"/></g>"
    },
    "menu": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M4 5h16M4 12h16M4 19h16\"/>"
    },
    "microscope": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M6 18h8M3 22h18m-7 0a7 7 0 1 0 0-14h-1m-4 6h2m-2-2a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Zm3-6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3\"/>"
    },
    "pin": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 17v5M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4a1 1 0 0 1 1 1z\"/>"
    },
    "radio": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M16.247 7.761a6 6 0 0 1 0 8.478m2.828-11.306a10 10 0 0 1 0 14.134m-14.15 0a10 10 0 0 1 0-14.134m2.828 11.306a6 6 0 0 1 0-8.478\"/><circle cx=\"12\" cy=\"12\" r=\"2\"/></g>"
    },
    "refresh-cw": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M3 12a9 9 0 0 1 9-9a9.75 9.75 0 0 1 6.74 2.74L21 8\"/><path d=\"M21 3v5h-5m5 4a9 9 0 0 1-9 9a9.75 9.75 0 0 1-6.74-2.74L3 16\"/><path d=\"M8 16H3v5\"/></g>"
    },
    "rocket": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09\"/><path d=\"M9 12a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.4 22.4 0 0 1-4 2z\"/><path d=\"M9 12H4s.55-3.03 2-4c1.62-1.08 5 .05 5 .05\"/></g>"
    },
    "search": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"m21 21l-4.34-4.34\"/><circle cx=\"11\" cy=\"11\" r=\"8\"/></g>"
    },
    "settings": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M9.671 4.136a2.34 2.34 0 0 1 4.659 0a2.34 2.34 0 0 0 3.319 1.915a2.34 2.34 0 0 1 2.33 4.033a2.34 2.34 0 0 0 0 3.831a2.34 2.34 0 0 1-2.33 4.033a2.34 2.34 0 0 0-3.319 1.915a2.34 2.34 0 0 1-4.659 0a2.34 2.34 0 0 0-3.32-1.915a2.34 2.34 0 0 1-2.33-4.033a2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915\"/><circle cx=\"12\" cy=\"12\" r=\"3\"/></g>"
    },
    "share-2": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><circle cx=\"18\" cy=\"5\" r=\"3\"/><circle cx=\"6\" cy=\"12\" r=\"3\"/><circle cx=\"18\" cy=\"19\" r=\"3\"/><path d=\"m8.59 13.51l6.83 3.98m-.01-10.98l-6.82 3.98\"/></g>"
    },
    "shield-check": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z\"/><path d=\"m9 12l2 2l4-4\"/></g>"
    },
    "sliders-horizontal": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M10 5H3m9 14H3M14 3v4m2 10v4m5-9h-9m9 7h-5m5-14h-7m-6 5v4m0-2H3\"/>"
    },
    "smartphone": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><rect width=\"14\" height=\"20\" x=\"5\" y=\"2\" rx=\"2\" ry=\"2\"/><path d=\"M12 18h.01\"/></g>"
    },
    "sparkles": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594zM20 2v4m2-2h-4\"/><circle cx=\"4\" cy=\"20\" r=\"2\"/></g>"
    },
    "terminal": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 19h8M4 17l6-6l-6-6\"/>"
    },
    "trending-up": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M16 7h6v6\"/><path d=\"m22 7l-8.5 8.5l-5-5L2 17\"/></g>"
    },
    "trophy": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><path d=\"M10 14.66V17a1 1 0 0 1-1 1a2 2 0 0 0-2 2v2m7-7.34V17a1 1 0 0 0 1 1a2 2 0 0 1 2 2v2m.916-12H19.5A2.5 2.5 0 0 0 22 7.5V5a1 1 0 0 0-1-1h-3M4 22h16\"/><path d=\"M6 9a6 6 0 0 0 12 0V3a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1z\"/><path d=\"M6.084 10H4.5A2.5 2.5 0 0 1 2 7.5V5a1 1 0 0 1 1-1h3\"/></g>"
    },
    "unlock": {
      "body": "<g fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\"><rect width=\"18\" height=\"11\" x=\"3\" y=\"11\" rx=\"2\" ry=\"2\"/><path d=\"M7 11V7a5 5 0 0 1 9.9-1\"/></g>"
    },
    "wifi": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 20h.01M2 8.82a15 15 0 0 1 20 0M5 12.859a10 10 0 0 1 14 0m-10.5 3.57a5 5 0 0 1 7 0\"/>"
    },
    "wifi-off": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 20h.01M8.5 16.429a5 5 0 0 1 7 0M5 12.859a10 10 0 0 1 5.17-2.69m8.83 2.69a10 10 0 0 0-2.007-1.523M2 8.82a15 15 0 0 1 4.177-2.643M22 8.82a15 15 0 0 0-11.288-3.764M2 2l20 20\"/>"
    },
    "x": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M18 6L6 18M6 6l12 12\"/>"
    },
    "zap": {
      "body": "<path fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M15.914 4a1.5 1.5 0 0 0-2.474-1.561l-9 9A1.5 1.5 0 0 0 5.5 14h4.002a.5.5 0 0 1 .471.666L8.086 20a1.5 1.5 0 0 0 2.475 1.56l9-9A1.5 1.5 0 0 0 18.5 10h-3.997a.5.5 0 0 1-.472-.667z\"/>"
    }
  }
};
const MDI_SUBSET = {
  "prefix": "mdi",
  "width": 24,
  "height": 24,
  "icons": {
    "soccer": {
      "body": "<path fill=\"currentColor\" d=\"m16.93 17.12l-.8-1.36l1.46-4.37l1.41-.47l1 .75v.14c0 .07.03.13.03.19c0 1.97-.66 3.71-1.97 5.21zM9.75 15l-1.37-4.03L12 8.43l3.62 2.54L14.25 15zM12 20.03c-.88 0-1.71-.14-2.5-.42l-.69-1.51l.66-1.1h5.11l.61 1.1l-.69 1.51c-.79.28-1.62.42-2.5.42m-6.06-2.82c-.53-.62-.99-1.45-1.38-2.46c-.39-1.02-.59-1.94-.59-2.75c0-.06.03-.12.03-.19v-.14l1-.75l1.41.47l1.46 4.37l-.8 1.36zM11 5.29v1.4L7 9.46l-1.34-.42l-.42-1.36C5.68 7 6.33 6.32 7.19 5.66s1.68-1.09 2.46-1.31zm3.35-.94c.78.22 1.6.65 2.46 1.31S18.32 7 18.76 7.68l-.42 1.36l-1.34.43l-4-2.77V5.29zm-9.42.58C3 6.89 2 9.25 2 12s1 5.11 2.93 7.07S9.25 22 12 22s5.11-1 7.07-2.93S22 14.75 22 12s-1-5.11-2.93-7.07S14.75 2 12 2S6.89 3 4.93 4.93\"/>"
    },
    "tennis": {
      "body": "<path fill=\"currentColor\" d=\"M18 15a4 4 0 0 1 4 4a4 4 0 0 1-4 4a4 4 0 0 1-4-4a4 4 0 0 1 4-4m0 2a2 2 0 0 0-2 2a2 2 0 0 0 2 2a2 2 0 0 0 2-2a2 2 0 0 0-2-2M6.05 14.54s1.41-1.42 1.42-4.24c-.36-2.19.5-4.76 2.47-6.72C12.87.65 17.14.17 19.5 2.5c2.33 2.36 1.85 6.63-1.08 9.56c-1.96 1.97-4.53 2.83-6.72 2.47c-2.82.01-4.24 1.42-4.24 1.42l-4.24 4.24l-1.41-1.41zM18.07 3.93C16.5 2.37 13.5 2.84 11.35 5c-2.14 2.14-2.62 5.15-1.06 6.71c1.57 1.56 4.57 1.08 6.71-1.06c2.16-2.15 2.63-5.15 1.07-6.72\"/>"
    },
    "basketball": {
      "body": "<path fill=\"currentColor\" d=\"M2.34 14.63c.6-.22 1.22-.33 1.88-.33q2.01 0 3.51 1.26L4.59 18.7a10.6 10.6 0 0 1-2.25-4.07M15.56 9.8c1.97 1.47 4.1 1.83 6.38 1.08c.03.21.06.59.06 1.12c0 1.03-.25 2.18-.72 3.45c-.47 1.26-1.05 2.28-1.73 3.05l-6.33-6.31zm-6.79 6.84c1.06 1.53 1.28 3.2.65 5.02c-1.42-.41-2.69-1.05-3.75-1.93zm3.42-3.42l6.31 6.33c-2.17 1.9-4.72 2.7-7.62 2.39c.21-.66.32-1.38.32-2.16c0-.62-.14-1.35-.42-2.18s-.61-1.51-.98-2.04zM8.81 14.5a6.7 6.7 0 0 0-3.23-1.59c-1.22-.23-2.39-.16-3.52.22c-.03-.22-.06-.6-.06-1.13c0-1.03.25-2.18.72-3.45c.47-1.26 1.05-2.28 1.73-3.05l6.66 6.69zm6.75-6.77c-1.34-1.65-1.65-3.45-.93-5.39c.62.16 1.33.46 2.13.92c.79.45 1.44.9 1.94 1.33zm6.1 1.65c-.6.21-1.22.32-1.88.32c-1.09 0-2.14-.32-3.14-.98l3.09-3.05c.88 1.1 1.52 2.33 1.93 3.71m-9.47 1.73L5.5 4.45c2.17-1.9 4.72-2.7 7.63-2.39q-.33.99-.33 2.16c0 .72.16 1.53.49 2.44c.33.9.71 1.62 1.21 2.15z\"/>"
    },
    "volleyball": {
      "body": "<path fill=\"currentColor\" d=\"M19.04 4.85C17.34 3.2 15.33 2.25 13 2v3.62l9 5.18c-.28-2.3-1.27-4.3-2.96-5.95M12 22c3.44 0 6.16-1.38 8.17-4.14L17.06 16l-8.99 5.2c1.25.53 2.57.8 3.93.8m1-10.59l8.15 4.66c.44-.94.73-1.93.85-2.96l-9-5.18zm-9.12 6.4c.66.91 1.38 1.65 2.17 2.19l8.99-5.1L12 13.15zM11.04 2C10 2.09 9 2.36 8 2.8v10.35l3.04-1.74zM2 12c0 1.39.3 2.77.89 4.12L6 14.28V4c-2.67 2-4 4.65-4 8\"/>"
    },
    "hockey-sticks": {
      "body": "<path fill=\"currentColor\" d=\"M17.68 4H14.3l-1.74 4c-.03.04-.11.22-.25.5s-.25.54-.31.69L9.7 4H6.32l4.09 8.84c.09.22.32.75.7 1.59c.39.85.67 1.48.89 1.92l1.41 3.09c.19.34.48.51.89.51L19 20v-4h-4l-1.4-3.16zm2.35 12v4H22v-3c0-.27-.09-.5-.28-.72c-.19-.2-.42-.28-.72-.28zM5 16v4l4.7-.05c.41 0 .7-.17.89-.51l.85-1.94l-1.6-3.44L9 16zm-3 4h1.97v-4H3c-.3 0-.53.08-.72.28c-.19.22-.28.45-.28.72z\"/>"
    },
    "football": {
      "body": "<path fill=\"currentColor\" d=\"M8.39 21L3 15.61c0 1.09.04 2.1.2 3.02c.15.92.3 1.47.51 1.66c.19.21.73.36 1.64.52s1.92.19 3.04.19M15.5 9.89L9.89 15.5L8.5 14.11l5.61-5.61zM3.29 13.08l7.63 7.63c2.78-.5 4.98-1.56 6.61-3.18c1.62-1.63 2.68-3.83 3.18-6.61l-7.63-7.63c-2.78.5-4.98 1.56-6.61 3.18s-2.68 3.83-3.18 6.61M15.61 3L21 8.39c0-1.09-.04-2.1-.19-3.02c-.16-.92-.31-1.47-.52-1.66c-.19-.21-.73-.36-1.64-.51S16.73 3 15.61 3\"/>"
    },
    "baseball": {
      "body": "<path fill=\"currentColor\" d=\"M12 2c-2.5 0-4.75.9-6.5 2.4c.5.41.91.87 1.3 1.36l1.09-.63l1 1.74l-1 .57c.56 1.09.93 2.29 1.06 3.56H10v2H8.95c-.13 1.27-.5 2.47-1.06 3.56l1 .57l-1 1.74l-1.09-.63c-.39.49-.8.95-1.3 1.36c1.75 1.5 4 2.4 6.5 2.4s4.75-.9 6.5-2.4c-.5-.41-.91-.87-1.31-1.36l-1.08.63l-1-1.74l1-.58A9.9 9.9 0 0 1 15.05 13H14v-2h1.05c.13-1.27.5-2.47 1.06-3.55l-1-.58l1-1.74l1.08.63c.4-.49.81-.95 1.31-1.36C16.75 2.9 14.5 2 12 2M4.12 5.85A9.94 9.94 0 0 0 2 12c0 2.32.79 4.45 2.12 6.15c.34-.28.64-.6.93-.93l-.62-.35l1-1.74l.73.43c.39-.79.66-1.65.77-2.56H6v-2h.93c-.11-.91-.38-1.77-.77-2.56l-.73.43l-1-1.74l.62-.35c-.29-.33-.59-.65-.93-.93m15.76 0c-.34.28-.64.6-.93.93l.62.35l-1 1.74l-.73-.43c-.39.79-.66 1.65-.77 2.56H18v2h-.93c.11.91.38 1.77.77 2.56l.73-.43l1 1.74l-.62.35c.29.33.59.65.93.93A9.94 9.94 0 0 0 22 12c0-2.32-.79-4.45-2.12-6.15\"/>"
    },
    "handball": {
      "body": "<path fill=\"currentColor\" d=\"M15.83 10.43a6.93 6.93 0 0 1 2.56 4.43a6.64 6.64 0 0 1-.89 4.64l-1.72-1a5 5 0 0 0 .66-2.5a5.2 5.2 0 0 0-.98-2.94L9.18 23.93l-1.74-.98l3-5.2l-1.73-.99l-1.5 2.58l-1.71-.98l5.13-8.91A7 7 0 0 1 8.8 5.46a6.9 6.9 0 0 1 .89-4.36l1.74 1.03a4.84 4.84 0 0 0-.52 3.77a4.74 4.74 0 0 0 2.3 3.03M16 5a2 2 0 1 0 2 2a2 2 0 0 0-2-2m-2.5-4A1.5 1.5 0 1 0 15 2.5A1.5 1.5 0 0 0 13.5 1\"/>"
    },
    "bullseye-arrow": {
      "body": "<path fill=\"currentColor\" d=\"M12 2A10 10 0 0 0 2 12a10 10 0 0 0 10 10a10 10 0 0 0 10-10c0-1.16-.21-2.31-.61-3.39l-1.6 1.6c.14.59.21 1.19.21 1.79a8 8 0 0 1-8 8a8 8 0 0 1-8-8a8 8 0 0 1 8-8c.6 0 1.2.07 1.79.21L15.4 2.6C14.31 2.21 13.16 2 12 2m7 0l-4 4v1.5l-2.55 2.55C12.3 10 12.15 10 12 10a2 2 0 0 0-2 2a2 2 0 0 0 2 2a2 2 0 0 0 2-2c0-.15 0-.3-.05-.45L16.5 9H18l4-4h-3zm-7 4a6 6 0 0 0-6 6a6 6 0 0 0 6 6a6 6 0 0 0 6-6h-2a4 4 0 0 1-4 4a4 4 0 0 1-4-4a4 4 0 0 1 4-4z\"/>"
    },
    "table-tennis": {
      "body": "<path fill=\"currentColor\" d=\"M18.5 14c1.4 0 2.5 1.1 2.5 2.5S19.9 19 18.5 19S16 17.9 16 16.5s1.1-2.5 2.5-2.5M7 15s1 1 1 2v3.5c0 .8.7 1.5 1.5 1.5s1.5-.7 1.5-1.5V17c0-1 1-2 1-2zm1-1h3s5 0 5-5s-4-7-6.5-7S3 4 3 9s5 5 5 5\"/>"
    }
  }
};

let initialized = false;
export function setupIconifyCollections(): void {
  if (initialized) return;
  initialized = true;
  addCollection(LUCIDE_SUBSET as any);
  addCollection(MDI_SUBSET as any);
}
