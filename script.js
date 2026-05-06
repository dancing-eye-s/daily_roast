const COPY_READY_STATUSES = new Set(["verified", "collected"]);
const copyArchive = Array.isArray(window.COPY_ARCHIVE) ? window.COPY_ARCHIVE : [];
const archive = copyArchive.filter((item) => {
  if (item.collection !== "award") {
    return true;
  }

  return COPY_READY_STATUSES.has(item.copyStatus);
});

const capsules = [
  {
    id: "passion",
    label: "열정",
    note: "마음을 데우는 문장",
    color: "#c94f3d",
  },
  {
    id: "wonder",
    label: "동심",
    note: "아이처럼 반짝이는 문장",
    color: "#547aa5",
  },
  {
    id: "tears",
    label: "감동",
    note: "조용히 울림이 남는 문장",
    color: "#2f2925",
  },
  {
    id: "humor",
    label: "유머",
    note: "피식 웃게 되는 문장",
    color: "#d6a33a",
  },
  {
    id: "pride",
    label: "자긍심",
    note: "한국인이라서 뜨거운 문장",
    color: "#5d7d55",
  },
];

const drawerCapsules = Array.from({ length: 25 }, (_, index) => {
  const capsule = capsules[index % capsules.length];
  return {
    ...capsule,
    instanceId: `${capsule.id}-${index}`,
  };
});

const appShell = document.querySelector(".app-shell");
const capsuleGrid = document.getElementById("capsule-grid");
const loadedCapsule = document.getElementById("loaded-capsule");
const brewCaption = document.getElementById("brew-caption");
const copyText = document.getElementById("copy-text");
const copyMeta = document.getElementById("copy-meta");
const noteLink = document.getElementById("note-link");
const saveImageButton = document.getElementById("save-image-button");
const againButton = document.getElementById("again-button");
const statusCount = document.getElementById("status-count");

let currentId = null;
let brewingTimer = null;
let revealTimer = null;

function pickRandomArchive() {
  if (!archive.length) {
    return null;
  }

  if (archive.length === 1) {
    return archive[0];
  }

  const candidates = archive.filter((item) => item.id !== currentId);
  return candidates[Math.floor(Math.random() * candidates.length)];
}

function setLinkState(item) {
  if (!item?.sourceUrl) {
    noteLink.href = "#";
    noteLink.setAttribute("aria-disabled", "true");
    noteLink.classList.add("is-disabled");
    return;
  }

  noteLink.href = item.sourceUrl;
  noteLink.removeAttribute("aria-disabled");
  noteLink.classList.remove("is-disabled");
}

function escapePattern(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isWordplayCopy(copy) {
  return /MEGA|메가|알바몬으로 알바가|뭘로토닝|나랑드랑|감탄에 감탄|퍼울했죠|시원서커|다다다|🎵/.test(
    copy,
  );
}

function getDisplayCopy(item) {
  const copy = item.copy.replace(/\s+/g, " ").trim();
  const brand = (item.brand || "").replace(/\s+/g, " ").trim();

  if (!brand || isWordplayCopy(copy)) {
    return copy;
  }

  const aliases = [brand, brand.replace(/\s+/g, "")]
    .map((alias) => alias.replace(/[()]/g, "").trim())
    .filter((alias) => alias.length >= 3);

  for (const alias of aliases) {
    const suffixPattern = new RegExp(`[\\s,，.。:：-]*${escapePattern(alias)}$`, "i");
    const cleaned = copy.replace(suffixPattern, "").trim();

    if (cleaned !== copy && cleaned.replace(/\s+/g, "").length >= 4) {
      return cleaned;
    }
  }

  return copy;
}

function getParticle(token) {
  const match = token.match(/(에게도|에게|에도|에서|으로|부터|까지|처럼|보다|엔|에|은|는|이|가|도)$/);
  return match ? match[1] : "";
}

function getReadableLongBreak(copy) {
  const breakPatterns = [
    /[^\s]+(와|과)\s+함께\s+/,
    /\s+덕분에\s+/,
    /[^\s]+(를|을)\s+위해\s+/,
    /[^\s]+(를|을)\s+통해\s+/,
    /[^\s]+(로|으로)\s+인해\s+/,
    /\s+(라서|이라서)\s+/,
  ];

  for (const pattern of breakPatterns) {
    const match = pattern.exec(copy);

    if (!match) {
      continue;
    }

    const splitAt = match.index + match[0].length;
    const firstLine = copy.slice(0, splitAt).trim();
    const secondLine = copy.slice(splitAt).trim();

    if (
      firstLine.replace(/\s+/g, "").length >= 10 &&
      secondLine.replace(/\s+/g, "").length >= 8 &&
      firstLine.length <= 32 &&
      secondLine.length <= 34
    ) {
      return `${firstLine}\n${secondLine}`;
    }
  }

  return "";
}

function getSemanticLineBreak(copy) {
  const preservedLines = copy
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (preservedLines.length > 1) {
    return preservedLines.join("\n");
  }

  const commaParts = copy
    .split(/[,，]/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (
    commaParts.length === 2 &&
    commaParts.every((part) => part.replace(/\s+/g, "").length >= 4)
  ) {
    return commaParts.join("\n");
  }

  const tokens = copy.split(" ").filter(Boolean);
  const firstParticle = getParticle(tokens[0] || "");

  if (!firstParticle || tokens.length < 4) {
    return "";
  }

  const splitIndex = tokens.findIndex((token, index) => {
    if (index < 2 || index > tokens.length - 2) {
      return false;
    }

    return getParticle(token) === firstParticle;
  });

  if (splitIndex === -1) {
    return "";
  }

  const firstLine = tokens.slice(0, splitIndex).join(" ");
  const secondLine = tokens.slice(splitIndex).join(" ");
  const firstTokenCount = splitIndex;
  const secondTokenCount = tokens.length - splitIndex;

  if (
    Math.abs(firstTokenCount - secondTokenCount) > 2 ||
    firstLine.replace(/\s+/g, "").length < 4 ||
    secondLine.replace(/\s+/g, "").length < 4 ||
    firstLine.length > 18 ||
    secondLine.length > 22
  ) {
    return "";
  }

  return `${firstLine}\n${secondLine}`;
}

function formatCopy(copy) {
  const normalized = copy.replace(/[ \t]+/g, " ").trim();
  const longBreak = getReadableLongBreak(normalized);

  if (longBreak) {
    return longBreak;
  }

  const semanticBreak = getSemanticLineBreak(normalized);

  if (semanticBreak) {
    return semanticBreak;
  }

  if (normalized.length <= 15) {
    return normalized;
  }

  const punctuationPattern = /[,，.。!！?？:：;；]/g;
  const candidates = [];
  let match = punctuationPattern.exec(normalized);

  while (match) {
    candidates.push(match.index + 1);
    match = punctuationPattern.exec(normalized);
  }

  normalized.split("").forEach((char, index) => {
    if (char === " " && index > 0) {
      candidates.push(index);
    }
  });

  const midpoint = normalized.length / 2;
  const splitAt =
    candidates
      .filter((index) => index >= 6 && index <= normalized.length - 4)
      .sort((a, b) => Math.abs(a - midpoint) - Math.abs(b - midpoint))[0] ??
    Math.min(15, Math.ceil(midpoint));

  const firstLine = normalized.slice(0, splitAt).trim();
  const secondLine = normalized.slice(splitAt).trim();

  return `${firstLine}\n${secondLine}`;
}

function renderCopy(item, capsule) {
  if (!item) {
    copyText.textContent = "아직 연결된 카피가 없습니다.";
    copyMeta.textContent = "";
    setLinkState(null);
    return;
  }

  currentId = item.id;
  const displayCopy = getDisplayCopy(item);
  copyText.textContent = formatCopy(displayCopy);
  copyText.classList.toggle("is-long", displayCopy.length > 15);
  copyMeta.textContent = [item.brand, item.campaign].filter(Boolean).join(" · ");
  setLinkState(item);
}

function brewCapsule(capsule) {
  const selected = pickRandomArchive();
  window.clearTimeout(brewingTimer);
  window.clearTimeout(revealTimer);

  appShell.style.setProperty("--capsule-color", capsule.color);
  loadedCapsule.style.background = capsule.color;
  brewCaption.textContent = `${capsule.label} 캡슐을 장착하는 중`;
  renderCopy(selected, capsule);

  appShell.dataset.state = "brew";
  appShell.classList.remove("is-brewing", "is-revealed");
  void appShell.offsetWidth;
  appShell.classList.add("is-brewing");

  brewingTimer = window.setTimeout(() => {
    brewCaption.textContent = "커피를 내리는 중";
  }, 700);

  revealTimer = window.setTimeout(() => {
    appShell.dataset.state = "reveal";
    appShell.classList.add("is-revealed");
  }, 2500);
}

function resetToDrawer() {
  window.clearTimeout(brewingTimer);
  window.clearTimeout(revealTimer);
  appShell.dataset.state = "select";
  appShell.classList.remove("is-brewing", "is-revealed");
  brewCaption.textContent = "캡슐을 장착하는 중";
}

function getDocumentStyleText() {
  return Array.from(document.styleSheets)
    .map((sheet) => {
      try {
        return Array.from(sheet.cssRules)
          .map((rule) => rule.cssText)
          .join("\n");
      } catch {
        return "";
      }
    })
    .join("\n");
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function canvasToPngBlob(canvas) {
  return new Promise((resolve) => {
    canvas.toBlob(resolve, "image/png", 1);
  });
}

async function createDomSnapshotBlob(width, height, scale) {
  const bodyClone = document.body.cloneNode(true);
  bodyClone.querySelector(".reveal-actions")?.remove();
  bodyClone.querySelectorAll("script").forEach((script) => script.remove());

  const html = `
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head>
        <style>
          html, body {
            width: ${width}px;
            height: ${height}px;
            margin: 0;
            overflow: hidden;
          }
          ${getDocumentStyleText()}
        </style>
      </head>
      <body>${bodyClone.innerHTML}</body>
    </html>
  `;
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
      <foreignObject width="100%" height="100%">${html}</foreignObject>
    </svg>
  `;
  const image = new Image();
  const svgUrl = URL.createObjectURL(
    new Blob([svg], { type: "image/svg+xml;charset=utf-8" }),
  );

  try {
    await new Promise((resolve, reject) => {
      image.onload = resolve;
      image.onerror = reject;
      image.src = svgUrl;
    });

    const canvas = document.createElement("canvas");
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    const context = canvas.getContext("2d");
    context.scale(scale, scale);
    context.drawImage(image, 0, 0, width, height);

    return canvasToPngBlob(canvas);
  } finally {
    URL.revokeObjectURL(svgUrl);
  }
}

function drawCenteredText(context, text, x, y, maxWidth, lineHeight) {
  const lines = text.split("\n").filter(Boolean);
  lines.forEach((line, index) => {
    context.fillText(line, x, y + index * lineHeight, maxWidth);
  });
  return y + Math.max(lines.length, 1) * lineHeight;
}

async function createFallbackSnapshotBlob(width, height, scale) {
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  const context = canvas.getContext("2d");
  const appWidth = Math.min(width, 430);
  const appLeft = (width - appWidth) / 2;
  const headerHeight = 54;
  const sceneTop = headerHeight;
  const sceneHeight = height - headerHeight;
  const centerX = appLeft + appWidth / 2;
  const cream = "#f3e9dc";
  const page = "#e5d7c8";
  const brownie = "#5e3023";
  const coffee = "#895737";
  const caramel = getComputedStyle(appShell).getPropertyValue("--capsule-color").trim() || "#c08552";

  context.scale(scale, scale);
  context.fillStyle = page;
  context.fillRect(0, 0, width, height);
  context.fillStyle = cream;
  context.fillRect(appLeft, 0, appWidth, height);

  context.strokeStyle = brownie;
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(appLeft, headerHeight);
  context.lineTo(appLeft + appWidth, headerHeight);
  context.stroke();

  context.fillStyle = brownie;
  context.font = "900 12px sans-serif";
  context.textAlign = "left";
  context.textBaseline = "middle";
  context.fillText("DAILY ROAST", appLeft + 20, 30);
  context.textAlign = "right";
  context.fillStyle = coffee;
  context.fillText(statusCount?.textContent || "", appLeft + appWidth - 20, 30);

  context.strokeStyle = brownie;
  context.globalAlpha = 0.5;
  context.strokeRect(appLeft + 18, sceneTop + 18, appWidth - 36, sceneHeight - 36);
  context.globalAlpha = 1;

  const cupY = sceneTop + sceneHeight / 2 + 72;
  const cupWidth = 172;
  const cupHeight = 150;
  const cupX = centerX - cupWidth / 2;

  context.strokeStyle = brownie;
  context.lineWidth = 5;
  context.beginPath();
  context.moveTo(cupX, cupY);
  context.lineTo(cupX, cupY + cupHeight - 46);
  context.quadraticCurveTo(cupX, cupY + cupHeight, cupX + 46, cupY + cupHeight);
  context.lineTo(cupX + cupWidth - 46, cupY + cupHeight);
  context.quadraticCurveTo(cupX + cupWidth, cupY + cupHeight, cupX + cupWidth, cupY + cupHeight - 46);
  context.lineTo(cupX + cupWidth, cupY);
  context.stroke();

  context.beginPath();
  context.ellipse(centerX, cupY + 28, 74, 15, 0, 0, Math.PI * 2);
  context.fillStyle = caramel;
  context.fill();

  context.beginPath();
  context.moveTo(cupX + cupWidth + 2, cupY + 30);
  context.bezierCurveTo(cupX + cupWidth + 58, cupY + 18, cupX + cupWidth + 58, cupY + 86, cupX + cupWidth + 2, cupY + 78);
  context.stroke();

  context.beginPath();
  context.moveTo(cupX - 38, cupY + cupHeight + 20);
  context.lineTo(cupX + cupWidth + 62, cupY + cupHeight + 20);
  context.stroke();

  context.lineWidth = 4;
  [centerX - 48, centerX, centerX + 48].forEach((x, index) => {
    context.beginPath();
    context.moveTo(x, cupY - 20);
    context.bezierCurveTo(x - 28, cupY - 64, x + 30, cupY - 86, x, cupY - 126 - index * 8);
    context.stroke();
  });

  context.fillStyle = brownie;
  context.textAlign = "center";
  context.textBaseline = "top";
  const isLong = copyText?.classList.contains("is-long");
  context.font = `800 ${isLong ? 27 : 34}px serif`;
  const afterCopyY = drawCenteredText(
    context,
    copyText?.textContent || "",
    centerX,
    sceneTop + 72,
    appWidth - 56,
    isLong ? 34 : 40,
  );

  context.fillStyle = coffee;
  context.font = "900 12px sans-serif";
  drawCenteredText(context, copyMeta?.textContent || "", centerX, afterCopyY + 12, appWidth - 56, 17);

  return canvasToPngBlob(canvas);
}

async function saveScreenAsImage() {
  if (!saveImageButton) {
    return;
  }

  const originalLabel = saveImageButton.textContent;
  saveImageButton.disabled = true;
  saveImageButton.textContent = "저장 중";

  try {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const scale = Math.min(window.devicePixelRatio || 1, 2);
    const blob =
      (await createDomSnapshotBlob(width, height, scale).catch(() =>
        createFallbackSnapshotBlob(width, height, scale),
      )) || (await createFallbackSnapshotBlob(width, height, scale));

    if (blob) {
      const date = new Date().toISOString().slice(0, 10);
      downloadBlob(blob, `daily-roast-${date}.png`);
    }
  } catch (error) {
    console.error(error);
    window.alert("이미지를 저장하지 못했어요. 브라우저 권한이나 다운로드 설정을 확인해주세요.");
  } finally {
    saveImageButton.disabled = false;
    saveImageButton.textContent = originalLabel;
  }
}

function renderCapsules() {
  capsuleGrid.innerHTML = drawerCapsules
    .map(
      (capsule) => `
        <button
          class="capsule-button"
          type="button"
          data-capsule="${capsule.id}"
          style="--capsule-color: ${capsule.color}"
          aria-label="${capsule.label} 감정의 광고 카피 캡슐 선택"
        >
          <span class="capsule-top"></span>
          <span class="capsule-body"></span>
        </button>
      `,
    )
    .join("");
}

capsuleGrid?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-capsule]");
  if (!button) {
    return;
  }

  const capsule = capsules.find((item) => item.id === button.dataset.capsule);
  if (capsule) {
    brewCapsule(capsule);
  }
});

againButton?.addEventListener("click", resetToDrawer);
saveImageButton?.addEventListener("click", saveScreenAsImage);

if (statusCount) {
  statusCount.textContent = `${archive.length.toLocaleString("ko-KR")} copies`;
}

renderCapsules();
