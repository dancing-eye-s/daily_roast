const awardArchive = Array.isArray(window.AD_ARCHIVE) ? window.AD_ARCHIVE : [];
const copypediaArchive = Array.isArray(window.COPYPEDIA_ARCHIVE)
  ? window.COPYPEDIA_ARCHIVE
  : [];
const archive = [...awardArchive, ...copypediaArchive];

const cookieArea = document.querySelector(".cookie-area");
const cookieButton = document.getElementById("fortune-cookie");
const statusCount = document.getElementById("status-count");
const cookieSlip = document.getElementById("cookie-slip");
const steamBrand = document.getElementById("steam-brand");
const noteCopy = document.getElementById("note-copy");
const noteMeta = document.getElementById("note-meta");
const noteLink = document.getElementById("note-link");

let currentId = null;

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

function renderArchive(item) {
  if (!item) {
    noteCopy.textContent = "아직 연결된 카피가 없습니다.";
    noteMeta.textContent = "";
    cookieSlip.textContent = "";
    steamBrand.textContent = "";
    cookieButton.style.removeProperty("--copy-lines");
    setLinkState(null);
    return;
  }

  currentId = item.id;
  noteCopy.textContent = item.copy;
  noteMeta.textContent = [item.brand, item.campaign].filter(Boolean).join(" · ");
  cookieSlip.textContent = item.copy;
  steamBrand.textContent = [item.brand, item.campaign].filter(Boolean).join(" · ");
  cookieButton.style.setProperty("--copy-lines", item.copy.length > 13 ? 2 : 1);
  setLinkState(item);
}

function crackCookie() {
  cookieArea.classList.remove("is-shaking");
  cookieArea.classList.remove("is-revealed");
  cookieButton.setAttribute("aria-expanded", "false");
  void cookieArea.offsetWidth;
  cookieArea.classList.add("is-shaking");

  window.setTimeout(() => {
    const selected = pickRandomArchive();
    renderArchive(selected);
    cookieArea.classList.add("is-revealed");
    cookieButton.setAttribute("aria-expanded", "true");
  }, 180);
}

cookieButton?.addEventListener("click", crackCookie);

if (statusCount) {
  statusCount.textContent = `현재 ${archive.length.toLocaleString("ko-KR")}개의 카피가 랜덤 풀에 연결되어 있습니다.`;
}

renderArchive(null);
