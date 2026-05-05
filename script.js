const awardArchive = Array.isArray(window.AD_ARCHIVE) ? window.AD_ARCHIVE : [];
const copypediaArchive = Array.isArray(window.COPYPEDIA_ARCHIVE)
  ? window.COPYPEDIA_ARCHIVE
  : [];
const archive = [...awardArchive, ...copypediaArchive];

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

const appShell = document.querySelector(".app-shell");
const capsuleGrid = document.getElementById("capsule-grid");
const loadedCapsule = document.getElementById("loaded-capsule");
const brewCaption = document.getElementById("brew-caption");
const copyText = document.getElementById("copy-text");
const copyMeta = document.getElementById("copy-meta");
const noteLink = document.getElementById("note-link");
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

function renderCopy(item, capsule) {
  if (!item) {
    copyText.textContent = "아직 연결된 카피가 없습니다.";
    copyMeta.textContent = "";
    setLinkState(null);
    return;
  }

  currentId = item.id;
  copyText.textContent = item.copy;
  copyText.classList.toggle("is-long", item.copy.length > 22);
  copyMeta.textContent = [capsule.label, item.brand, item.campaign]
    .filter(Boolean)
    .join(" · ");
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

function renderCapsules() {
  capsuleGrid.innerHTML = capsules
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
          <span class="capsule-label">${capsule.label}</span>
          <span class="capsule-note">${capsule.note}</span>
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

if (statusCount) {
  statusCount.textContent = `${archive.length.toLocaleString("ko-KR")} copies`;
}

renderCapsules();
